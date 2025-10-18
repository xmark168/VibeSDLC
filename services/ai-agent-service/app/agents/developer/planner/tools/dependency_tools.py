"""
Dependency Analysis Tools

Tools để analyze dependencies và create execution order.
"""

import os
import json
import ast
from typing import Dict, Any, List, Set, Optional
from langchain_core.tools import tool


@tool
def dependency_analyzer_tool(
    target_path: str,
    analysis_scope: str = "all",
    depth: int = 2
) -> str:
    """
    Analyze dependencies của target path.
    
    Args:
        target_path: Path để analyze dependencies
        analysis_scope: Scope of analysis ('internal', 'external', 'all')
        depth: Depth of dependency analysis
        
    Returns:
        JSON string với dependency analysis results
    """
    try:
        if not os.path.exists(target_path):
            return json.dumps({
                "error": f"Target path not found: {target_path}",
                "dependencies": {"internal": [], "external": []}
            }, indent=2)
        
        internal_deps = []
        external_deps = []
        
        if os.path.isfile(target_path):
            # Analyze single file
            deps = analyze_file_dependencies(target_path)
            internal_deps.extend(deps["internal"])
            external_deps.extend(deps["external"])
        else:
            # Analyze directory
            for root, dirs, files in os.walk(target_path):
                # Skip common directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv']]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                        file_path = os.path.join(root, file)
                        deps = analyze_file_dependencies(file_path)
                        internal_deps.extend(deps["internal"])
                        external_deps.extend(deps["external"])
        
        # Remove duplicates
        internal_deps = list({dep["module"]: dep for dep in internal_deps}.values())
        external_deps = list({dep["package"]: dep for dep in external_deps}.values())
        
        # Filter by scope
        result_deps = {"internal": [], "external": []}
        
        if analysis_scope in ["internal", "all"]:
            result_deps["internal"] = internal_deps
        
        if analysis_scope in ["external", "all"]:
            result_deps["external"] = external_deps
        
        # Add dependency graph
        dependency_graph = build_dependency_graph(internal_deps)
        
        result = {
            "target_path": target_path,
            "analysis_scope": analysis_scope,
            "dependencies": result_deps,
            "dependency_graph": dependency_graph,
            "summary": {
                "total_internal": len(internal_deps),
                "total_external": len(external_deps),
                "circular_dependencies": find_circular_dependencies(dependency_graph)
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Dependency analysis failed: {str(e)}",
            "target_path": target_path,
            "dependencies": {"internal": [], "external": []}
        }, indent=2)


@tool
def execution_order_tool(
    tasks: List[Dict[str, Any]],
    dependency_rules: List[Dict[str, Any]] = None
) -> str:
    """
    Create execution order based on tasks và dependencies.
    
    Args:
        tasks: List of tasks với dependencies
        dependency_rules: Additional dependency rules
        
    Returns:
        JSON string với execution order
    """
    try:
        if not tasks:
            return json.dumps({
                "execution_order": [],
                "error": "No tasks provided"
            }, indent=2)
        
        # Build dependency graph
        task_graph = {}
        task_map = {}
        
        for task in tasks:
            task_id = task.get("id", task.get("name", f"task_{len(task_map)}"))
            task_map[task_id] = task
            task_graph[task_id] = {
                "task": task,
                "dependencies": task.get("dependencies", []),
                "dependents": []
            }
        
        # Add reverse dependencies
        for task_id, task_info in task_graph.items():
            for dep in task_info["dependencies"]:
                if dep in task_graph:
                    task_graph[dep]["dependents"].append(task_id)
        
        # Apply additional dependency rules
        if dependency_rules:
            for rule in dependency_rules:
                before = rule.get("before")
                after = rule.get("after")
                if before in task_graph and after in task_graph:
                    if after not in task_graph[before]["dependencies"]:
                        task_graph[before]["dependencies"].append(after)
                    if before not in task_graph[after]["dependents"]:
                        task_graph[after]["dependents"].append(before)
        
        # Topological sort
        execution_order = topological_sort(task_graph)
        
        # Identify parallel opportunities
        parallel_groups = find_parallel_groups(task_graph, execution_order)
        
        # Calculate execution phases
        phases = calculate_execution_phases(task_graph, execution_order)
        
        result = {
            "execution_order": execution_order,
            "parallel_groups": parallel_groups,
            "execution_phases": phases,
            "total_tasks": len(tasks),
            "dependency_violations": check_dependency_violations(task_graph, execution_order)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({
            "error": f"Execution order calculation failed: {str(e)}",
            "execution_order": []
        }, indent=2)


def analyze_file_dependencies(file_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """Analyze dependencies của single file."""
    internal_deps = []
    external_deps = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if file_path.endswith('.py'):
            # Python dependencies
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if is_internal_module(alias.name):
                                internal_deps.append({
                                    "module": alias.name,
                                    "type": "import",
                                    "file": file_path
                                })
                            else:
                                external_deps.append({
                                    "package": alias.name.split('.')[0],
                                    "module": alias.name,
                                    "type": "import",
                                    "file": file_path
                                })
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if is_internal_module(module):
                            internal_deps.append({
                                "module": module,
                                "type": "from_import",
                                "imports": [alias.name for alias in node.names],
                                "file": file_path
                            })
                        else:
                            external_deps.append({
                                "package": module.split('.')[0] if module else "unknown",
                                "module": module,
                                "type": "from_import",
                                "imports": [alias.name for alias in node.names],
                                "file": file_path
                            })
            except SyntaxError:
                pass
        
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            # JavaScript/TypeScript dependencies (basic parsing)
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Simple regex-based parsing
                    if 'from ' in line:
                        parts = line.split('from ')
                        if len(parts) > 1:
                            module = parts[-1].strip().strip('\'"').strip(';')
                            if module.startswith('.'):
                                internal_deps.append({
                                    "module": module,
                                    "type": "import",
                                    "file": file_path
                                })
                            else:
                                external_deps.append({
                                    "package": module.split('/')[0],
                                    "module": module,
                                    "type": "import",
                                    "file": file_path
                                })
    
    except Exception:
        pass
    
    return {"internal": internal_deps, "external": external_deps}


def is_internal_module(module_name: str) -> bool:
    """Check if module is internal to project."""
    if not module_name:
        return False
    
    # Common external packages
    external_packages = {
        'os', 'sys', 'json', 'datetime', 'typing', 'pathlib',
        'langchain', 'openai', 'pydantic', 'fastapi', 'sqlalchemy',
        'pytest', 'numpy', 'pandas', 'requests', 'flask', 'django'
    }
    
    root_module = module_name.split('.')[0]
    return root_module not in external_packages and not root_module.startswith('_')


def build_dependency_graph(internal_deps: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Build dependency graph từ internal dependencies."""
    graph = {}
    
    for dep in internal_deps:
        module = dep["module"]
        if module not in graph:
            graph[module] = []
        
        # Add dependencies based on imports
        if dep["type"] == "from_import":
            imports = dep.get("imports", [])
            for imp in imports:
                if imp not in graph[module]:
                    graph[module].append(imp)
    
    return graph


def find_circular_dependencies(graph: Dict[str, List[str]]) -> List[List[str]]:
    """Find circular dependencies trong graph."""
    visited = set()
    rec_stack = set()
    cycles = []
    
    def dfs(node, path):
        if node in rec_stack:
            # Found cycle
            cycle_start = path.index(node)
            cycles.append(path[cycle_start:] + [node])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in graph.get(node, []):
            dfs(neighbor, path + [node])
        
        rec_stack.remove(node)
    
    for node in graph:
        if node not in visited:
            dfs(node, [])
    
    return cycles


def topological_sort(task_graph: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Perform topological sort on task graph."""
    in_degree = {}
    
    # Calculate in-degrees
    for task_id in task_graph:
        in_degree[task_id] = len(task_graph[task_id]["dependencies"])
    
    # Find tasks with no dependencies
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        current = queue.pop(0)
        result.append({
            "task_id": current,
            "task": task_graph[current]["task"],
            "step": len(result) + 1
        })
        
        # Update in-degrees of dependents
        for dependent in task_graph[current]["dependents"]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    return result


def find_parallel_groups(task_graph: Dict[str, Dict[str, Any]], execution_order: List[Dict[str, Any]]) -> List[List[str]]:
    """Find tasks that can be executed in parallel."""
    parallel_groups = []
    
    # Group tasks by their dependency level
    levels = {}
    for item in execution_order:
        task_id = item["task_id"]
        level = len(task_graph[task_id]["dependencies"])
        if level not in levels:
            levels[level] = []
        levels[level].append(task_id)
    
    # Tasks at same level can potentially run in parallel
    for level, tasks in levels.items():
        if len(tasks) > 1:
            parallel_groups.append(tasks)
    
    return parallel_groups


def calculate_execution_phases(task_graph: Dict[str, Dict[str, Any]], execution_order: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate execution phases based on dependencies."""
    phases = []
    current_phase = []
    completed_tasks = set()
    
    for item in execution_order:
        task_id = item["task_id"]
        dependencies = task_graph[task_id]["dependencies"]
        
        # Check if all dependencies are completed
        if all(dep in completed_tasks for dep in dependencies):
            current_phase.append(task_id)
        else:
            # Start new phase
            if current_phase:
                phases.append({
                    "phase": len(phases) + 1,
                    "tasks": current_phase.copy()
                })
                completed_tasks.update(current_phase)
                current_phase = []
            current_phase.append(task_id)
    
    # Add final phase
    if current_phase:
        phases.append({
            "phase": len(phases) + 1,
            "tasks": current_phase
        })
    
    return phases


def check_dependency_violations(task_graph: Dict[str, Dict[str, Any]], execution_order: List[Dict[str, Any]]) -> List[str]:
    """Check for dependency violations trong execution order."""
    violations = []
    executed_tasks = set()
    
    for item in execution_order:
        task_id = item["task_id"]
        dependencies = task_graph[task_id]["dependencies"]
        
        for dep in dependencies:
            if dep not in executed_tasks:
                violations.append(f"Task {task_id} depends on {dep} but {dep} is not executed yet")
        
        executed_tasks.add(task_id)
    
    return violations
