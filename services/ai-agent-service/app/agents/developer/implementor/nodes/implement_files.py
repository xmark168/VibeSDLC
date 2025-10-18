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
                    create_result = create_directory_tool(
                        directory_path=str(file_path.parent),
                        working_directory=working_dir,
                    )
                    print(f"    📁 Directory: {file_path.parent}")

                # Write file content
                result = write_file_tool(
                    file_path=file_change.file_path,
                    content=file_change.content,
                    working_directory=working_dir,
                    create_dirs=True,
                )

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

            except Exception as e:
                error_msg = f"Error creating {file_change.file_path}: {str(e)}"
                errors.append(error_msg)
                print(f"    ❌ Error: {e}")

        # Process files to modify
        for file_change in state.files_to_modify:
            try:
                print(f"  ✏️  Modifying: {file_change.file_path}")

                if file_change.change_type == "incremental":
                    # Use incremental tools for precise changes
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
                    result = write_file_tool(
                        file_path=file_change.file_path,
                        content=file_change.content,
                        working_directory=working_dir,
                    )

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
                result = add_function_tool(
                    file_path=file_change.file_path,
                    function_code=file_change.content,
                    after_function=file_change.target_function,
                    working_directory=working_dir,
                )
            else:
                # Modifying existing function
                changes = [{"type": "replace", "content": file_change.content}]
                result = modify_function_tool(
                    file_path=file_change.file_path,
                    function_name=file_change.target_function,
                    changes=changes,
                    working_directory=working_dir,
                )

        elif file_change.target_class:
            # Class-level modification (add method)
            result = create_method_tool(
                file_path=file_change.file_path,
                class_name=file_change.target_class,
                method_code=file_change.content,
                working_directory=working_dir,
            )

        elif file_change.content.strip().startswith(("import ", "from ")):
            # Import statement
            result = add_import_tool(
                file_path=file_change.file_path,
                import_statement=file_change.content.strip(),
                working_directory=working_dir,
            )

        else:
            # Generic string replacement
            # Read file first to determine what to replace
            read_result = read_file_tool(
                file_path=file_change.file_path, working_directory=working_dir
            )

            if "File not found" in read_result:
                return False

            # Use edit_file_tool for generic replacement
            # This is a fallback - ideally the plan should specify what to replace
            result = edit_file_tool(
                file_path=file_change.file_path,
                old_str="# TODO: Implement",  # Common placeholder
                new_str=file_change.content,
                working_directory=working_dir,
            )

        # Check result
        result_data = json.loads(result)
        return result_data.get("status") == "success"

    except Exception as e:
        print(f"Error in incremental change: {e}")
        return False
