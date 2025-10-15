# app/agents/developer/planner/tools.py
"""
Tools for the DeepAgents Planner

All tools are READ-ONLY for context gathering.
Based on the LangGraph tools but adapted for DeepAgents patterns.
"""

from langchain_core.tools import tool
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
import ast
import json
import re

# Shared scratchpad for notes
_scratchpad_notes: List[str] = []


@tool
def grep_search(pattern: str, path: str = ".", file_pattern: str = "*") -> str:
    """
    Search for a pattern in files using grep/ripgrep.

    Args:
        pattern: The pattern to search for
        path: Directory to search in (default: current directory)
        file_pattern: File pattern to match (e.g., "*.py", "*.ts")

    Returns:
        Search results with file paths and line numbers
    """
    try:
        # Try ripgrep first
        try:
            result = subprocess.run(
                ["rg", pattern, path, "-g", file_pattern, "-n", "--color=never"],
                capture_output=True,
                text=True,
                timeout=30
            )
        except FileNotFoundError:
            # Fallback to grep
            result = subprocess.run(
                ["grep", "-rn", pattern, path, "--include", file_pattern],
                capture_output=True,
                text=True,
                timeout=30
            )

        if result.returncode == 0:
            return result.stdout
        elif result.returncode == 1:
            return "No matches found"
        else:
            return f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds"
    except Exception as e:
        return f"Error executing grep: {str(e)}"


@tool
def view_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    View the contents of a file or specific line range.

    Args:
        file_path: Path to the file to view
        start_line: Optional starting line number (1-indexed)
        end_line: Optional ending line number (1-indexed)

    Returns:
        File contents with line numbers
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not path.is_file():
            return f"Error: '{file_path}' is not a file"

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Apply line range
        if start_line is not None or end_line is not None:
            start = (start_line - 1) if start_line else 0
            end = end_line if end_line else len(lines)
            lines = lines[start:end]
            line_offset = start + 1
        else:
            line_offset = 1

        # Format with line numbers
        formatted_lines = [
            f"{i + line_offset:4d} | {line.rstrip()}"
            for i, line in enumerate(lines)
        ]

        return "\n".join(formatted_lines)
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def shell_execute(command: str) -> str:
    """
    Execute a READ-ONLY shell command.

    SAFETY: Only allows read-only commands (ls, pwd, cat, find, etc.)
    Blocks destructive commands (rm, mv, cp, etc.)

    Args:
        command: Shell command to execute

    Returns:
        Command output
    """
    # Safety check: block dangerous commands
    dangerous_commands = [
        'rm', 'mv', 'cp', 'dd', 'mkfs', 'format',
        'del', 'deltree', 'chmod', 'chown',
        '>', '>>', 'sudo', 'su'
    ]

    command_parts = command.split()
    if command_parts and command_parts[0] in dangerous_commands:
        return f"Error: Command '{command_parts[0]}' is not allowed (read-only mode)"

    # Check for redirection
    if any(op in command for op in ['>', '>>']):
        return "Error: Output redirection is not allowed (read-only mode)"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return output
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


@tool
def list_directory(path: str = ".", show_hidden: bool = False, recursive: bool = False) -> str:
    """
    List directory contents with details.

    Args:
        path: Directory path to list
        show_hidden: Include hidden files
        recursive: List recursively

    Returns:
        Formatted directory listing
    """
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return f"Error: Path '{path}' does not exist"

        if not path_obj.is_dir():
            return f"Error: '{path}' is not a directory"

        files = []
        if recursive:
            for item in path_obj.rglob("*"):
                if not show_hidden and item.name.startswith('.'):
                    continue
                files.append(str(item.relative_to(path_obj)))
        else:
            for item in path_obj.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                files.append(item.name)

        files.sort()
        return "\n".join(files) if files else "Directory is empty"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


@tool
def take_notes(note: str) -> str:
    """
    Take notes about important information discovered during context gathering.

    These notes will be available when generating the final plan and will be
    condensed by the noteTaker subagent.

    Args:
        note: The note to record

    Returns:
        Confirmation message
    """
    global _scratchpad_notes
    _scratchpad_notes.append(note)
    return f"Note recorded. Total notes: {len(_scratchpad_notes)}"


def get_scratchpad_notes() -> List[str]:
    """Get all recorded notes."""
    global _scratchpad_notes
    return _scratchpad_notes.copy()


def clear_scratchpad_notes():
    """Clear all notes (for testing/reset)."""
    global _scratchpad_notes
    _scratchpad_notes.clear()


# ============================================================================
# SPECIALIZED TOOLS FOR PLANNER AGENT
# ============================================================================


@tool
def code_search_tool(
    pattern: str,
    file_extensions: Optional[List[str]] = None,
    search_path: str = ".",
    context_lines: int = 2,
    case_sensitive: bool = False
) -> str:
    """
    Advanced code search tool for finding specific patterns, functions, or classes.

    Use this tool to locate existing code patterns, understand implementation approaches,
    and identify files that may need modification.

    Args:
        pattern: Code pattern to search for (e.g., 'def authenticate', 'class User', 'import jwt')
        file_extensions: List of file extensions to search (e.g., ['py', 'js', 'ts'])
        search_path: Directory to search in (default: current directory)
        context_lines: Number of lines to show before/after match (default: 2)
        case_sensitive: Whether search should be case-sensitive (default: False)

    Returns:
        Detailed search results with file paths, line numbers, and context

    Example:
        code_search_tool(
            pattern="auth",
            file_extensions=["py"],
            search_path="app/",
            context_lines=3
        )
    """
    try:
        # Build ripgrep command
        cmd = ["rg", pattern, search_path, "-n", "--color=never"]

        # Add context lines
        if context_lines > 0:
            cmd.extend(["-C", str(context_lines)])

        # Add case sensitivity
        if not case_sensitive:
            cmd.append("-i")

        # Add file extensions
        if file_extensions:
            for ext in file_extensions:
                cmd.extend(["-g", f"*.{ext.lstrip('.')}"])

        # Try ripgrep first
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
        except FileNotFoundError:
            # Fallback to basic grep
            grep_cmd = ["grep", "-rn"]
            if not case_sensitive:
                grep_cmd.append("-i")
            if context_lines > 0:
                grep_cmd.extend(["-C", str(context_lines)])
            grep_cmd.append(pattern)
            grep_cmd.append(search_path)

            if file_extensions:
                for ext in file_extensions:
                    grep_cmd.extend(["--include", f"*.{ext.lstrip('.')}"])

            result = subprocess.run(
                grep_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

        if result.returncode == 0:
            # Parse and format results
            lines = result.stdout.strip().split('\n')

            # Group results by file
            files_dict: Dict[str, List[str]] = {}
            current_file = None

            for line in lines:
                if ':' in line:
                    parts = line.split(':', 2)
                    if len(parts) >= 2:
                        file_path = parts[0]
                        if file_path not in files_dict:
                            files_dict[file_path] = []
                        files_dict[file_path].append(line)

            # Format output
            output_parts = []
            output_parts.append(f"Found {len(files_dict)} file(s) matching pattern '{pattern}':\n")

            for file_path, matches in files_dict.items():
                output_parts.append(f"\n📄 {file_path}")
                output_parts.append("-" * 80)
                for match in matches[:10]:  # Limit to first 10 matches per file
                    output_parts.append(match)
                if len(matches) > 10:
                    output_parts.append(f"... and {len(matches) - 10} more matches")
                output_parts.append("")

            return "\n".join(output_parts)

        elif result.returncode == 1:
            return f"No matches found for pattern '{pattern}' in {search_path}"
        else:
            return f"Error: {result.stderr}"

    except subprocess.TimeoutExpired:
        return "Error: Search timed out after 30 seconds"
    except Exception as e:
        return f"Error executing code search: {str(e)}"


@tool
def ast_parser_tool(
    file_path: str,
    analysis_type: str = "full"
) -> str:
    """
    Parse Python files using AST to analyze code structure, dependencies, and complexity.

    Use this tool to understand existing code architecture, identify dependencies,
    and analyze the impact of proposed changes.

    Args:
        file_path: Path to the Python file to analyze
        analysis_type: Type of analysis to perform:
            - "full": Complete analysis (classes, functions, imports, complexity)
            - "classes": Class definitions and methods only
            - "functions": Function definitions only
            - "imports": Import statements and dependencies only
            - "structure": High-level structure overview

    Returns:
        Structured analysis of the Python file

    Example:
        ast_parser_tool(
            file_path="app/models/user.py",
            analysis_type="full"
        )
    """
    try:
        path = Path(file_path)

        if not path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not path.suffix == '.py':
            return f"Error: File '{file_path}' is not a Python file"

        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse AST
        try:
            tree = ast.parse(content, filename=str(path))
        except SyntaxError as e:
            return f"Error: Syntax error in file at line {e.lineno}: {e.msg}"

        # Initialize analysis results
        analysis = {
            "file": str(path),
            "imports": [],
            "classes": [],
            "functions": [],
            "complexity": {
                "total_lines": len(content.split('\n')),
                "code_lines": 0,
                "class_count": 0,
                "function_count": 0,
                "max_nesting_depth": 0
            }
        }

        # Analyze based on type
        for node in ast.walk(tree):
            # Import analysis
            if analysis_type in ["full", "imports", "structure"]:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis["imports"].append({
                            "type": "import",
                            "module": alias.name,
                            "alias": alias.asname
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        analysis["imports"].append({
                            "type": "from_import",
                            "module": module,
                            "name": alias.name,
                            "alias": alias.asname
                        })

            # Class analysis
            if analysis_type in ["full", "classes", "structure"]:
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "bases": [_get_name(base) for base in node.bases],
                        "methods": [],
                        "decorators": [_get_name(dec) for dec in node.decorator_list]
                    }

                    # Get methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append({
                                "name": item.name,
                                "line": item.lineno,
                                "args": [arg.arg for arg in item.args.args],
                                "decorators": [_get_name(dec) for dec in item.decorator_list]
                            })

                    analysis["classes"].append(class_info)
                    analysis["complexity"]["class_count"] += 1

            # Function analysis
            if analysis_type in ["full", "functions", "structure"]:
                if isinstance(node, ast.FunctionDef):
                    # Skip methods (already counted in classes)
                    parent = None
                    for parent_node in ast.walk(tree):
                        for child in ast.iter_child_nodes(parent_node):
                            if child is node:
                                parent = parent_node
                                break

                    if not isinstance(parent, ast.ClassDef):
                        func_info = {
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "decorators": [_get_name(dec) for dec in node.decorator_list],
                            "returns": _get_name(node.returns) if node.returns else None
                        }
                        analysis["functions"].append(func_info)
                        analysis["complexity"]["function_count"] += 1

        # Count non-empty lines
        analysis["complexity"]["code_lines"] = sum(
            1 for line in content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        )

        # Format output based on analysis type
        return _format_ast_analysis(analysis, analysis_type)

    except Exception as e:
        return f"Error parsing file: {str(e)}"


def _get_name(node):
    """Helper to extract name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{_get_name(node.value)}.{node.attr}"
    elif isinstance(node, ast.Constant):
        return str(node.value)
    else:
        return ast.unparse(node) if hasattr(ast, 'unparse') else str(node)


def _format_ast_analysis(analysis: Dict[str, Any], analysis_type: str) -> str:
    """Format AST analysis results for readability."""
    output = []
    output.append(f"AST Analysis: {analysis['file']}")
    output.append("=" * 80)
    output.append("")

    # Complexity metrics
    if analysis_type in ["full", "structure"]:
        output.append("📊 Complexity Metrics:")
        output.append(f"  Total Lines: {analysis['complexity']['total_lines']}")
        output.append(f"  Code Lines: {analysis['complexity']['code_lines']}")
        output.append(f"  Classes: {analysis['complexity']['class_count']}")
        output.append(f"  Functions: {analysis['complexity']['function_count']}")
        output.append("")

    # Imports
    if analysis_type in ["full", "imports"] and analysis['imports']:
        output.append("📦 Imports:")
        for imp in analysis['imports'][:20]:  # Limit output
            if imp['type'] == 'import':
                alias_str = f" as {imp['alias']}" if imp['alias'] else ""
                output.append(f"  import {imp['module']}{alias_str}")
            else:
                alias_str = f" as {imp['alias']}" if imp['alias'] else ""
                output.append(f"  from {imp['module']} import {imp['name']}{alias_str}")
        if len(analysis['imports']) > 20:
            output.append(f"  ... and {len(analysis['imports']) - 20} more imports")
        output.append("")

    # Classes
    if analysis_type in ["full", "classes", "structure"] and analysis['classes']:
        output.append("🏛️  Classes:")
        for cls in analysis['classes'][:10]:  # Limit output
            bases_str = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
            output.append(f"  class {cls['name']}{bases_str} (line {cls['line']})")
            if cls['decorators']:
                output.append(f"    Decorators: {', '.join(cls['decorators'])}")
            if cls['methods']:
                output.append(f"    Methods ({len(cls['methods'])}):")
                for method in cls['methods'][:5]:
                    args_str = ', '.join(method['args'])
                    output.append(f"      - {method['name']}({args_str}) (line {method['line']})")
                if len(cls['methods']) > 5:
                    output.append(f"      ... and {len(cls['methods']) - 5} more methods")
            output.append("")
        if len(analysis['classes']) > 10:
            output.append(f"  ... and {len(analysis['classes']) - 10} more classes")
        output.append("")

    # Functions
    if analysis_type in ["full", "functions"] and analysis['functions']:
        output.append("⚙️  Functions:")
        for func in analysis['functions'][:10]:  # Limit output
            args_str = ', '.join(func['args'])
            returns_str = f" -> {func['returns']}" if func['returns'] else ""
            output.append(f"  def {func['name']}({args_str}){returns_str} (line {func['line']})")
            if func['decorators']:
                output.append(f"    Decorators: {', '.join(func['decorators'])}")
        if len(analysis['functions']) > 10:
            output.append(f"  ... and {len(analysis['functions']) - 10} more functions")
        output.append("")

    return "\n".join(output)


@tool
def dependency_analyzer_tool(
    target_path: str,
    analysis_scope: str = "internal",
    depth: int = 2
) -> str:
    """
    Analyze dependencies for a given file, module, or directory.

    Use this tool to map out component relationships, understand the impact
    of changes, and identify potential dependency conflicts.

    Args:
        target_path: Path to file or directory to analyze
        analysis_scope: Scope of dependency analysis:
            - "internal": Internal code dependencies only
            - "external": External library dependencies only
            - "all": Both internal and external dependencies
        depth: Maximum depth for dependency traversal (1-5, default: 2)

    Returns:
        Dependency graph and analysis report

    Example:
        dependency_analyzer_tool(
            target_path="app/agents/developer",
            analysis_scope="all",
            depth=2
        )
    """
    try:
        path = Path(target_path)

        if not path.exists():
            return f"Error: Path '{target_path}' does not exist"

        # Limit depth
        depth = max(1, min(5, depth))

        # Collect Python files
        python_files = []
        if path.is_file() and path.suffix == '.py':
            python_files.append(path)
        elif path.is_dir():
            python_files = list(path.rglob("*.py"))[:50]  # Limit to 50 files
        else:
            return f"Error: '{target_path}' must be a Python file or directory"

        # Initialize dependency tracking
        dependencies = {
            "target": str(path),
            "files_analyzed": len(python_files),
            "internal_deps": {},
            "external_deps": set(),
            "dependency_graph": []
        }

        # Analyze each file
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)
                file_key = str(py_file.relative_to(path.parent) if path.is_dir() else py_file.name)

                file_deps = {
                    "file": file_key,
                    "imports": [],
                    "internal": [],
                    "external": []
                }

                # Extract imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name
                            file_deps["imports"].append(module)

                            # Classify as internal or external
                            if _is_internal_import(module, path):
                                file_deps["internal"].append(module)
                            else:
                                file_deps["external"].append(module)
                                dependencies["external_deps"].add(module.split('.')[0])

                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            full_import = f"{module}.{alias.name}" if module else alias.name
                            file_deps["imports"].append(full_import)

                            # Classify as internal or external
                            if _is_internal_import(module, path):
                                file_deps["internal"].append(full_import)
                            else:
                                file_deps["external"].append(full_import)
                                if module:
                                    dependencies["external_deps"].add(module.split('.')[0])

                # Store in dependency graph
                if analysis_scope == "internal" and file_deps["internal"]:
                    dependencies["dependency_graph"].append(file_deps)
                elif analysis_scope == "external" and file_deps["external"]:
                    dependencies["dependency_graph"].append(file_deps)
                elif analysis_scope == "all":
                    dependencies["dependency_graph"].append(file_deps)

            except Exception as e:
                # Skip files with errors
                continue

        # Format output
        return _format_dependency_analysis(dependencies, analysis_scope)

    except Exception as e:
        return f"Error analyzing dependencies: {str(e)}"


def _is_internal_import(module: str, base_path: Path) -> bool:
    """Determine if an import is internal to the project."""
    if not module:
        return False

    # Check if module starts with common project paths
    internal_prefixes = ['app', 'src', 'lib', 'core', 'services', 'agents']

    # Check relative imports (starting with .)
    if module.startswith('.'):
        return True

    # Check if module matches internal structure
    module_parts = module.split('.')
    if module_parts[0] in internal_prefixes:
        return True

    # Check if module exists in the project directory
    if base_path.is_dir():
        potential_path = base_path / module.replace('.', '/')
        if potential_path.exists() or potential_path.with_suffix('.py').exists():
            return True

    return False


def _format_dependency_analysis(dependencies: Dict[str, Any], scope: str) -> str:
    """Format dependency analysis results for readability."""
    output = []
    output.append(f"Dependency Analysis: {dependencies['target']}")
    output.append("=" * 80)
    output.append(f"Files Analyzed: {dependencies['files_analyzed']}")
    output.append("")

    # External dependencies summary
    if scope in ["external", "all"] and dependencies["external_deps"]:
        output.append("📦 External Dependencies:")
        for dep in sorted(dependencies["external_deps"])[:30]:
            output.append(f"  - {dep}")
        if len(dependencies["external_deps"]) > 30:
            output.append(f"  ... and {len(dependencies['external_deps']) - 30} more")
        output.append("")

    # Dependency graph
    if dependencies["dependency_graph"]:
        output.append("🔗 Dependency Graph:")
        for file_dep in dependencies["dependency_graph"][:15]:  # Limit output
            output.append(f"\n  📄 {file_dep['file']}")

            if scope in ["internal", "all"] and file_dep["internal"]:
                output.append("    Internal Dependencies:")
                for dep in file_dep["internal"][:10]:
                    output.append(f"      → {dep}")
                if len(file_dep["internal"]) > 10:
                    output.append(f"      ... and {len(file_dep['internal']) - 10} more")

            if scope in ["external", "all"] and file_dep["external"]:
                output.append("    External Dependencies:")
                for dep in file_dep["external"][:10]:
                    output.append(f"      → {dep}")
                if len(file_dep["external"]) > 10:
                    output.append(f"      ... and {len(file_dep['external']) - 10} more")

        if len(dependencies["dependency_graph"]) > 15:
            output.append(f"\n  ... and {len(dependencies['dependency_graph']) - 15} more files")

    output.append("")
    output.append("💡 Tip: Use this information to:")
    output.append("  - Identify files that will be affected by changes")
    output.append("  - Detect circular dependencies")
    output.append("  - Plan migration or refactoring efforts")
    output.append("  - Ensure all required packages are installed")

    return "\n".join(output)


# Export tools for DeepAgents
grep_search_tool = grep_search
view_file_tool = view_file
shell_execute_tool = shell_execute
list_directory_tool = list_directory
take_notes_tool = take_notes

# Specialized tools for planner agent
code_search_tool_export = code_search_tool
ast_parser_tool_export = ast_parser_tool
dependency_analyzer_tool_export = dependency_analyzer_tool

# All tools list for easy agent configuration
ALL_TOOLS = [
    grep_search_tool,
    view_file_tool,
    shell_execute_tool,
    list_directory_tool,
    take_notes_tool,
    code_search_tool,
    ast_parser_tool,
    dependency_analyzer_tool
]

# Categorized tool lists
CONTEXT_GATHERING_TOOLS = [
    grep_search_tool,
    view_file_tool,
    list_directory_tool,
    code_search_tool
]

ANALYSIS_TOOLS = [
    ast_parser_tool,
    dependency_analyzer_tool
]

UTILITY_TOOLS = [
    shell_execute_tool,
    take_notes_tool
]
