"""Quick test for parallel execution with Homepage story simulation."""
import asyncio
import time

from app.agents.developer_v2.src.nodes.parallel_utils import (
    group_steps_by_layer,
    run_layer_parallel,
    should_use_parallel,
)


async def main():
    print("=" * 60)
    print("TEST: Parallel Layer Execution - Homepage Story")
    print("=" * 60)
    
    # Simulated plan steps for Homepage
    steps = [
        {"order": 1, "file_path": "prisma/schema.prisma", "task": "Update schema"},
        {"order": 2, "file_path": "prisma/seed.ts", "task": "Create seed"},
        {"order": 3, "file_path": "src/app/api/books/route.ts", "task": "Books API"},
        {"order": 4, "file_path": "src/app/api/categories/route.ts", "task": "Categories API"},
        {"order": 5, "file_path": "src/components/BookCard.tsx", "task": "BookCard"},
        {"order": 6, "file_path": "src/components/CategoryCard.tsx", "task": "CategoryCard"},
        {"order": 7, "file_path": "src/components/FeaturedBooks.tsx", "task": "FeaturedBooks"},
        {"order": 8, "file_path": "src/components/HeroSection.tsx", "task": "HeroSection"},
        {"order": 9, "file_path": "src/app/page.tsx", "task": "Homepage"},
    ]
    
    layers = group_steps_by_layer(steps)
    can_parallel = should_use_parallel(steps)
    
    print(f"\nTotal steps: {len(steps)}")
    print(f"Can use parallel: {can_parallel}")
    print(f"\nLayer Distribution:")
    for ln in sorted(layers.keys()):
        ls = layers[ln]
        mode = "PARALLEL" if len(ls) > 1 else "SEQ"
        print(f"  Layer {ln}: {len(ls)} steps - {mode}")
        for s in ls:
            print(f"    - {s['file_path']}")
    
    # Track execution
    concurrent_count = 0
    max_concurrent = 0
    
    async def mock_implement(step, state):
        nonlocal concurrent_count, max_concurrent
        fp = step["file_path"]
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        print(f"    [START] {fp} (concurrent: {concurrent_count})")
        await asyncio.sleep(0.2)  # 200ms per step
        concurrent_count -= 1
        print(f"    [END] {fp}")
        return {"success": True, "file_path": fp, "modified_files": [fp]}
    
    # Execute
    total_start = time.time()
    all_results = []
    
    print(f"\n--- EXECUTION ---")
    for ln in sorted(layers.keys()):
        ls = layers[ln]
        layer_start = time.time()
        print(f"\nLayer {ln}: Starting {len(ls)} steps...")
        results = await run_layer_parallel(ls, mock_implement, {})
        all_results.extend(results)
        layer_time = time.time() - layer_start
        print(f"Layer {ln}: Done in {layer_time:.2f}s")
    
    total_time = time.time() - total_start
    
    # Analysis
    print(f"\n--- RESULTS ---")
    print(f"Total time: {total_time:.2f}s")
    print(f"Steps executed: {len(all_results)}")
    print(f"Max concurrent: {max_concurrent}")
    
    seq_time = len(steps) * 0.2
    speedup = seq_time / total_time
    savings = (1 - total_time / seq_time) * 100
    
    print(f"\nPerformance:")
    print(f"  Sequential would take: {seq_time:.2f}s")
    print(f"  Parallel took: {total_time:.2f}s")
    print(f"  Speedup: {speedup:.1f}x ({savings:.0f}% faster)")
    
    print(f"\n" + "=" * 60)
    if speedup > 1.5:
        print("RESULT: PASS - Parallel execution working correctly")
    else:
        print("RESULT: WARN - Speedup lower than expected")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
