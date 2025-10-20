"""
Implement Files Node

Thực hiện file changes sử dụng incremental tools và filesystem tools.
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import (
    create_directory_tool,
    edit_file_tool,
    read_file_tool,
    write_file_tool,
)
from ..tool.incremental_tools import (
    add_function_tool,
    add_import_tool,
    create_method_tool,
    modify_function_tool,
)
from ..utils.incremental_modifications import (
    IncrementalModificationValidator,
    parse_structured_modifications,
)
from ..utils.validators import validate_file_changes


def implement_files(state: ImplementorState) -> ImplementorState:
    """
    Thực hiện file changes theo implementation plan.

    Args:
        state: ImplementorState với file changes to implement

    Returns:
        Updated ImplementorState với implementation results
    """
    try:
        print("📝 Implementing file changes...")

        # Validate file changes
        files_to_create_dict = [
            {"file_path": fc.file_path, "content": fc.content}
            for fc in state.files_to_create
        ]
        files_to_modify_dict = [
            {"file_path": fc.file_path, "content": fc.content}
            for fc in state.files_to_modify
        ]

        files_valid, file_issues = validate_file_changes(
            files_to_create_dict, files_to_modify_dict
        )
        if not files_valid:
            print(f"⚠️  File validation issues: {'; '.join(file_issues[:3])}")

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Track implementation results
        files_created = []
        files_modified = []
        errors = []

        # Process files to create
        for file_change in state.files_to_create:
            try:
                print(f"  📄 Creating: {file_change.file_path}")

                # Create parent directories if needed
                file_path = Path(file_change.file_path)
                if file_path.parent != Path("."):
                    create_result = create_directory_tool.invoke(
                        {
                            "directory_path": str(file_path.parent),
                            "working_directory": working_dir,
                        }
                    )
                    print(f"    📁 Directory: {file_path.parent}")

                # Write file content
                result = write_file_tool.invoke(
                    {
                        "file_path": file_change.file_path,
                        "content": file_change.content,
                        "working_directory": working_dir,
                        "create_dirs": True,
                    }
                )

                # Parse result with error handling
                try:
                    if not result or result.strip() == "":
                        print("    ❌ Error: Empty response from file creation tool")
                        errors.append(
                            f"Failed to create {file_change.file_path}: Empty response"
                        )
                        continue

                    result_data = json.loads(result)
                    if result_data.get("status") == "success":
                        files_created.append(file_change.file_path)
                        print(f"    ✅ Created: {file_change.file_path}")
                    else:
                        error_msg = result_data.get("message", "Unknown error")
                        errors.append(
                            f"Failed to create {file_change.file_path}: {error_msg}"
                        )
                        print(f"    ❌ Failed: {error_msg}")
                except json.JSONDecodeError as e:
                    print(f"    ❌ Error: Invalid JSON response - {e}")
                    print(f"    Raw response: {result[:200] if result else 'None'}...")
                    errors.append(
                        f"Failed to create {file_change.file_path}: Invalid response format"
                    )

            except Exception as e:
                error_msg = f"Error creating {file_change.file_path}: {str(e)}"
                errors.append(error_msg)
                print(f"    ❌ Error: {e}")

        # Process files to modify
        for file_change in state.files_to_modify:
            try:
                print(f"  ✏️  Modifying: {file_change.file_path}")

                if file_change.change_type == "incremental":
                    # Check if we have structured modifications
                    if file_change.structured_modifications:
                        success = _apply_structured_modifications(
                            file_change, working_dir
                        )
                    else:
                        # Use legacy incremental tools for precise changes
                        success = _apply_incremental_change(file_change, working_dir)

                    if success:
                        files_modified.append(file_change.file_path)
                        print(f"    ✅ Modified: {file_change.file_path}")
                    else:
                        errors.append(
                            f"Failed incremental modification of {file_change.file_path}"
                        )
                        print("    ❌ Failed incremental modification")

                else:
                    # Full file replacement (use sparingly)
                    result = write_file_tool.invoke(
                        {
                            "file_path": file_change.file_path,
                            "content": file_change.content,
                            "working_directory": working_dir,
                        }
                    )

                    # Parse result with error handling
                    try:
                        if not result or result.strip() == "":
                            print(
                                "    ❌ Error: Empty response from file modification tool"
                            )
                            errors.append(
                                f"Failed to modify {file_change.file_path}: Empty response"
                            )
                            continue

                        result_data = json.loads(result)
                        if result_data.get("status") == "success":
                            files_modified.append(file_change.file_path)
                            print(f"    ✅ Modified: {file_change.file_path}")
                        else:
                            error_msg = result_data.get("message", "Unknown error")
                            errors.append(
                                f"Failed to modify {file_change.file_path}: {error_msg}"
                            )
                            print(f"    ❌ Failed: {error_msg}")
                    except json.JSONDecodeError as e:
                        print(f"    ❌ Error: Invalid JSON response - {e}")
                        print(
                            f"    Raw response: {result[:200] if result else 'None'}..."
                        )
                        errors.append(
                            f"Failed to modify {file_change.file_path}: Invalid response format"
                        )

            except Exception as e:
                error_msg = f"Error modifying {file_change.file_path}: {str(e)}"
                errors.append(error_msg)
                print(f"    ❌ Error: {e}")

        # Update state
        state.files_created.extend(files_created)
        state.files_modified.extend(files_modified)

        # Store results
        state.tools_output["file_implementation"] = {
            "files_created": files_created,
            "files_modified": files_modified,
            "errors": errors,
        }

        # Determine next phase
        if errors:
            state.status = "implementation_partial"
            state.error_message = (
                f"Some file operations failed: {'; '.join(errors[:3])}"
            )
        else:
            state.status = "files_implemented"

        state.current_phase = "run_tests"

        # Add message
        total_files = len(files_created) + len(files_modified)
        message = AIMessage(
            content=f"✅ File implementation completed\n"
            f"- Files created: {len(files_created)}\n"
            f"- Files modified: {len(files_modified)}\n"
            f"- Total files: {total_files}\n"
            f"- Errors: {len(errors)}\n"
            f"- Next: Run tests"
        )
        state.messages.append(message)

        print(
            f"✅ File implementation completed - {total_files} files processed, {len(errors)} errors"
        )

        return state

    except Exception as e:
        state.error_message = f"File implementation failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ File implementation error: {str(e)}")
        state.messages.append(message)

        print(f"❌ File implementation failed: {e}")
        return state


def _extract_actual_content(formatted_content: str) -> str:
    """
    Extract actual file content from read_file_tool output (cat -n format).

    Args:
        formatted_content: Content with line numbers from read_file_tool

    Returns:
        Actual file content without line numbers
    """
    lines = formatted_content.splitlines()
    actual_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            actual_lines.append("")
            continue

        # Extract content after line number and tab
        # Format: "     1\tclass UserService:"
        if "\t" in line:
            actual_content = line.split("\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            # Fallback for lines without tab
            actual_lines.append(line)

    return "\n".join(actual_lines)


def _find_best_insertion_point(formatted_content: str) -> dict | None:
    """
    Find the best insertion point in file content using line-by-line analysis.

    Args:
        formatted_content: File content from read_file_tool (with line numbers)

    Returns:
        Dict with insertion point info or None if not found
    """
    # Extract actual content without line numbers
    actual_content = _extract_actual_content(formatted_content)
    lines = actual_content.splitlines()

    # Priority order for insertion points
    insertion_patterns = [
        {"pattern": "pass", "type": "pass"},
        {"pattern": "# TODO: Implement", "type": "todo_implement"},
        {"pattern": "# TODO", "type": "todo"},
        {"pattern": "...", "type": "ellipsis"},
        {"pattern": "# Add implementation here", "type": "add_implementation"},
        {"pattern": "# Implementation goes here", "type": "implementation_here"},
    ]

    for i, line in enumerate(lines):
        stripped = line.strip()

        for pattern_info in insertion_patterns:
            pattern = pattern_info["pattern"]

            # Check for exact match or standalone keyword
            if pattern == "pass":
                # For 'pass', check if it's a standalone statement
                if stripped == "pass" or (
                    stripped.startswith("pass ") and "#" in stripped
                ):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }
            elif pattern == "...":
                # For ellipsis, check if it's standalone
                if stripped == "..." or stripped.startswith("... "):
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }
            else:
                # For comment patterns, check if line contains the pattern
                if pattern in stripped:
                    return {
                        "type": pattern_info["type"],
                        "line": i + 1,
                        "original_line": line,
                        "indentation": len(line) - len(line.lstrip()),
                        "pattern": pattern,
                    }

    return None


def _apply_structured_modifications(file_change: FileChange, working_dir: str) -> bool:
    """
    Apply structured incremental modifications using OLD_CODE/NEW_CODE pairs.

    Args:
        file_change: FileChange with structured_modifications content
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    try:
        # Debug: Log structured modifications content
        print(
            f"    🔍 DEBUG: Structured modifications length: {len(file_change.structured_modifications)} chars"
        )
        print(
            f"    🔍 DEBUG: First 300 chars: {file_change.structured_modifications[:300]}..."
        )

        # Parse structured modifications from LLM output
        print("    🔍 DEBUG: Starting parse_structured_modifications...")
        modifications = parse_structured_modifications(
            file_change.structured_modifications
        )
        print(
            f"    🔍 DEBUG: Parsing completed, got {len(modifications)} modifications"
        )

        if not modifications:
            print("    ⚠️ No valid modifications found in structured output")
            print("    💡 This is expected when LLM generates placeholder OLD_CODE")
            return False

        print(f"    🔍 DEBUG: Parsed {len(modifications)} modifications")

        # Read current file content
        read_result = read_file_tool.invoke(
            {"file_path": file_change.file_path, "working_directory": working_dir}
        )

        if "File not found" in read_result or "Error:" in read_result:
            print(f"    ❌ Could not read file: {file_change.file_path}")
            return False

        # Extract actual content (remove line numbers if present)
        current_content = _extract_actual_content(read_result)

        # Apply modifications using validator
        validator = IncrementalModificationValidator(current_content)
        result = validator.apply_multiple_modifications(modifications)

        if result.success:
            # Write modified content back to file
            write_result = write_file_tool.invoke(
                {
                    "file_path": file_change.file_path,
                    "content": result.final_content,
                    "working_directory": working_dir,
                }
            )

            if "successfully" in write_result.lower():
                print(
                    f"    ✅ Applied {result.modifications_applied} structured modifications"
                )
                for warning in result.warnings:
                    print(f"    {warning}")
                return True
            else:
                print(f"    ❌ Failed to write modified file: {write_result}")
                return False
        else:
            print("    ❌ Structured modifications failed:")
            for error in result.errors:
                print(f"      {error}")
            return False

    except Exception as e:
        print(f"    ❌ Error applying structured modifications: {e}")
        return False


def _apply_incremental_change(file_change: FileChange, working_dir: str) -> bool:
    """
    Apply incremental change to a file using appropriate tool.

    Args:
        file_change: FileChange with incremental modification details
        working_dir: Working directory

    Returns:
        True if successful, False otherwise
    """
    try:
        # Determine the type of incremental change needed
        if file_change.target_function:
            # Function-level modification
            if file_change.content.strip().startswith("def "):
                # Adding new function
                result = add_function_tool.invoke(
                    {
                        "file_path": file_change.file_path,
                        "function_code": file_change.content,
                        "after_function": file_change.target_function,
                        "working_directory": working_dir,
                    }
                )
            else:
                # Modifying existing function
                changes = [{"type": "replace", "content": file_change.content}]
                result = modify_function_tool.invoke(
                    {
                        "file_path": file_change.file_path,
                        "function_name": file_change.target_function,
                        "changes": changes,
                        "working_directory": working_dir,
                    }
                )

        elif file_change.target_class:
            # Class-level modification (add method)
            result = create_method_tool.invoke(
                {
                    "file_path": file_change.file_path,
                    "class_name": file_change.target_class,
                    "method_code": file_change.content,
                    "working_directory": working_dir,
                }
            )

        elif file_change.content.strip().startswith(("import ", "from ")):
            # Import statement
            result = add_import_tool.invoke(
                {
                    "file_path": file_change.file_path,
                    "import_statement": file_change.content.strip(),
                    "working_directory": working_dir,
                }
            )

        else:
            # Generic incremental modification - try to find insertion points
            # Read file first to analyze content
            read_result = read_file_tool.invoke(
                {"file_path": file_change.file_path, "working_directory": working_dir}
            )

            if "File not found" in read_result or "Error:" in read_result:
                return False

            # Find proper insertion points using line-by-line analysis
            insertion_point = _find_best_insertion_point(read_result)

            result = None
            if insertion_point:
                print(
                    f"    🎯 Found insertion point: '{insertion_point['type']}' at line {insertion_point['line']}"
                )

                # Use the exact line content for replacement
                old_str = insertion_point["original_line"]

                # Preserve indentation when replacing
                indentation = " " * insertion_point["indentation"]
                new_content_lines = file_change.content.split("\n")

                # Apply indentation to all non-empty lines
                indented_lines = []
                for line in new_content_lines:
                    if line.strip():  # Non-empty line
                        indented_lines.append(indentation + line)
                    else:  # Empty line
                        indented_lines.append("")

                indented_content = "\n".join(indented_lines)

                result = edit_file_tool.invoke(
                    {
                        "file_path": file_change.file_path,
                        "old_str": old_str,
                        "new_str": indented_content,
                        "working_directory": working_dir,
                    }
                )

            # If no insertion point found, try to append to end of file
            if not result:
                print("    ⚠️ No insertion point found, appending to end of file")
                # Extract actual content from formatted read_result (remove line numbers)
                current_content = _extract_actual_content(read_result)
                new_content = current_content + "\n\n" + file_change.content

                result = write_file_tool.invoke(
                    {
                        "file_path": file_change.file_path,
                        "content": new_content,
                        "working_directory": working_dir,
                    }
                )

        # Check result with error handling
        try:
            if not result or result.strip() == "":
                print("Error in incremental change: Empty response")
                return False

            result_data = json.loads(result)
            return result_data.get("status") == "success"
        except json.JSONDecodeError as e:
            print(f"Error in incremental change: {e}")
            print(f"Raw response: {result[:200] if result else 'None'}...")
            return False

    except Exception as e:
        print(f"Error in incremental change: {e}")
        return False
