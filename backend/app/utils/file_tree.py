"""File tree building utilities."""

from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel


class FileNode(BaseModel):
    """File tree node representation."""
    name: str
    type: str  # 'file' or 'folder'
    path: str
    size: Optional[int] = None
    modified: Optional[str] = None
    children: List['FileNode'] = []


def build_file_tree(folder: Path, relative_path: str = "", max_depth: int = 5) -> FileNode:
    """Recursively build file tree structure.
    
    Args:
        folder: Path to the folder to traverse
        relative_path: Relative path from project root
        max_depth: Maximum depth to traverse (prevents infinite recursion)
        
    Returns:
        FileNode tree structure
    """
    if max_depth <= 0:
        return FileNode(
            name=folder.name or "root",
            type="folder",
            path=relative_path or "/",
            children=[],
        )

    children = []

    try:
        # Sort: folders first, then files, alphabetically
        items = sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))

        for item in items:
            item_relative_path = f"{relative_path}/{item.name}" if relative_path else item.name

            if item.is_dir():
                # Skip hidden folders and common ignored directories
                if item.name.startswith(".") or item.name in [
                    "node_modules", "__pycache__", ".git", ".venv", "venv",
                    "dist", "build", ".next", ".nuxt", "coverage"
                ]:
                    continue

                child_node = build_file_tree(item, item_relative_path, max_depth - 1)
                children.append(child_node)
                
            else:
                # Skip hidden files
                if item.name.startswith("."):
                    continue

                stat = item.stat()
                children.append(FileNode(
                    name=item.name,
                    type="file",
                    path=item_relative_path,
                    size=stat.st_size,
                    modified=str(stat.st_mtime),
                ))

    except PermissionError:
        pass  # Skip inaccessible directories

    return FileNode(
        name=folder.name or "root",
        type="folder",
        path=relative_path or "/",
        children=children,
    )


def get_file_tree_json(root: Path, max_depth: int = 5) -> dict:
    """Get file tree as JSON-serializable dictionary.
    
    Args:
        root: Root directory path
        max_depth: Maximum depth to traverse
        
    Returns:
        Dictionary representation of file tree
    """
    tree = build_file_tree(root, "", max_depth)
    return tree.model_dump()


def filter_file_tree(node: FileNode, extensions: Optional[List[str]] = None) -> FileNode:
    """Filter file tree to only include specific file extensions.
    
    Args:
        node: Root file node
        extensions: List of file extensions to include (e.g., ['.py', '.js'])
        
    Returns:
        Filtered file tree
    """
    if node.type == "file":
        if extensions and not any(node.name.endswith(ext) for ext in extensions):
            return None
        return node
    
    # Filter children recursively
    filtered_children = []
    for child in node.children:
        filtered_child = filter_file_tree(child, extensions)
        if filtered_child:
            filtered_children.append(filtered_child)
    
    # Only return folder if it has children or no filter
    if filtered_children or not extensions:
        return FileNode(
            name=node.name,
            type=node.type,
            path=node.path,
            children=filtered_children,
        )
    
    return None


def count_files(node: FileNode) -> int:
    """Count total number of files in tree.
    
    Args:
        node: Root file node
        
    Returns:
        Total file count
    """
    if node.type == "file":
        return 1
    
    return sum(count_files(child) for child in node.children)


def get_total_size(node: FileNode) -> int:
    """Calculate total size of all files in tree.
    
    Args:
        node: Root file node
        
    Returns:
        Total size in bytes
    """
    if node.type == "file":
        return node.size or 0
    
    return sum(get_total_size(child) for child in node.children)
