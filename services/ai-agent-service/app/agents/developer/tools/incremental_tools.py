# app/agents/developer/implementor/tools/incremental_tools.py
"""
Incremental Code Editing Tools

Tools for making precise, incremental code changes instead of full rewrites.
Based on the principle of making small, safe edits.
"""

import ast
from pathlib import Path

from langchain_core.tools import tool

# ============================================================================
# PRECISE CODE MODIFICATION TOOLS
# ============================================================================


@tool
def add_function_tool(
    file_path: str,
    function_code: str,
    after_function: str | None = None,
    before_function: str | None = None,
    working_directory: str = ".",
) -> str:
    """
    Add a new function to a file at a specific location.

    Args:
        file_path: Path to the Python file
        function_code: Complete function code to add
        after_function: Add after this function name
        before_function: Add before this function name
        working_directory: Base directory

    Returns:
        Success message or error

    Example:
        add_function_tool(
            "app/utils.py",
            "def new_helper():\n    return 'helper result'",
            after_function="existing_function"
        )
    """
    try:
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied"

        if not full_path.exists():
            return f"Error: File '{file_path}' does not exist"

        # Read current content
        with open(full_path, encoding="utf-8") as f:
            content = f.read()

        # Parse to find function positions
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return f"Error: File has syntax error - {e}"

        # Find function positions
        function_positions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                function_positions[node.name] = node.lineno

        # Determine insertion point
        lines = content.split("\n")
        insertion_line = len(lines)  # Default: end of file

        if after_function and after_function in function_positions:
            # Find the line after the target function ends
            target_line = function_positions[after_function]
            # Find the next function or end of file
            for i in range(target_line, len(lines)):
                if lines[i].strip() == "" or lines[i].startswith("def "):
                    insertion_line = i
                    break
            else:
                insertion_line = len(lines)

        elif before_function and before_function in function_positions:
            insertion_line = function_positions[before_function] - 1

        # Insert the function
        indent = "    "  # Standard 4-space indent
        formatted_function = function_code.strip()

        # Ensure proper formatting
        if not formatted_function.startswith("def "):
            return "Error: function_code must start with 'def '"

        # Add the function with proper spacing
        new_content = lines[:insertion_line]
        if insertion_line > 0 and lines[insertion_line - 1].strip() != "":
            new_content.append("")  # Add blank line before
        new_content.append(formatted_function)
        if insertion_line < len(lines) and lines[insertion_line].strip() != "":
            new_content.append("")  # Add blank line after

        # Add remaining content
        new_content.extend(lines[insertion_line:])

        # Write back
        full_path.write_text("\n".join(new_content), encoding="utf-8")

        location_desc = "at the end"
        if after_function:
            location_desc = f"after function '{after_function}'"
        elif before_function:
            location_desc = f"before function '{before_function}'"

        return f"✅ Successfully added function {location_desc} in '{file_path}'"

    except Exception as e:
        return f"Error adding function: {str(e)}"


@tool
def modify_function_tool(
    file_path: str,
    function_name: str,
    changes: list[dict],
    working_directory: str = ".",
) -> str:
    """
    Make incremental changes to a specific function.

    Args:
        file_path: Path to Python file
        function_name: Name of function to modify
        changes: List of change operations
        working_directory: Base directory

    Change operations format:
        {
            "type": "add_line",
            "line": "    new_line_of_code",
            "after_line": "existing_line_pattern"
        }
        {
            "type": "replace_line",
            "old_pattern": "line_to_replace",
            "new_line": "replacement_line"
        }
        {
            "type": "remove_line",
            "pattern": "line_to_remove"
        }

    Returns:
        Success message or error
    """
    try:
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied"

        if not full_path.exists():
            return f"Error: File '{file_path}' does not exist"

        # Read and parse file
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "Error: File has syntax errors"

        # Find the target function
        target_func = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                target_func = node
                break

        if not target_func:
            return f"Error: Function '{function_name}' not found in file"

        # Get function line range
        start_line = target_func.lineno - 1  # 0-based
        # Find end of function (next function or end of file)
        end_line = start_line
        for i in range(start_line + 1, len(lines)):
            if i >= len(lines):
                break
            line = lines[i]
            # Check if this is the start of another top-level function
            if (
                line.strip().startswith("def ")
                or line.strip().startswith("class ")
                or (
                    line.strip()
                    and i > start_line + 1
                    and not line.startswith(" ")
                    and not line.startswith("\t")
                )
            ):
                # This is likely the start of another top-level definition
                end_line = i - 1
                break
        else:
            end_line = len(lines) - 1

        # Extract function lines
        func_lines = lines[start_line : end_line + 1]

        # Apply changes
        modified_lines = func_lines.copy()
        changes_made = 0

        for change in changes:
            change_type = change.get("type")

            if change_type == "add_line":
                new_line = change["line"]
                after_pattern = change.get("after_line")

                if after_pattern:
                    # Find the line to add after
                    for i, line in enumerate(modified_lines):
                        if after_pattern in line:
                            modified_lines.insert(i + 1, new_line)
                            changes_made += 1
                            break
                else:
                    # Add at the end of function (before return or last line)
                    modified_lines.insert(-1, new_line)
                    changes_made += 1

            elif change_type == "replace_line":
                old_pattern = change["old_pattern"]
                new_line = change["new_line"]

                for i, line in enumerate(modified_lines):
                    if old_pattern in line:
                        modified_lines[i] = new_line
                        changes_made += 1
                        break

            elif change_type == "remove_line":
                pattern = change["pattern"]
                modified_lines = [
                    line for line in modified_lines if pattern not in line
                ]
                changes_made += 1

        if changes_made == 0:
            return "No changes were applied - patterns not found"

        # Replace the function in the original content
        new_content = lines[:start_line] + modified_lines + lines[end_line + 1 :]

        # Write back
        full_path.write_text("\n".join(new_content), encoding="utf-8")

        return f"✅ Successfully applied {changes_made} change(s) to function '{function_name}'"

    except Exception as e:
        return f"Error modifying function: {str(e)}"


@tool
def add_import_tool(
    file_path: str, import_statement: str, working_directory: str = "."
) -> str:
    """
    Add an import statement to a Python file.

    Args:
        file_path: Path to Python file
        import_statement: Import statement to add
        working_directory: Base directory

    Returns:
        Success message or error

    Example:
        add_import_tool("app/main.py", "from fastapi import Depends")
    """
    try:
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied"

        if not full_path.exists():
            return f"Error: File '{file_path}' does not exist"

        # Read content
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        # Find where to insert (after existing imports)
        insert_line = 0
        in_import_section = True

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            if not line_stripped:
                continue

            if line_stripped.startswith("import ") or line_stripped.startswith("from "):
                insert_line = i + 1
            elif (
                line_stripped.startswith("def ")
                or line_stripped.startswith("class ")
                or line_stripped.startswith("@")
            ):
                in_import_section = False
                break
            else:
                # Not an import and not code - might be comments
                if in_import_section:
                    insert_line = i + 1

        # Check if import already exists
        if import_statement in content:
            return f"✅ Import already exists: {import_statement}"

        # Insert the import
        lines.insert(insert_line, import_statement)

        # Write back
        full_path.write_text("\n".join(lines), encoding="utf-8")

        return f"✅ Successfully added import: {import_statement}"

    except Exception as e:
        return f"Error adding import: {str(e)}"


@tool
def create_method_tool(
    file_path: str, class_name: str, method_code: str, working_directory: str = "."
) -> str:
    """
    Add a method to an existing class.

    Args:
        file_path: Path to Python file
        class_name: Name of the class
        method_code: Complete method code
        working_directory: Base directory

    Returns:
        Success message or error

    Example:
        create_method_tool(
            "app/models.py",
            "UserModel",
            "def get_display_name(self):\n    return f'{self.first_name} {self.last_name}'"
        )
    """
    try:
        full_path = Path(working_directory) / file_path
        full_path = full_path.resolve()

        # Security check
        working_dir_resolved = Path(working_directory).resolve()
        if not str(full_path).startswith(str(working_dir_resolved)):
            return "Error: Access denied"

        if not full_path.exists():
            return f"Error: File '{file_path}' does not exist"

        # Read and parse
        with open(full_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return "Error: File has syntax errors"

        # Find the target class
        target_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                target_class = node
                break

        if not target_class:
            return f"Error: Class '{class_name}' not found in file"

        # Find insertion point (end of class)
        class_start = target_class.lineno - 1
        class_end = class_start

        # Find the next class/function or end of file
        for i in range(class_start + 1, len(lines)):
            if i >= len(lines):
                break
            line = lines[i]
            indent_level = len(line) - len(line.lstrip())

            # If we're back to top-level indentation, we've left the class
            if indent_level == 0 and line.strip():
                class_end = i - 1
                break
        else:
            class_end = len(lines) - 1

        # Insert method at the end of class (before the closing)
        insertion_point = class_end
        formatted_method = method_code.strip()

        # Ensure proper indentation
        if not formatted_method.startswith("    def "):
            # Add indentation
            formatted_method = "\n".join(
                ["    " + line for line in formatted_method.split("\n")]
            )

        # Insert with proper spacing
        new_lines = lines[:insertion_point]
        if (
            insertion_point > class_start + 1
            and lines[insertion_point - 1].strip() != ""
        ):
            new_lines.append("")  # Add blank line before method

        new_lines.append(formatted_method)
        new_lines.extend(lines[insertion_point:])

        # Write back
        full_path.write_text("\n".join(new_lines), encoding="utf-8")

        return f"✅ Successfully added method to class '{class_name}'"

    except Exception as e:
        return f"Error creating method: {str(e)}"
