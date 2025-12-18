"""Parallel implementation utilities."""
import asyncio
import logging
from collections import defaultdict
from typing import Dict, List

from app.agents.developer.src.config import MAX_CONCURRENT

logger = logging.getLogger(__name__)

LAYER_PRIORITY = {
    "prisma/schema": 1,
    "prisma/seed": 4,      # CHANGED: từ 2 → 4 (chạy song song với API)
    "src/types": 2,        # CHANGED: từ 3 → 2
    "src/lib": 3,          # CHANGED: từ 4 → 3
    "src/app/api": 4,      # CHANGED: từ 5 → 4
    "src/app/actions": 5,  # CHANGED: từ 6 → 5
    "src/components": 6,   # CHANGED: từ 7 → 6
    "page.tsx": 7,         # CHANGED: từ 8 → 7
}


def get_layer_priority(file_path: str) -> int:
    if not file_path:
        return 99
    
    fp = file_path.lower().replace("\\", "/")
    
    if "prisma/schema" in fp:
        return 1
    if "seed.ts" in fp:
        return 4  # CHANGED: từ 2 → 4 (chạy song song với API)
    if "/types/" in fp or fp.endswith(".d.ts"):
        return 2  # CHANGED: từ 3 → 2
    if "/lib/" in fp or "/utils/" in fp:
        return 3  # CHANGED: từ 4 → 3
    if "/api/" in fp and "route.ts" in fp:
        return 4  # CHANGED: từ 5 → 4
    if "/actions/" in fp:
        return 5  # CHANGED: từ 6 → 5
    if "/components/" in fp:
        name = fp.split("/")[-1].lower()
        if "card" in name or "item" in name:
            return 6.1  # CHANGED: từ 7.1 → 6.1
        if "section" in name:
            return 6.2  # CHANGED: từ 7.2 → 6.2
        return 6.3  # CHANGED: từ 7.3 → 6.3
    if "page.tsx" in fp or "page.ts" in fp:
        return 7  # CHANGED: từ 8 → 7
    return 5  # CHANGED: từ 6 → 5 (default)


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
    """Run all steps in a layer in parallel."""
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
    """Merge results from parallel execution into state."""
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
    """
    Determine if parallel execution is beneficial.
    """
    if len(steps) < 4:
        return False
    
    layers = group_steps_by_layer(steps)
    
    # Check if any layer has 2+ steps
    for layer_steps in layers.values():
        if len(layer_steps) >= 2:
            return True
    
    return False
