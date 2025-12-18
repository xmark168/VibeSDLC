"""Parallel execution utilities for Tester agent (aligned with Developer V2)."""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

from app.core.agent.llm_factory import MAX_CONCURRENT_TASKS as MAX_CONCURRENT

logger = logging.getLogger(__name__)


# =============================================================================
# Layer Priority for Test Files
# =============================================================================

def get_test_layer_priority(file_path: str, test_type: str = "") -> int:
    """Get layer priority for test files.
    
    For Tester: Integration tests (layer 1) run before Unit tests (layer 2)
    because integration tests may reveal API issues that affect components.
    
    Returns:
        Layer number (lower = runs first)
    """
    if not file_path:
        return 99
    
    fp = file_path.lower().replace("\\", "/")
    
    # Integration tests run first (test API before components)
    if "integration" in fp or test_type == "integration":
        return 1
    
    # Unit tests run after
    if "unit" in fp or test_type == "unit":
        return 2
    
    # Default
    return 3


def group_tests_by_layer(steps: List[Dict]) -> Dict[int, List[Dict]]:
    """Group test steps by layer for parallel execution.
    
    Args:
        steps: List of test plan steps
        
    Returns:
        Dict mapping layer number to list of steps in that layer
    """
    layers = defaultdict(list)
    
    for step in steps:
        file_path = step.get("file_path", "")
        test_type = step.get("type", "")
        layer = get_test_layer_priority(file_path, test_type)
        layers[layer].append(step)
    
    return dict(layers)


# =============================================================================
# Parallel Execution Utilities
# =============================================================================

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
    """Run coroutine with semaphore for rate limiting."""
    async with semaphore:
        return await coro


async def run_parallel(
    items: List[Any],
    async_fn: Callable,
    max_concurrent: int = MAX_CONCURRENT,
) -> List[Any]:
    """Run async function on items in parallel with rate limiting.
    
    Args:
        items: List of items to process
        async_fn: Async function(item) -> result
        max_concurrent: Max concurrent executions
        
    Returns:
        List of results from each item
    """
    if not items:
        return []
    
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Create tasks
    tasks = [
        run_with_semaphore(semaphore, async_fn(item))
        for item in items
    ]
    
    # Run in parallel
    logger.info(f"[parallel] Running {len(tasks)} tasks (max {max_concurrent} concurrent)")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"[parallel] Task {i} failed: {result}")
            processed_results.append({"error": str(result), "index": i})
        else:
            processed_results.append(result)
    
    return processed_results


async def run_layer_sequential(
    layers: Dict[int, List[Dict]],
    async_fn: Callable,
    max_concurrent: int = MAX_CONCURRENT,
) -> List[Any]:
    """Run layers sequentially, but items within each layer in parallel.
    
    Args:
        layers: Dict mapping layer number to list of items
        async_fn: Async function(item) -> result
        max_concurrent: Max concurrent executions per layer
        
    Returns:
        List of all results (flattened)
    """
    all_results = []
    
    for layer_num in sorted(layers.keys()):
        layer_items = layers[layer_num]
        logger.info(f"[parallel] Layer {layer_num}: {len(layer_items)} items")
        
        if len(layer_items) == 1:
            # Single item - run directly
            result = await async_fn(layer_items[0])
            all_results.append(result)
        else:
            # Multiple items - run in parallel
            results = await run_parallel(layer_items, async_fn, max_concurrent)
            all_results.extend(results)
    
    return all_results


def merge_results(results: List[Dict], base_state: Dict) -> Dict:
    """Merge parallel execution results into state.
    
    Args:
        results: List of result dicts from parallel execution
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
            file_path = result.get("file_path")
            if file_path:
                all_modified.add(file_path)
            
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
    
    For Tester: Always use parallel since IT and UT are independent.
    
    Returns:
        True if parallel execution recommended
    """
    return len(steps) >= 2
