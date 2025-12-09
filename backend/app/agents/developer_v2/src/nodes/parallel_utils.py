"""Parallel implementation utilities."""
import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

MAX_CONCURRENT = 5

LAYER_PRIORITY = {
    "prisma/schema": 1,
    "prisma/seed": 2,
    "src/types": 3,
    "src/lib": 4,
    "src/app/api": 5,
    "src/app/actions": 6,
    "src/components": 7,
    "page.tsx": 8,
}


def get_layer_priority(file_path: str) -> int:
    if not file_path:
        return 99
    
    fp = file_path.lower().replace("\\", "/")
    
    if "prisma/schema" in fp:
        return 1
    if "seed.ts" in fp:
        return 2
    if "/types/" in fp or fp.endswith(".d.ts"):
        return 3
    if "/lib/" in fp or "/utils/" in fp:
        return 4
    if "/api/" in fp and "route.ts" in fp:
        return 5
    if "/actions/" in fp:
        return 6
    if "/components/" in fp:
        name = fp.split("/")[-1].lower()
        if "card" in name or "item" in name:
            return 7.1
        if "section" in name:
            return 7.2
        return 7.3
    if "page.tsx" in fp or "page.ts" in fp:
        return 8
    return 6


def group_steps_by_layer(steps: List[Dict]) -> Dict[float, List[Dict]]:
    """Group steps by layer priority, respecting dependencies."""
    layers = defaultdict(list)
    component_paths = set()
    for step in steps:
        fp = step.get("file_path", "")
        if "/components/" in fp and fp.endswith(".tsx"):
            component_paths.add(fp)
    
    for step in steps:
        file_path = step.get("file_path", "")
        base_layer = get_layer_priority(file_path)
        step_deps = step.get("dependencies", [])
        has_component_dep = any(dep in component_paths for dep in step_deps)
        
        if has_component_dep and 7 <= base_layer < 8:
            dep_layers = [get_layer_priority(d) for d in step_deps if d in component_paths]
            if dep_layers:
                base_layer = max(base_layer, max(dep_layers) + 0.1)
        
        layers[base_layer].append(step)
    
    return dict(layers)


def detect_file_conflicts(steps: List[Dict]) -> List[str]:
    """Detect if multiple steps modify the same file."""
    file_counts = defaultdict(int)
    
    for step in steps:
        file_path = step.get("file_path", "")
        if file_path:
            file_counts[file_path] += 1
    
    conflicts = [fp for fp, count in file_counts.items() if count > 1]
    return conflicts


async def run_with_semaphore(semaphore: asyncio.Semaphore, coro):
    async with semaphore:
        return await coro


async def run_layer_parallel(
    layer_steps: List[Dict],
    implement_fn,
    state: Dict,
    max_concurrent: int = MAX_CONCURRENT
) -> List[Dict]:
    """Run all steps in a layer in parallel.
    
    Args:
        layer_steps: List of step dicts to run
        implement_fn: Async function(step) -> result (closure with state access)
        state: Current state dict (unused, kept for API compatibility)
        max_concurrent: Max concurrent executions
        
    Returns:
        List of results from each step
    """
    if not layer_steps:
        return []
    
    # Check for file conflicts
    conflicts = detect_file_conflicts(layer_steps)
    if conflicts:
        logger.warning(f"[parallel] File conflicts detected, running sequentially: {conflicts}")
        # Run sequentially for safety
        results = []
        for step in layer_steps:
            result = await implement_fn(step)
            results.append(result)
        return results
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Create tasks - implement_fn is a closure that already has state
    tasks = [
        run_with_semaphore(semaphore, implement_fn(step))
        for step in layer_steps
    ]
    
    # Run in parallel
    logger.info(f"[parallel] Running {len(tasks)} steps in parallel (max {max_concurrent} concurrent)")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[parallel] Step {i} failed: {result}")
            processed_results.append({"error": str(result)})
        else:
            processed_results.append(result)
    
    return processed_results


def merge_parallel_results(results: List[Dict], base_state: Dict) -> Dict:
    """Merge results from parallel execution into state.
    
    Args:
        results: List of result dicts from parallel steps
        base_state: Original state to merge into
        
    Returns:
        Merged state dict
    """
    merged = {**base_state}
    
    # Collect all modified files
    all_modified = set(merged.get("files_modified", []))
    
    # Collect errors
    errors = []
    
    for result in results:
        if isinstance(result, dict):
            # Add modified files
            modified = result.get("files_modified", [])
            if isinstance(modified, list):
                all_modified.update(modified)
            
            # Collect errors
            if result.get("error"):
                errors.append(result["error"])
    
    merged["files_modified"] = list(all_modified)
    
    if errors:
        merged["parallel_errors"] = errors
    
    return merged


def should_use_parallel(steps: List[Dict]) -> bool:
    """Determine if parallel execution is beneficial.
    
    Returns True if:
    - More than 3 steps
    - At least 2 steps can run in same layer
    """
    if len(steps) < 4:
        return False
    
    layers = group_steps_by_layer(steps)
    
    # Check if any layer has 2+ steps
    for layer_steps in layers.values():
        if len(layer_steps) >= 2:
            return True
    
    return False
