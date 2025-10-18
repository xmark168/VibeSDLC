"""
Code Analysis Tools

Tools để analyze existing code patterns, structure và dependencies.
"""

import os
import ast
import json
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool


@tool
def code_search_tool(
    search_pattern: str,
    file_extensions: List[str] = None,
    search_path: str = ".",
    max_results: int = 10
) -> str:
    """
    Search for code patterns trong codebase.
    
    Args:
        search_pattern: Pattern để search (regex hoặc string)
        file_extensions: List extensions để search (default: ['.py', '.js', '.ts'])
        search_path: Path để search (default: current directory)
        max_results: Maximum số results trả về
        
    Returns:
        JSON string với search results
    """
    try:
        if file_extensions is None:
            file_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
        
        results = []
        search_count = 0
        
        # Walk through directory structure
        for root, dirs, files in os.walk(search_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
            
            for file in files:
                if search_count >= max_results:
                    break
                    
                # Check file extension
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Simple pattern search
                        if search_pattern.lower() in content.lower():
                            # Find line numbers
                            lines = content.split('\n')
                            matching_lines = []
                            
                            for i, line in enumerate(lines, 1):
                                if search_pattern.lower() in line.lower():
                                    matching_lines.append({
                                        "line_number": i,
                                        "content": line.strip()
                                    })
                                    
                                    if len(matching_lines) >= 5:  # Limit per file
                                        break
                            
                            if matching_lines:
                                results.append({
                                    "file_path": file_path,
                                    "matches": matching_lines,
                                    "total_matches": len(matching_lines)
                                })
                                search_count += 1
                                
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return json.dumps({
            "search_pattern": search_pattern,
            "total_files_found": len(results),
            "results": results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Code search failed: {str(e)}",
            "search_pattern": search_pattern,
            "results": []
        }, indent=2)


@tool
def ast_parser_tool(
    file_path: str,
    analysis_type: str = "structure"
) -> str:
    """
    Parse Python file using AST để analyze structure.
    
    Args:
        file_path: Path đến Python file
        analysis_type: Type of analysis ('structure', 'functions', 'classes', 'imports')
        
    Returns:
        JSON string với AST analysis results
    """
    try:
        if not os.path.exists(file_path):
            return json.dumps({
                "error": f"File not found: {file_path}",
                "analysis_type": analysis_type
            }, indent=2)
        
        if not file_path.endswith('.py'):
            return json.dumps({
                "error": f"AST parser only supports Python files: {file_path}",
                "analysis_type": analysis_type
            }, indent=2)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        tree = ast.parse(content)
        
        result = {
            "file_path": file_path,
            "analysis_type": analysis_type
        }
        
        if analysis_type == "structure" or analysis_type == "all":
            # Analyze overall structure
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line_number": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.FunctionDef):
                    # Only top-level functions
                    if isinstance(node.parent if hasattr(node, 'parent') else None, ast.Module):
                        functions.append({
                            "name": node.name,
                            "line_number": node.lineno,
                            "args": [arg.arg for arg in node.args.args]
                        })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append({
                                "type": "import",
                                "module": alias.name,
                                "alias": alias.asname
                            })
                    else:  # ImportFrom
                        for alias in node.names:
                            imports.append({
                                "type": "from_import",
                                "module": node.module,
                                "name": alias.name,
                                "alias": alias.asname
                            })
            
            result.update({
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "summary": {
                    "total_classes": len(classes),
                    "total_functions": len(functions),
                    "total_imports": len(imports)
                }
            })
        
        return json.dumps(result, indent=2)
        
    except SyntaxError as e:
        return json.dumps({
            "error": f"Syntax error in file: {str(e)}",
            "file_path": file_path,
            "line_number": e.lineno
        }, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"AST parsing failed: {str(e)}",
            "file_path": file_path
        }, indent=2)


@tool
def file_analyzer_tool(
    file_path: str,
    analysis_depth: str = "basic"
) -> str:
    """
    Analyze file để determine changes needed.
    
    Args:
        file_path: Path đến file cần analyze
        analysis_depth: Depth of analysis ('basic', 'detailed')
        
    Returns:
        JSON string với file analysis results
    """
    try:
        if not os.path.exists(file_path):
            return json.dumps({
                "file_path": file_path,
                "exists": False,
                "analysis": "File does not exist - will need to be created"
            }, indent=2)
        
        # Get file stats
        stat = os.stat(file_path)
        file_size = stat.st_size
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        lines = content.split('\n')
        
        result = {
            "file_path": file_path,
            "exists": True,
            "file_size": file_size,
            "line_count": len(lines),
            "extension": os.path.splitext(file_path)[1]
        }
        
        if analysis_depth == "detailed":
            # More detailed analysis
            non_empty_lines = [line for line in lines if line.strip()]
            comment_lines = []
            
            if file_path.endswith('.py'):
                comment_lines = [line for line in lines if line.strip().startswith('#')]
            elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                comment_lines = [line for line in lines if line.strip().startswith('//')]
            
            result.update({
                "non_empty_lines": len(non_empty_lines),
                "comment_lines": len(comment_lines),
                "code_density": len(non_empty_lines) / len(lines) if lines else 0,
                "sample_content": content[:500] + "..." if len(content) > 500 else content
            })
            
            # Language-specific analysis
            if file_path.endswith('.py'):
                # Python-specific analysis
                try:
                    tree = ast.parse(content)
                    complexity_score = calculate_complexity(tree)
                    result["complexity_score"] = complexity_score
                except:
                    result["complexity_score"] = "unknown"
        
        # Determine modification complexity
        if file_size < 1000:
            modification_complexity = "low"
        elif file_size < 5000:
            modification_complexity = "medium"
        else:
            modification_complexity = "high"
        
        result["modification_complexity"] = modification_complexity
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"File analysis failed: {str(e)}",
            "file_path": file_path
        }, indent=2)


def calculate_complexity(tree) -> int:
    """Calculate cyclomatic complexity of AST tree."""
    complexity = 1  # Base complexity
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(node, ast.ExceptHandler):
            complexity += 1
        elif isinstance(node, (ast.And, ast.Or)):
            complexity += 1
    
    return complexity
