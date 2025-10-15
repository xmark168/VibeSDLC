# app/agents/developer/implementor/tools/codebase_tools.py
"""
Codebase analysis and indexing tools
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from langchain_core.tools import tool
import ast


@tool
def load_codebase_tool(working_directory: str) -> str:
    """
    Load and analyze existing codebase structure.

    This tool scans the codebase directory and provides a comprehensive overview
    of the project structure, key files, and patterns.

    Args:
        working_directory: Path to the codebase directory

    Returns:
        JSON string containing codebase analysis

    Example:
        load_codebase_tool("./src")
    """
    try:
        working_dir = Path(working_directory).resolve()

        if not working_dir.exists():
            return f"Error: Directory '{working_directory}' does not exist"

        if not working_dir.is_dir():
            return f"Error: '{working_directory}' is not a directory"

        analysis = {
            "directory": str(working_dir),
            "structure": {},
            "key_files": [],
            "languages": {},
            "patterns": {},
            "dependencies": {},
            "total_files": 0,
            "total_lines": 0,
        }

        # Scan directory structure
        def scan_directory(path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict:
            if current_depth >= max_depth:
                return {"...": "truncated"}

            structure = {}
            try:
                for item in sorted(path.iterdir()):
                    # Skip hidden files and common ignore patterns
                    if item.name.startswith(".") or item.name in [
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".git",
                    ]:
                        continue

                    if item.is_dir():
                        structure[f"{item.name}/"] = scan_directory(
                            item, max_depth, current_depth + 1
                        )
                    else:
                        structure[item.name] = f"file ({item.stat().st_size} bytes)"
                        analysis["total_files"] += 1

                        # Count lines for text files
                        if item.suffix in [
                            ".py",
                            ".js",
                            ".ts",
                            ".java",
                            ".cpp",
                            ".c",
                            ".h",
                            ".cs",
                            ".go",
                            ".rs",
                        ]:
                            try:
                                with open(item, "r", encoding="utf-8", errors="ignore") as f:
                                    lines = len(f.readlines())
                                    analysis["total_lines"] += lines
                            except:
                                pass

            except PermissionError:
                structure["<permission_denied>"] = "Cannot access"

            return structure

        analysis["structure"] = scan_directory(working_dir)

        # Identify key files
        key_patterns = {
            "package.json": "Node.js project",
            "requirements.txt": "Python dependencies",
            "pyproject.toml": "Python project config",
            "pom.xml": "Maven Java project",
            "build.gradle": "Gradle project",
            "Cargo.toml": "Rust project",
            "go.mod": "Go module",
            "Dockerfile": "Docker configuration",
            "docker-compose.yml": "Docker Compose",
            "README.md": "Project documentation",
            ".gitignore": "Git ignore rules",
            "main.py": "Python entry point",
            "app.py": "Python Flask/FastAPI app",
            "index.js": "Node.js entry point",
            "main.java": "Java entry point",
        }

        for pattern, description in key_patterns.items():
            key_file = working_dir / pattern
            if key_file.exists():
                analysis["key_files"].append(
                    {"file": pattern, "description": description, "size": key_file.stat().st_size}
                )

        # Analyze languages by file extensions
        for root, dirs, files in os.walk(working_dir):
            # Skip hidden and ignored directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in ["node_modules", "__pycache__", "venv"]
            ]

            for file in files:
                if file.startswith("."):
                    continue

                ext = Path(file).suffix.lower()
                if ext:
                    analysis["languages"][ext] = analysis["languages"].get(ext, 0) + 1

        # Detect common patterns
        patterns = {}

        # Check for web frameworks
        if (working_dir / "package.json").exists():
            try:
                with open(working_dir / "package.json", "r") as f:
                    package_data = json.load(f)
                    deps = {
                        **package_data.get("dependencies", {}),
                        **package_data.get("devDependencies", {}),
                    }

                    if "react" in deps:
                        patterns["React"] = "React application"
                    if "vue" in deps:
                        patterns["Vue"] = "Vue.js application"
                    if "angular" in deps:
                        patterns["Angular"] = "Angular application"
                    if "express" in deps:
                        patterns["Express"] = "Express.js server"
                    if "next" in deps:
                        patterns["Next.js"] = "Next.js application"

            except:
                pass

        # Check for Python frameworks
        if (working_dir / "requirements.txt").exists() or (working_dir / "pyproject.toml").exists():
            try:
                req_files = []
                if (working_dir / "requirements.txt").exists():
                    with open(working_dir / "requirements.txt", "r") as f:
                        req_files.extend(f.readlines())

                if (working_dir / "pyproject.toml").exists():
                    # Simple check for common dependencies in pyproject.toml
                    with open(working_dir / "pyproject.toml", "r") as f:
                        content = f.read()
                        if "fastapi" in content.lower():
                            patterns["FastAPI"] = "FastAPI application"
                        if "django" in content.lower():
                            patterns["Django"] = "Django application"
                        if "flask" in content.lower():
                            patterns["Flask"] = "Flask application"

                req_content = " ".join(req_files).lower()
                if "fastapi" in req_content:
                    patterns["FastAPI"] = "FastAPI application"
                if "django" in req_content:
                    patterns["Django"] = "Django application"
                if "flask" in req_content:
                    patterns["Flask"] = "Flask application"

            except:
                pass

        analysis["patterns"] = patterns

        # Try to detect dependencies
        if (working_dir / "package.json").exists():
            try:
                with open(working_dir / "package.json", "r") as f:
                    package_data = json.load(f)
                    analysis["dependencies"]["npm"] = {
                        "dependencies": len(package_data.get("dependencies", {})),
                        "devDependencies": len(package_data.get("devDependencies", {})),
                    }
            except:
                pass

        return json.dumps(analysis, indent=2)

    except Exception as e:
        return f"Error analyzing codebase: {str(e)}"


@tool
def index_codebase_tool(codebase_path: str, enable_pgvector: bool = True) -> str:
    """
    Index codebase using pgvector for semantic search.

    This tool extracts code snippets, generates embeddings, and stores them
    in a pgvector database for semantic similarity search.

    Args:
        codebase_path: Path to the codebase to index
        enable_pgvector: Whether to use pgvector (if False, creates local index)

    Returns:
        Status message about indexing process

    Example:
        index_codebase_tool("./src", enable_pgvector=True)
    """
    try:
        codebase_dir = Path(codebase_path).resolve()

        if not codebase_dir.exists():
            return f"Error: Directory '{codebase_path}' does not exist"

        # For now, create a simple local index
        # TODO: Implement actual pgvector integration

        indexed_files = []
        code_snippets = []

        # Supported file extensions for indexing
        code_extensions = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".cpp",
            ".c",
            ".h",
            ".cs",
            ".go",
            ".rs",
            ".php",
            ".rb",
        }

        for root, dirs, files in os.walk(codebase_dir):
            # Skip hidden and ignored directories
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["node_modules", "__pycache__", "venv", "target", "build"]
            ]

            for file in files:
                file_path = Path(root) / file

                if file_path.suffix.lower() in code_extensions:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        # Extract meaningful code snippets
                        if file_path.suffix == ".py":
                            snippets = extract_python_snippets(content, str(file_path))
                        else:
                            # For other languages, split by functions/classes (simple approach)
                            snippets = extract_generic_snippets(content, str(file_path))

                        code_snippets.extend(snippets)
                        indexed_files.append(str(file_path.relative_to(codebase_dir)))

                    except Exception:
                        continue

        # Store index information (simplified for now)
        index_info = {
            "indexed_files": len(indexed_files),
            "code_snippets": len(code_snippets),
            "files": indexed_files[:10],  # Show first 10 files
            "sample_snippets": [snippet["content"][:100] + "..." for snippet in code_snippets[:3]],
        }

        if enable_pgvector:
            # Use LangChain PGVector integration
            try:
                from ..langchain_pgvector_client import LangChainPgVectorClient

                # Initialize LangChain PGVector client
                client = LangChainPgVectorClient(
                    collection_name="code_snippets", embedding_model="text-embedding-3-large"
                )

                # Index code snippets using LangChain Documents
                indexed_snippets = 0
                for snippet in code_snippets:
                    success = client.index_code_snippet(
                        file_path=snippet["file_path"],
                        snippet_type=snippet["type"],
                        content=snippet["content"],
                        snippet_name=snippet.get("name"),
                        start_line=snippet.get("start_line"),
                        end_line=snippet.get("end_line"),
                        language=snippet.get("language"),
                        metadata=snippet.get("metadata", {}),
                    )
                    if success:
                        indexed_snippets += 1

                # Get index statistics
                stats = client.get_index_stats()

                status = f"Indexed {len(indexed_files)} files with {indexed_snippets} code snippets using LangChain PGVector"
                if client.mock_mode:
                    status += " (mock mode)"

            except ImportError as e:
                logger.error(f"LangChain pgvector dependencies not available: {e}")
                logger.info("Install with: pip install langchain-postgres langchain-openai")
                status = f"Created local index with {len(indexed_files)} files and {len(code_snippets)} code snippets (LangChain PGVector unavailable)"
        else:
            status = f"Created local index with {len(indexed_files)} files and {len(code_snippets)} code snippets"

        return json.dumps({"status": status, "details": index_info}, indent=2)

    except Exception as e:
        return f"Error indexing codebase: {str(e)}"


@tool
def search_similar_code_tool(
    query: str,
    limit: int = 5,
    similarity_threshold: float = 0.7,
    language: str = None,
    snippet_type: str = None,
    file_path: str = None,
) -> str:
    """
    Search for similar code snippets using LangChain PGVector semantic search.

    This tool performs semantic similarity search on the indexed codebase
    to find code snippets similar to the query.

    Args:
        query: Search query describing the code you're looking for
        limit: Maximum number of results to return (default: 5)
        similarity_threshold: Minimum similarity score 0-1 (default: 0.7)
        language: Filter by programming language (e.g., "python", "javascript")
        snippet_type: Filter by snippet type (e.g., "function", "class", "file")
        file_path: Filter by specific file path

    Returns:
        JSON string with search results and metadata

    Example:
        search_similar_code_tool("authentication function with JWT", limit=3, language="python")
    """
    try:
        from ..langchain_pgvector_client import LangChainPgVectorClient

        # Initialize LangChain PGVector client
        client = LangChainPgVectorClient(
            collection_name="code_snippets", embedding_model="text-embedding-3-large"
        )

        # Perform semantic search
        results = client.search_similar_code(
            query=query,
            limit=limit,
            similarity_threshold=similarity_threshold,
            language=language,
            snippet_type=snippet_type,
            file_path=file_path,
        )

        # Format results
        search_results = {
            "query": query,
            "total_results": len(results),
            "filters": {
                "language": language,
                "snippet_type": snippet_type,
                "file_path": file_path,
                "similarity_threshold": similarity_threshold,
            },
            "results": results,
        }

        if client.mock_mode:
            search_results["note"] = (
                "Running in mock mode - install langchain-postgres for full functionality"
            )

        return json.dumps(search_results, indent=2)

    except ImportError as e:
        logger.error(f"LangChain pgvector dependencies not available: {e}")
        return json.dumps(
            {
                "error": "LangChain PGVector not available",
                "message": "Install with: pip install langchain-postgres langchain-openai",
                "query": query,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error searching similar code: {e}")
        return json.dumps({"error": "Search failed", "message": str(e), "query": query}, indent=2)


def extract_python_snippets(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract meaningful snippets from Python code"""
    snippets = []

    try:
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start_line = node.lineno
                end_line = getattr(node, "end_lineno", start_line + 10)

                lines = content.split("\n")
                snippet_content = "\n".join(lines[start_line - 1 : end_line])

                snippets.append(
                    {
                        "type": type(node).__name__,
                        "name": node.name,
                        "file": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "content": snippet_content,
                    }
                )

    except SyntaxError:
        # If parsing fails, create a single snippet with the whole file
        snippets.append(
            {
                "type": "file",
                "name": Path(file_path).name,
                "file": file_path,
                "start_line": 1,
                "end_line": len(content.split("\n")),
                "content": content[:1000],  # First 1000 chars
            }
        )

    return snippets


def extract_generic_snippets(content: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract snippets from non-Python code files"""
    # Simple approach: split by common patterns
    lines = content.split("\n")
    snippets = []

    current_snippet = []
    snippet_start = 1

    for i, line in enumerate(lines, 1):
        current_snippet.append(line)

        # Look for function/class-like patterns
        if any(
            keyword in line.lower()
            for keyword in ["function", "class", "def ", "public ", "private ", "protected "]
        ):
            if len(current_snippet) > 1:
                snippets.append(
                    {
                        "type": "code_block",
                        "name": f"block_{len(snippets)}",
                        "file": file_path,
                        "start_line": snippet_start,
                        "end_line": i,
                        "content": "\n".join(current_snippet),
                    }
                )

            current_snippet = [line]
            snippet_start = i

    # Add the last snippet
    if current_snippet:
        snippets.append(
            {
                "type": "code_block",
                "name": f"block_{len(snippets)}",
                "file": file_path,
                "start_line": snippet_start,
                "end_line": len(lines),
                "content": "\n".join(current_snippet),
            }
        )

    return snippets
