"""Filesystem Tools - Glob, Grep, Read, LS for agents."""

import fnmatch
import logging
import re
from pathlib import Path
from uuid import UUID

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Config files that should not be overwritten if they exist
CONFIG_FILES = {
    "jest.config.js", "jest.config.ts", "jest.config.mjs",
    "playwright.config.ts", "playwright.config.js",
    "vitest.config.ts", "vitest.config.js",
    "tsconfig.json", "package.json",
}

# Tool context - set before invoking tools
_tool_context = {
    "project_id": None,
    "workspace_path": None,
}


def set_tool_context(project_id: str = None, workspace_path: str = None):
    """Set global context for tools. Called by nodes before agent invocation."""
    if project_id:
        _tool_context["project_id"] = project_id
    if workspace_path:
        _tool_context["workspace_path"] = workspace_path


def _get_workspace_path() -> Path | None:
    """Get workspace path from context (preferred) or fallback to database."""
    # Prefer workspace_path from context (worktree)
    if _tool_context.get("workspace_path"):
        return Path(_tool_context["workspace_path"])
    
    # Fallback: query from database
    project_id = _tool_context.get("project_id")
    if project_id:
        return _get_project_path_from_db(project_id)
    
    return None


def _get_project_path_from_db(project_id: str) -> Path | None:
    """Get project path from database."""
    from sqlmodel import Session

    from app.core.db import engine
    from app.models import Project

    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            return Path(project.project_path)
    return None


@tool
def glob_files(
    project_id: str, patterns: list[str], exclude_patterns: list[str] = None
) -> str:
    """Search for files matching glob patterns.

    Call this when:
    - Need to find files by extension or name pattern
    - Exploring project structure
    - Finding all files of a type (e.g., all .tsx files)

    Args:
        project_id: The project UUID
        patterns: List of glob patterns (e.g., ["**/*.ts", "**/*.tsx"])
        exclude_patterns: Patterns to exclude (e.g., ["node_modules/**"])

    Returns:
        List of matching file paths
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        exclude_patterns = exclude_patterns or [
            "node_modules/**",
            ".next/**",
            "__pycache__/**",
            ".git/**",
        ]

        matched_files = []
        for pattern in patterns:
            for file_path in project_path.glob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(project_path)
                    # Check excludes
                    excluded = any(
                        fnmatch.fnmatch(str(rel_path), exc) for exc in exclude_patterns
                    )
                    if not excluded:
                        matched_files.append(str(rel_path))

        # Deduplicate and sort
        matched_files = sorted(set(matched_files))

        if not matched_files:
            return f"No files found matching patterns: {patterns}"

        result = [f"Found {len(matched_files)} files:"]
        for f in matched_files[:50]:
            result.append(f"  {f}")

        if len(matched_files) > 50:
            result.append(f"  ... and {len(matched_files) - 50} more")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"[glob_files] Error: {e}")
        return f"Error: {str(e)}"


@tool
def grep_files(
    project_id: str,
    pattern: str,
    file_pattern: str = "**/*",
    case_insensitive: bool = False,
    context_lines: int = 0,
) -> str:
    """Search for text pattern in files.

    Call this when:
    - Need to find code containing specific text
    - Searching for function/class definitions
    - Finding usages of a variable/function

    Args:
        project_id: The project UUID
        pattern: Regex pattern to search for
        file_pattern: Glob pattern for files to search (default: all files)
        case_insensitive: Whether to ignore case
        context_lines: Number of lines before/after match to show

    Returns:
        Matching lines with file paths and line numbers
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        exclude_dirs = {"node_modules", ".next", "__pycache__", ".git", "dist", "build"}
        flags = re.IGNORECASE if case_insensitive else 0
        regex = re.compile(pattern, flags)

        matches = []

        for file_path in project_path.glob(file_pattern):
            if not file_path.is_file():
                continue

            # Skip excluded directories
            if any(exc in file_path.parts for exc in exclude_dirs):
                continue

            # Skip binary files
            if file_path.suffix in {".png", ".jpg", ".ico", ".woff", ".ttf", ".lock"}:
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.split("\n")
                rel_path = file_path.relative_to(project_path)

                for i, line in enumerate(lines):
                    if regex.search(line):
                        # Get context
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)

                        if context_lines > 0:
                            context = "\n".join(
                                f"    {j + 1}: {lines[j]}" for j in range(start, end)
                            )
                            matches.append(f"{rel_path}:{i + 1}\n{context}")
                        else:
                            matches.append(f"{rel_path}:{i + 1}: {line.strip()[:100]}")

                        if len(matches) >= 30:
                            break
            except Exception:
                continue

            if len(matches) >= 30:
                break

        if not matches:
            return f"No matches found for pattern: {pattern}"

        result = [f"Found {len(matches)} matches:"]
        result.extend(matches)

        if len(matches) >= 30:
            result.append("... (truncated at 30 matches)")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"[grep_files] Error: {e}")
        return f"Error: {str(e)}"


@tool
def read_file(
    project_id: str, file_path: str, offset: int = 0, limit: int = 200
) -> str:
    """Read content of a file.

    Call this when:
    - Need to see file contents
    - Analyzing code implementation
    - Understanding how something works

    Args:
        project_id: The project UUID
        file_path: Relative path to the file
        offset: Line number to start from (0-based)
        limit: Maximum number of lines to read

    Returns:
        File content with line numbers
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        full_path = project_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        if not full_path.is_file():
            return f"Not a file: {file_path}"

        content = full_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.split("\n")
        total_lines = len(lines)

        # Apply offset and limit
        selected_lines = lines[offset : offset + limit]

        result = [f"File: {file_path} ({total_lines} lines)"]
        if offset > 0:
            result.append(
                f"Showing lines {offset + 1}-{min(offset + limit, total_lines)}"
            )
        result.append("---")

        for i, line in enumerate(selected_lines):
            line_num = offset + i + 1
            result.append(f"{line_num:4d} | {line}")

        if offset + limit < total_lines:
            result.append(f"--- ({total_lines - offset - limit} more lines)")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"[read_file] Error: {e}")
        return f"Error: {str(e)}"


@tool
def write_file(project_id: str, file_path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed.

    Call this when:
    - Creating new test files
    - Writing generated code to disk

    Args:
        project_id: The project UUID
        file_path: Relative path to the file
        content: Content to write

    Returns:
        Confirmation message
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        full_path = project_path / file_path

        # Check if trying to overwrite protected config file
        file_name = Path(file_path).name
        if file_name in CONFIG_FILES and full_path.exists():
            return (
                f"⚠️ BLOCKED: {file_name} already exists in project. "
                f"Do NOT create duplicate config files. "
                f"Only create TEST files (.test.ts, .spec.ts)."
            )

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        full_path.write_text(content, encoding="utf-8")

        logger.info(f"[write_file] Wrote {len(content)} chars to {full_path}")
        return f"Successfully wrote {len(content)} chars to {file_path}"

    except Exception as e:
        logger.error(f"[write_file] Error: {e}")
        return f"Error writing file: {str(e)}"


@tool
def edit_file(project_id: str, file_path: str, old_str: str, new_str: str) -> str:
    """Edit a file by replacing text. Use for surgical edits.

    Call this when:
    - Adding tests to existing file
    - Fixing code in a file
    - Replacing specific content

    Args:
        project_id: The project UUID
        file_path: Relative path to the file
        old_str: Exact text to find and replace
        new_str: Text to replace with

    Returns:
        Confirmation message
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        full_path = project_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        content = full_path.read_text(encoding="utf-8")

        if old_str not in content:
            return f"Text not found in {file_path}. Use read_file to check content."

        # Count occurrences
        count = content.count(old_str)
        if count > 1:
            return f"Found {count} occurrences. Please provide more context to match exactly one."

        # Replace
        new_content = content.replace(old_str, new_str, 1)
        full_path.write_text(new_content, encoding="utf-8")

        return f"Successfully edited {file_path}"

    except Exception as e:
        logger.error(f"[edit_file] Error: {e}")
        return f"Error editing file: {str(e)}"


@tool
def list_directory(
    project_id: str, dir_path: str = "", show_hidden: bool = False
) -> str:
    """List contents of a directory.

    Call this when:
    - Need to see what's in a folder
    - Exploring project structure
    - Finding files/subdirectories

    Args:
        project_id: The project UUID
        dir_path: Relative path to directory (empty = project root)
        show_hidden: Whether to show hidden files (starting with .)

    Returns:
        List of files and directories
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."

        target_path = project_path / dir_path if dir_path else project_path

        if not target_path.exists():
            return f"Directory not found: {dir_path or '/'}"

        if not target_path.is_dir():
            return f"Not a directory: {dir_path}"

        entries = []
        for entry in sorted(target_path.iterdir()):
            name = entry.name

            # Skip hidden unless requested
            if name.startswith(".") and not show_hidden:
                continue

            # Skip common ignored directories
            if name in {"node_modules", "__pycache__", ".git", ".next", "dist"}:
                continue

            if entry.is_dir():
                entries.append(f"📁 {name}/")
            else:
                size = entry.stat().st_size
                size_str = f"{size:,}" if size < 10000 else f"{size // 1024}K"
                entries.append(f"📄 {name} ({size_str})")

        if not entries:
            return f"Directory is empty: {dir_path or '/'}"

        result = [f"Directory: {dir_path or '/'} ({len(entries)} items)"]
        result.append("---")
        result.extend(entries[:100])

        if len(entries) > 100:
            result.append(f"... and {len(entries) - 100} more")

        return "\n".join(result)

    except Exception as e:
        logger.error(f"[list_directory] Error: {e}")
        return f"Error: {str(e)}"


@tool
def get_project_structure(project_id: str, max_depth: int = 3) -> str:
    """Get a quick overview of the project structure.
    
    Call this FIRST to understand the project layout before exploring.
    Shows main folders, key files, and test locations.
    
    Args:
        project_id: The project UUID
        max_depth: Maximum folder depth to show (default 3)
    
    Returns:
        Tree-like structure of the project with key files highlighted
    """
    try:
        project_path = _get_workspace_path()
        if not project_path:
            return "Project path not configured."
        
        # Folders to skip
        skip_dirs = {
            "node_modules", ".next", ".git", "__pycache__", 
            ".swc", "dist", "build", ".cocoindex_temp", "coverage"
        }
        
        # Key files to highlight
        key_files = {
            "package.json", "tsconfig.json", "jest.config.ts", "jest.config.js",
            "playwright.config.ts", "jest.setup.ts", "jest.setup.js",
            "prisma/schema.prisma", ".env.example"
        }
        
        result = [f"📁 {project_path.name}/"]
        
        def walk_dir(path: Path, prefix: str = "", depth: int = 0):
            if depth >= max_depth:
                return
            
            try:
                items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            except PermissionError:
                return
            
            # Separate dirs and files
            dirs = [x for x in items if x.is_dir() and x.name not in skip_dirs]
            files = [x for x in items if x.is_file()]
            
            # Show important files first
            for f in files:
                rel_path = f.relative_to(project_path)
                marker = "⭐" if str(rel_path) in key_files or f.name in key_files else "📄"
                result.append(f"{prefix}{marker} {f.name}")
            
            # Then directories
            for i, d in enumerate(dirs):
                is_last = (i == len(dirs) - 1)
                connector = "└── " if is_last else "├── "
                
                # Special markers for test directories
                if d.name in ("tests", "test", "__tests__", "e2e"):
                    result.append(f"{prefix}{connector}🧪 {d.name}/")
                elif d.name == "src":
                    result.append(f"{prefix}{connector}📦 {d.name}/")
                else:
                    result.append(f"{prefix}{connector}📁 {d.name}/")
                
                # Recurse
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk_dir(d, new_prefix, depth + 1)
        
        walk_dir(project_path)
        
        # Add summary
        result.append("\n--- Summary ---")
        
        # Count test files
        test_files = list(project_path.glob("**/*.test.ts")) + list(project_path.glob("**/*.test.js"))
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        
        spec_files = list(project_path.glob("**/*.spec.ts")) + list(project_path.glob("**/*.spec.js"))
        spec_files = [f for f in spec_files if "node_modules" not in str(f)]
        
        result.append(f"Integration tests (*.test.ts): {len(test_files)}")
        result.append(f"E2E tests (*.spec.ts): {len(spec_files)}")
        
        # Check for test config with warnings
        result.append("\n--- ⚠️ Config Status (DO NOT CREATE NEW) ---")
        if (project_path / "jest.config.ts").exists():
            result.append("⚠️ jest.config.ts EXISTS - DO NOT create jest.config.*")
        elif (project_path / "jest.config.js").exists():
            result.append("⚠️ jest.config.js EXISTS - DO NOT create jest.config.*")
        else:
            result.append("Jest: Not configured")
        
        if (project_path / "playwright.config.ts").exists():
            result.append("⚠️ playwright.config.ts EXISTS - DO NOT create playwright.config.*")
        else:
            result.append("Playwright: Not configured")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"[get_project_structure] Error: {e}")
        return f"Error: {str(e)}"


# Tool registry
FILESYSTEM_TOOLS = [
    glob_files,
    grep_files,
    read_file,
    list_directory,
    write_file,
    edit_file,
    get_project_structure,
]


def get_filesystem_tools():
    """Get list of filesystem tools."""
    return FILESYSTEM_TOOLS
