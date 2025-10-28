"""
Implement Files Module

Provides file implementation functionality as both:
1. Helper functions for single file operations (used by execute_step)
2. Node function for batch file operations (legacy/optional)

This refactored module supports Option 1 flow where execute_step
generates and implements files sequentially per sub-step.
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import (
    create_directory_tool,
    read_file_tool,
    str_replace_tool,
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

# ========================================
# HELPER FUNCTIONS (for execute_step)
# ========================================


def implement_single_file(
    file_change: FileChange,
    working_dir: str,
) -> tuple[bool, str]:
    """
    Implement a single file change (create or modify).

    This is the main helper function used by execute_step for
    sequential file implementation.

    Args:
        file_change: File change to implement
        working_dir: Working directory path

    Returns:
        (success: bool, error_message: str)
    """
    try:
        if file_change.operation == "create":
            return _create_single_file(file_change, working_dir)
        elif file_change.operation == "modify":
            return _modify_single_file(file_change, working_dir)
        else:
            return False, f"Unknown operation: {file_change.operation}"
    except Exception as e:
        return False, f"Error implementing {file_change.file_path}: {str(e)}"


def _create_single_file(
    file_change: FileChange,
    working_dir: str,
) -> tuple[bool, str]:
    """
    Create a new file.

    Args:
        file_change: File change with create operation
        working_dir: Working directory

    Returns:
        (success, error_message)
    """
    try:
        print(f"  📄 Creating: {file_change.file_path}")

        # Create parent directories if needed
        file_path = Path(file_change.file_path)
        if file_path.parent != Path("."):
            create_directory_tool.invoke(
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

        # Parse result
        if not result or result.strip() == "":
            return False, "Empty response from file creation tool"

        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                print(f"    ✅ Created: {file_change.file_path}")
                return True, ""
            else:
                error_msg = result_data.get("message", "Unknown error")
                print(f"    ❌ Failed: {error_msg}")
                return False, error_msg
        except json.JSONDecodeError as e:
            print(f"    ❌ Error: Invalid JSON response - {e}")
            return False, f"Invalid response format: {str(e)}"

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False, str(e)


def _modify_single_file(
    file_change: FileChange,
    working_dir: str,
) -> tuple[bool, str]:
    """
    Modify an existing file.

    Args:
        file_change: File change with modify operation
        working_dir: Working directory

    Returns:
        (success, error_message)
    """
    try:
        print(f"  ✏️  Modifying: {file_change.file_path}")

        # ✅ NEW APPROACH: Always use full-file regeneration
        # file_change.content should contain the complete regenerated file
        if not file_change.content or len(file_change.content.strip()) == 0:
            print("    ❌ No content to write")
            return False, "No content generated for file modification"

        print(f"    📝 Writing complete file ({len(file_change.content)} chars)")

        # Write the complete file content
        result = write_file_tool.invoke(
            {
                "file_path": file_change.file_path,
                "content": file_change.content,
                "working_directory": working_dir,
            }
        )

        # Parse result
        if not result or result.strip() == "":
            return False, "Empty response from file modification tool"

        try:
            result_data = json.loads(result)
            if result_data.get("status") == "success":
                print(f"    ✅ Modified: {file_change.file_path}")
                return True, ""
            else:
                error_msg = result_data.get("message", "Unknown error")
                print(f"    ❌ Failed: {error_msg}")
                return False, error_msg
        except json.JSONDecodeError as e:
            print(f"    ❌ Error: Invalid JSON response - {e}")
            return False, f"Invalid response format: {str(e)}"

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False, str(e)


# ========================================
# NODE FUNCTION (for batch operations)
# ========================================


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

                # ✅ NEW APPROACH: Always use full-file regeneration
                if not file_change.content or len(file_change.content.strip()) == 0:
                    print("    ❌ No content to write")
                    errors.append(f"No content generated for {file_change.file_path}")
                    continue

                print(
                    f"    📝 Writing complete file ({len(file_change.content)} chars)"
                )

                # Write the complete file content
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
                    print(f"    Raw response: {result[:200] if result else 'None'}...")
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


def _verify_file_content_for_modifications(
    file_path: str, current_content: str, modifications: list
) -> dict:
    """
    Verify that file content is appropriate for the planned modifications.

    Args:
        file_path: Path to the file being modified
        current_content: Current file content
        modifications: List of CodeModification objects

    Returns:
        Dict with 'valid' (bool), 'reason' (str), and 'suggestions' (list) keys
    """
    try:
        # Analyze file type and content
        file_analysis = _analyze_file_type_and_content(file_path, current_content)

        # Check each modification for compatibility
        for i, modification in enumerate(modifications):
            old_code = modification.old_code.strip()

            # Check if OLD_CODE exists in file
            if old_code not in current_content:
                # Try to find similar code or suggest alternatives
                suggestions = _suggest_alternatives_for_missing_code(
                    old_code, current_content, file_analysis
                )

                return {
                    "valid": False,
                    "reason": f"Modification #{i + 1}: OLD_CODE not found in {file_path}",
                    "suggestions": suggestions,
                }

            # Check if modification makes sense for this file type
            compatibility_check = _check_modification_compatibility(
                modification, file_analysis
            )

            if not compatibility_check["compatible"]:
                return {
                    "valid": False,
                    "reason": f"Modification #{i + 1}: {compatibility_check['reason']}",
                    "suggestions": compatibility_check.get("suggestions", []),
                }

        return {"valid": True, "reason": "All modifications are valid"}

    except Exception as e:
        return {
            "valid": False,
            "reason": f"Verification error: {str(e)}",
            "suggestions": ["Check file path and content format"],
        }


def _analyze_file_type_and_content(file_path: str, content: str) -> dict:
    """Analyze file type and content to understand its purpose."""
    import os

    file_ext = os.path.splitext(file_path)[1].lower()
    file_name = os.path.basename(file_path).lower()

    analysis = {
        "extension": file_ext,
        "file_name": file_name,
        "content_type": "unknown",
        "patterns": [],
        "line_count": len(content.splitlines()),
    }

    # Detect content patterns
    if "mongoose" in content.lower() and "schema" in content.lower():
        analysis["content_type"] = "mongoose_model"
        analysis["patterns"].append("database_model")
    elif "router" in content.lower() or "app.get" in content or "app.post" in content:
        analysis["content_type"] = "express_routes"
        analysis["patterns"].append("route_handlers")
    elif "req.body" in content and "res." in content:
        analysis["content_type"] = "controller"
        analysis["patterns"].append("request_handlers")
    elif "module.exports" in content:
        analysis["patterns"].append("node_module")

    return analysis


def _suggest_alternatives_for_missing_code(
    old_code: str, content: str, file_analysis: dict
) -> list:
    """Suggest alternatives when OLD_CODE is not found."""
    suggestions = []

    # Check if this looks like route handler code in a model file
    if "req.body" in old_code and file_analysis["content_type"] == "mongoose_model":
        suggestions.extend(
            [
                "You're trying to modify a Mongoose model file with route handler code",
                "Consider modifying a controller or route file instead",
                "Look for files in src/controllers/ or src/routes/ directories",
            ]
        )

    # Check if code exists in similar form
    old_code_keywords = old_code.split()
    for keyword in old_code_keywords:
        if len(keyword) > 3 and keyword in content:
            suggestions.append(
                f"Found keyword '{keyword}' in file - check for similar patterns"
            )

    # Suggest checking file structure
    if file_analysis["line_count"] < 50:
        suggestions.append("File is small - verify you're modifying the correct file")

    # File type specific suggestions
    if file_analysis["content_type"] == "mongoose_model":
        suggestions.append(
            "This appears to be a database model file - consider if modification belongs here"
        )

    return suggestions


def _check_modification_compatibility(modification, file_analysis: dict) -> dict:
    """Check if modification is compatible with file type."""
    old_code = modification.old_code
    new_code = modification.new_code

    # Check for route handler code in model files
    if file_analysis["content_type"] == "mongoose_model":
        if any(
            pattern in old_code
            for pattern in ["req.body", "res.", "app.get", "app.post"]
        ):
            return {
                "compatible": False,
                "reason": "Trying to add route handler logic to a database model file",
                "suggestions": [
                    "Move this modification to a controller or route file",
                    "Model files should only contain schema definitions",
                ],
            }

    # Check for model definitions in route files
    if file_analysis["content_type"] == "express_routes":
        if "Schema" in new_code and "mongoose" in new_code:
            return {
                "compatible": False,
                "reason": "Trying to add model schema to a route file",
                "suggestions": [
                    "Move schema definitions to a model file",
                    "Import the model instead of defining it here",
                ],
            }

    return {"compatible": True, "reason": "Modification is compatible"}


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

        # ✅ Pre-validation: Verify file content matches expectations
        print("    🔍 DEBUG: Starting file content verification...")
        verification_result = _verify_file_content_for_modifications(
            file_change.file_path, current_content, modifications
        )

        if not verification_result["valid"]:
            print(
                f"    ❌ File content verification failed: {verification_result['reason']}"
            )
            print("    💡 Suggestions:")
            for suggestion in verification_result.get("suggestions", []):
                print(f"       • {suggestion}")
            return False

        print("    ✅ File content verification passed")

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

                result = str_replace_tool.invoke(
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
