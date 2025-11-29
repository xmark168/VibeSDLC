"""Code Context Tools - Utilities for gathering code context (MetaGPT-inspired)."""

import logging
from pathlib import Path
from typing import List, Optional

from app.agents.developer_v2.src.tools.cocoindex_tools import get_markdown_code_block_type

logger = logging.getLogger(__name__)


def get_all_workspace_files(
    workspace_path: str,
    max_files: int = 20,
    extensions: List[str] = None
) -> str:
    """Get all source files from workspace as context (MetaGPT WriteCode pattern).
    
    Args:
        workspace_path: Path to the workspace directory
        max_files: Maximum number of files to include
        extensions: File extensions to include (default: common source files)
        
    Returns:
        Markdown-formatted code snippets of all files
    """
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".css", ".html"]
    
    workspace = Path(workspace_path)
    if not workspace.exists():
        return "No workspace files found."
    
    context_parts = []
    file_count = 0
    
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "venv", ".venv"}
    
    for ext in extensions:
        for file_path in workspace.rglob(f"*{ext}"):
            if file_count >= max_files:
                break
            
            if any(part in file_path.parts for part in skip_dirs):
                continue
            
            try:
                relative_path = file_path.relative_to(workspace)
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                
                code_type = get_markdown_code_block_type(str(file_path))
                context_parts.append(
                    f"### File: `{relative_path}`\n```{code_type}\n{content}\n```\n"
                )
                file_count += 1
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                continue
    
    if not context_parts:
        return "No source files found in workspace."
    
    return "\n".join(context_parts)


def get_related_code_context(
    workspace_path: str,
    current_file: str,
    task_files: List[str],
    include_all_src: bool = False
) -> str:
    """Gather related code files for context (MetaGPT-style).
    
    Args:
        workspace_path: Path to the workspace directory
        current_file: The file currently being implemented
        task_files: List of files related to the current task
        include_all_src: If True, include all source files in workspace
        
    Returns:
        Markdown-formatted code snippets of related files
    """
    context_parts = []
    workspace = Path(workspace_path)
    
    files_to_include = set(task_files)
    
    if include_all_src:
        for ext in [".py", ".js", ".ts", ".tsx", ".jsx"]:
            for file_path in workspace.rglob(f"*{ext}"):
                if any(part in file_path.parts for part in 
                       ["node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build"]):
                    continue
                rel_path = str(file_path.relative_to(workspace))
                files_to_include.add(rel_path)
    
    for file in files_to_include:
        file_path = workspace / file
        
        if not file_path.exists():
            continue
            
        try:
            content = file_path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, PermissionError, IOError):
            continue
            
        code_type = get_markdown_code_block_type(file)
        
        if file == current_file:
            context_parts.insert(
                0,
                f"### File to rewrite: `{file}`\n```{code_type}\n{content}\n```\n"
            )
            logger.info(f"Prepare to rewrite `{file}`")
        else:
            context_parts.append(
                f"### File: `{file}`\n```{code_type}\n{content}\n```\n"
            )
    
    return "\n".join(context_parts) if context_parts else "No related files found."


def get_legacy_code(workspace_path: str, exclude_files: Optional[List[str]] = None) -> str:
    """Get all existing source code from workspace (MetaGPT-style).
    
    Args:
        workspace_path: Path to the workspace directory
        exclude_files: Files to exclude from the output
        
    Returns:
        Markdown-formatted code of all source files
    """
    workspace = Path(workspace_path)
    exclude_files = exclude_files or []
    code_parts = []
    
    source_extensions = [".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go"]
    skip_dirs = {"node_modules", "__pycache__", ".git", "venv", ".venv", "dist", "build", ".pytest_cache"}
    
    for ext in source_extensions:
        for file_path in workspace.rglob(f"*{ext}"):
            if any(part in file_path.parts for part in skip_dirs):
                continue
                
            rel_path = str(file_path.relative_to(workspace))
            
            if rel_path in exclude_files:
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8')
                code_type = get_markdown_code_block_type(rel_path)
                code_parts.append(
                    f"### File: `{rel_path}`\n```{code_type}\n{content}\n```\n"
                )
            except (UnicodeDecodeError, PermissionError, IOError):
                continue
    
    return "\n".join(code_parts) if code_parts else "No existing code found."


def format_code_for_context(file_path: str, content: str, is_target: bool = False) -> str:
    """Format a single file's code for inclusion in context.
    
    Args:
        file_path: Path to the file
        content: File content
        is_target: If True, mark as file to be written/modified
        
    Returns:
        Markdown-formatted code block
    """
    code_type = get_markdown_code_block_type(file_path)
    header = "### File to rewrite:" if is_target else "### File:"
    return f"{header} `{file_path}`\n```{code_type}\n{content}\n```\n"
