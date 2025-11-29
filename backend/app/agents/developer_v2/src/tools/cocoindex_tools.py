"""CocoIndex Tools - Semantic search and project context utilities."""

import json
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


# =============================================================================
# GLOBAL CONTEXT
# =============================================================================

_tool_context = {
    "project_id": None,
    "task_id": None,
    "workspace_path": None,
}


def set_tool_context(project_id: str = None, task_id: str = None, workspace_path: str = None):
    """Set global context for tools. Called by nodes before agent invocation."""
    if project_id:
        _tool_context["project_id"] = project_id
    if task_id:
        _tool_context["task_id"] = task_id
    if workspace_path:
        _tool_context["workspace_path"] = workspace_path


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_markdown_code_block_type(filename: str) -> str:
    """Get markdown code block type from filename extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Markdown code block language identifier
    """
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".html": "html",
        ".css": "css",
        ".sql": "sql",
        ".sh": "bash",
        ".md": "markdown",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
    }
    ext = Path(filename).suffix.lower()
    return ext_map.get(ext, "")


# =============================================================================
# COCOINDEX SEMANTIC SEARCH
# =============================================================================

def search_codebase(project_id: str, query: str, top_k: int = 5, task_id: str = None) -> str:
    """Search codebase using CocoIndex semantic search.

    Args:
        project_id: Project identifier
        query: Natural language query (e.g., "authentication logic", "user model")
        top_k: Maximum number of results to return
        task_id: Optional task ID for task-specific search
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            results = project_manager.search_task(project_id, task_id, query, top_k=top_k)
        else:
            results = project_manager.search(project_id, query, top_k=top_k)
        
        if not results:
            return "No relevant code found."
        
        # Format results as markdown
        formatted = []
        for r in results:
            score_pct = int(r.get("score", 0) * 100)
            code_type = get_markdown_code_block_type(r['filename'])
            formatted.append(
                f"### {r['filename']} (Relevance: {score_pct}%)\n"
                f"```{code_type}\n{r['code']}\n```\n"
            )
        
        return "\n".join(formatted)
        
    except ImportError as e:
        logger.warning(f"CocoIndex not available: {e}")
        return "CocoIndex not available."
    except Exception as e:
        logger.error(f"Codebase search error: {e}")
        return f"Search error: {str(e)}"


def index_workspace(project_id: str, workspace_path: str, task_id: str = None) -> bool:
    """Index workspace using CocoIndex.
    
    Creates vector embeddings for all source files in the workspace,
    enabling fast semantic search later.
    
    Args:
        project_id: Project identifier
        workspace_path: Path to workspace directory
        task_id: Optional task ID for task-specific indexing
        
    Returns:
        True if indexing successful, False otherwise
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            project_manager.register_task(project_id, task_id, workspace_path)
            logger.info(f"Indexed task workspace: {project_id}/{task_id}")
        else:
            project_manager.register_project(project_id, workspace_path)
            logger.info(f"Indexed project workspace: {project_id}")
        return True
    except ImportError as e:
        logger.warning(f"CocoIndex not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return False


async def update_workspace_index(project_id: str, task_id: str = None) -> bool:
    """Re-index workspace after code changes.
    
    Should be called after implementing code changes to keep
    the search index up-to-date.
    
    Args:
        project_id: Project identifier
        task_id: Optional task ID for task-specific update
        
    Returns:
        True if update successful, False otherwise
    """
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            await project_manager.update_task(project_id, task_id)
            logger.info(f"Updated task index: {project_id}/{task_id}")
        else:
            await project_manager.update_project(project_id)
            logger.info(f"Updated project index: {project_id}")
        return True
    except ImportError as e:
        logger.warning(f"CocoIndex not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Index update error: {e}")
        return False


def get_related_code_indexed(
    project_id: str,
    current_file: str,
    task_description: str,
    top_k: int = 5,
    task_id: str = None
) -> str:
    """Get related code context using CocoIndex semantic search.
    
    Replacement for get_related_code_context() that uses semantic search
    instead of importing all files. Much more efficient for large codebases.
    
    Args:
        project_id: Project identifier
        current_file: File being implemented (for context)
        task_description: Description of what's being implemented
        top_k: Number of relevant chunks to retrieve
        task_id: Optional task ID for task-specific search
        
    Returns:
        Markdown-formatted related code snippets
    """
    # Build semantic query from task context
    query = f"{task_description} related to {current_file}"
    
    return search_codebase(
        project_id=project_id,
        query=query,
        top_k=top_k,
        task_id=task_id
    )


# =============================================================================
# LANGCHAIN @TOOL DECORATED TOOLS
# =============================================================================

@tool
def search_codebase_tool(query: str, top_k: int = 5) -> str:
    """Search codebase using semantic search to find relevant code.

    Args:
        query: Natural language query (e.g., "authentication logic", "user model")
        top_k: Maximum number of results to return
    """
    project_id = _tool_context.get("project_id")
    task_id = _tool_context.get("task_id")
    
    if not project_id:
        return "Error: project_id not set in tool context"
    
    return search_codebase(project_id, query, top_k, task_id)


@tool
def reindex_workspace() -> str:
    """Reindex the workspace to update the semantic search index.
    
    Call this after making file changes to ensure search results are up-to-date.
    """
    project_id = _tool_context.get("project_id")
    task_id = _tool_context.get("task_id")
    workspace_path = _tool_context.get("workspace_path")
    
    if not project_id or not workspace_path:
        return "Error: project_id or workspace_path not set in tool context"
    
    try:
        from app.agents.developer.project_manager import project_manager
        
        if task_id:
            project_manager.register_task(project_id, task_id, workspace_path)
        else:
            project_manager.register_project(project_id, workspace_path)
        
        return f"Successfully reindexed workspace: {workspace_path}"
        
    except ImportError as e:
        return f"CocoIndex not available: {e}"
    except Exception as e:
        return f"Reindex error: {str(e)}"


@tool
def get_related_code(query: str, top_k: int = 5) -> str:
    """Search for code related to the current task using semantic search.

    Args:
        query: Description of what code you're looking for
        top_k: Maximum number of results to return
    """
    project_id = _tool_context.get("project_id")
    task_id = _tool_context.get("task_id")
    
    if not project_id:
        return "Error: project_id not set in tool context"
    
    return search_codebase(project_id, query, top_k, task_id)


@tool
def get_project_structure() -> str:
    """Get the project structure including framework, router type, and conventions.
    
    Use this to understand the project layout before generating code.
    """
    workspace_path = _tool_context.get("workspace_path")
    
    if not workspace_path:
        return "Error: workspace_path not set in tool context"
    
    structure = detect_project_structure(workspace_path)
    
    parts = []
    parts.append(f"Framework: {structure.get('framework', 'unknown')}")
    if structure.get("router_type"):
        parts.append(f"Router Type: {structure['router_type']}")
    if structure.get("conventions"):
        parts.append(f"Conventions: {structure['conventions']}")
    if structure.get("key_dirs"):
        parts.append(f"Key Directories: {', '.join(structure['key_dirs'])}")
    if structure.get("existing_pages"):
        parts.append(f"Existing Pages: {', '.join(structure['existing_pages'][:10])}")
    if structure.get("directory_tree"):
        parts.append(f"\nDirectory Tree:\n{structure['directory_tree']}")
    
    return "\n".join(parts)


@tool
def get_coding_guidelines() -> str:
    """Get the project's coding guidelines from AGENTS.md."""
    workspace_path = _tool_context.get("workspace_path")
    
    if not workspace_path:
        return "Error: workspace_path not set in tool context"
    
    content = get_agents_md(workspace_path)
    return content if content else "No AGENTS.md found in project"


@tool
def get_code_examples(task_type: str = "page") -> str:
    """Get existing code examples from the project as reference.

    Args:
        task_type: Type of code to find examples for (page, component, api, layout)
    """
    workspace_path = _tool_context.get("workspace_path")
    
    if not workspace_path:
        return "Error: workspace_path not set in tool context"
    
    return get_boilerplate_examples(workspace_path, task_type)


@tool
def get_project_info() -> str:
    """Get comprehensive project context including structure and guidelines.
    
    Combines project structure, AGENTS.md, and directory tree.
    """
    workspace_path = _tool_context.get("workspace_path")
    
    if not workspace_path:
        return "Error: workspace_path not set in tool context"
    
    return get_project_context(workspace_path)


# =============================================================================
# PROJECT STRUCTURE DETECTION
# =============================================================================

def detect_project_structure(workspace_path: str) -> dict:
    """Detect project structure and conventions automatically.
    
    Analyzes the workspace to determine framework, router type, and conventions.
    This allows the agent to generate code that follows existing patterns.
    
    Args:
        workspace_path: Path to the workspace directory
        
    Returns:
        Dict with framework info, router type, key directories, and conventions
    """
    workspace = Path(workspace_path)
    
    result = {
        "framework": "unknown",
        "router_type": None,
        "key_dirs": [],
        "existing_pages": [],
        "conventions": "",
        "directory_tree": ""
    }
    
    if not workspace.exists():
        return result
    
    # Detect framework from package.json
    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding='utf-8'))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            
            # NextJS detection
            if "next" in deps:
                result["framework"] = "nextjs"
                version = deps.get("next", "").replace("^", "").replace("~", "")
                
                # Detect App Router vs Pages Router
                app_dir = workspace / "app"
                pages_dir = workspace / "pages"
                src_app_dir = workspace / "src" / "app"
                src_pages_dir = workspace / "src" / "pages"
                
                if app_dir.exists() or src_app_dir.exists():
                    result["router_type"] = "app"
                    base_dir = app_dir if app_dir.exists() else src_app_dir
                    base_path = str(base_dir.relative_to(workspace))
                    result["conventions"] = f"App Router - pages in {base_path}/ (see AGENTS.md for details)"
                    
                    # Find existing pages
                    for page_file in base_dir.rglob("page.tsx"):
                        result["existing_pages"].append(str(page_file.relative_to(workspace)))
                    for page_file in base_dir.rglob("page.jsx"):
                        result["existing_pages"].append(str(page_file.relative_to(workspace)))
                        
                elif pages_dir.exists() or src_pages_dir.exists():
                    result["router_type"] = "pages"
                    base_dir = pages_dir if pages_dir.exists() else src_pages_dir
                    result["conventions"] = f"Pages Router - pages in {base_dir.relative_to(workspace)}/ (see AGENTS.md)"
                else:
                    result["router_type"] = "app"
                    result["conventions"] = "See AGENTS.md for conventions"
                    
            # React detection
            elif "react" in deps and "next" not in deps:
                result["framework"] = "react"
                result["conventions"] = "See AGENTS.md for conventions"
                
            # Vue detection
            elif "vue" in deps:
                result["framework"] = "vue"
                result["conventions"] = "See AGENTS.md for conventions"
                
        except Exception:
            pass
    
    # Python project detection
    pyproject = workspace / "pyproject.toml"
    requirements = workspace / "requirements.txt"
    if pyproject.exists() or requirements.exists():
        if result["framework"] == "unknown":
            result["framework"] = "python"
            result["conventions"] = "See AGENTS.md for conventions"
    
    # Detect key directories
    key_dirs_to_check = ["app", "src", "components", "lib", "utils", "pages", "styles", "public", "api"]
    for dir_name in key_dirs_to_check:
        dir_path = workspace / dir_name
        if dir_path.exists() and dir_path.is_dir():
            result["key_dirs"].append(dir_name)
        # Also check in src/
        src_dir_path = workspace / "src" / dir_name
        if src_dir_path.exists() and src_dir_path.is_dir():
            result["key_dirs"].append(f"src/{dir_name}")
    
    # Generate directory tree (limited depth)
    result["directory_tree"] = _generate_directory_tree(workspace, max_depth=3)
    
    return result


def _generate_directory_tree(directory: Path, max_depth: int = 3, prefix: str = "") -> str:
    """Generate a directory tree string.
    
    Args:
        directory: Root directory
        max_depth: Maximum depth to traverse
        prefix: Prefix for formatting
        
    Returns:
        Formatted directory tree string
    """
    if max_depth <= 0:
        return ""
    
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "venv", ".venv", ".cache"}
    
    lines = []
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        for i, item in enumerate(items):
            if item.name.startswith('.') and item.name not in ['.env.example']:
                continue
            if item.name in skip_dirs:
                continue
                
            is_last = i == len(items) - 1
            connector = "└── " if is_last else "├── "
            
            if item.is_dir():
                lines.append(f"{prefix}{connector}{item.name}/")
                extension = "    " if is_last else "│   "
                subtree = _generate_directory_tree(item, max_depth - 1, prefix + extension)
                if subtree:
                    lines.append(subtree)
            else:
                # Only show important files at top level
                if max_depth >= 2 or item.suffix in ['.tsx', '.ts', '.jsx', '.js', '.py', '.json']:
                    lines.append(f"{prefix}{connector}{item.name}")
    except PermissionError:
        pass
    
    return "\n".join(lines)


def get_agents_md(workspace_path: str) -> str:
    """Read AGENTS.md from workspace if it exists.
    
    Args:
        workspace_path: Path to the workspace directory
        
    Returns:
        Content of AGENTS.md or empty string
    """
    workspace = Path(workspace_path)
    agents_md = workspace / "AGENTS.md"
    
    if agents_md.exists():
        try:
            return agents_md.read_text(encoding='utf-8')
        except Exception:
            pass
    
    return ""


def get_project_context(workspace_path: str) -> str:
    """Get comprehensive project context including structure and guidelines.
    
    Combines project structure detection, AGENTS.md, and directory tree
    to provide full context for the agent.
    
    Args:
        workspace_path: Path to the workspace directory
        
    Returns:
        Formatted project context string
    """
    structure = detect_project_structure(workspace_path)
    agents_md = get_agents_md(workspace_path)
    
    context_parts = []
    
    # Project structure info
    if structure["framework"] != "unknown":
        context_parts.append(f"FRAMEWORK: {structure['framework']}")
        if structure["router_type"]:
            context_parts.append(f"ROUTER TYPE: {structure['router_type']}")
        if structure["conventions"]:
            context_parts.append(f"CONVENTIONS: {structure['conventions']}")
    
    # Key directories
    if structure["key_dirs"]:
        context_parts.append(f"KEY DIRECTORIES: {', '.join(structure['key_dirs'])}")
    
    # Existing pages (important for NextJS)
    if structure["existing_pages"]:
        context_parts.append(f"EXISTING PAGES: {', '.join(structure['existing_pages'][:10])}")
    
    # Directory tree
    if structure["directory_tree"]:
        context_parts.append(f"\nDIRECTORY STRUCTURE:\n{structure['directory_tree']}")
    
    # AGENTS.md content (full - contains important conventions, examples, structure)
    if agents_md:
        context_parts.append(f"\nPROJECT GUIDELINES (AGENTS.md - MUST FOLLOW):\n{agents_md}")
    
    return "\n".join(context_parts)


def get_boilerplate_examples(workspace_path: str, task_type: str = "page") -> str:
    """Get existing code examples from the project as boilerplate reference.
    
    Finds existing pages/components in the project and returns them as examples
    for the agent to follow when generating new code.
    
    Args:
        workspace_path: Path to the workspace directory
        task_type: Type of code to find examples for ("page", "component", "api")
        
    Returns:
        Markdown-formatted code examples from the project
    """
    workspace = Path(workspace_path)
    examples = []
    
    if not workspace.exists():
        return ""
    
    # Define patterns based on task type
    patterns = {
        "page": ["**/page.tsx", "**/page.jsx", "**/pages/*.tsx", "**/pages/*.jsx"],
        "component": ["**/components/*.tsx", "**/components/*.jsx", "**/src/components/*.tsx"],
        "api": ["**/api/**/route.ts", "**/api/**/route.js", "**/pages/api/*.ts"],
        "layout": ["**/layout.tsx", "**/layout.jsx"],
    }
    
    skip_dirs = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "venv", ".venv"}
    
    # Get patterns for the task type
    search_patterns = patterns.get(task_type, patterns["page"])
    
    for pattern in search_patterns:
        for file_path in workspace.glob(pattern):
            # Skip excluded directories
            if any(part in file_path.parts for part in skip_dirs):
                continue
            
            # Limit to 2 examples
            if len(examples) >= 2:
                break
            
            try:
                content = file_path.read_text(encoding='utf-8')
                # Truncate large files
                if len(content) > 1500:
                    content = content[:1500] + "\n// ... (truncated)"
                
                rel_path = file_path.relative_to(workspace)
                code_type = "tsx" if file_path.suffix in [".tsx", ".ts"] else "jsx"
                examples.append(f"### Example: {rel_path}\n```{code_type}\n{content}\n```")
            except Exception:
                continue
    
    if examples:
        return "## EXISTING CODE EXAMPLES (Follow this style!):\n" + "\n\n".join(examples)
    
    return ""


def validate_plan_file_paths(steps: list, project_structure: dict) -> list:
    """Validate and fix file paths in implementation plan based on project structure.
    
    Ensures generated file paths match the project's conventions.
    For example, converts wrong paths like 'src/pages/about.tsx' to correct 
    paths like 'app/about/page.tsx' for NextJS App Router.
    
    Args:
        steps: List of implementation plan steps
        project_structure: Dict from detect_project_structure()
        
    Returns:
        Corrected list of steps with valid file paths
    """
    framework = project_structure.get("framework", "unknown")
    router_type = project_structure.get("router_type")
    key_dirs = project_structure.get("key_dirs", [])
    existing_pages = project_structure.get("existing_pages", [])
    
    # Determine the base directory for pages
    page_base_dir = None
    if "app" in key_dirs:
        page_base_dir = "app"
    elif "src/app" in key_dirs:
        page_base_dir = "src/app"
    elif "pages" in key_dirs:
        page_base_dir = "pages"
    elif "src/pages" in key_dirs:
        page_base_dir = "src/pages"
    
    # Determine component base directory
    component_base_dir = None
    if "components" in key_dirs:
        component_base_dir = "components"
    elif "src/components" in key_dirs:
        component_base_dir = "src/components"
    
    for step in steps:
        file_path = step.get("file_path", "")
        if not file_path:
            continue
        
        original_path = file_path
        
        # Fix page paths for App Router projects
        if framework == "nextjs" and router_type == "app" and page_base_dir:
            # Wrong: src/pages/about.tsx or pages/about.tsx -> Correct: app/about/page.tsx
            if file_path.startswith("src/pages/") or file_path.startswith("pages/"):
                page_name = file_path.replace("src/pages/", "").replace("pages/", "")
                page_name = page_name.replace(".tsx", "").replace(".jsx", "").replace(".ts", "").replace(".js", "")
                
                if page_name in ["index", "_app", "_document"]:
                    step["file_path"] = f"{page_base_dir}/page.tsx"
                else:
                    step["file_path"] = f"{page_base_dir}/{page_name}/page.tsx"
                    
            # Wrong: pages/api/... -> Correct: app/api/.../route.ts
            elif file_path.startswith("pages/api/") or file_path.startswith("src/pages/api/"):
                api_path = file_path.replace("src/pages/api/", "").replace("pages/api/", "")
                api_path = api_path.replace(".ts", "").replace(".js", "")
                step["file_path"] = f"{page_base_dir}/api/{api_path}/route.ts"
        
        # Ensure components go to the right place
        if "component" in file_path.lower() and component_base_dir:
            if not file_path.startswith(component_base_dir):
                component_name = Path(file_path).name
                step["file_path"] = f"{component_base_dir}/{component_name}"
        
        if step["file_path"] != original_path:
            logger.info(f"[validate_plan] Fixed path: {original_path} -> {step['file_path']}")
    
    return steps
