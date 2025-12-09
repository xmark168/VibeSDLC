"""Test zero-shot planning only."""
import asyncio
import time
import json
from app.agents.developer_v2.src.nodes.plan import plan, FileRepository

state = {
    'workspace_path': 'projects/story1_20251208_233158',
    'tech_stack': 'nextjs',
    'project_id': 'test',
    'task_id': 'story1',
    'story_id': 'story1',
    'story_title': 'Homepage with featured books and categories',
    'story_description': 'As a first-time visitor, I want to see featured books and categories on the homepage so that I can quickly discover interesting books without searching',
    'story_requirements': [
        'Hero section with welcome message and CTA',
        'Featured books grid (6-8 books)',
        'Categories section with icons',
        'Bestsellers carousel',
        'New arrivals section'
    ],
    'acceptance_criteria': [
        'Homepage loads with hero section',
        'Featured books fetched from API',
        'Categories displayed with navigation',
        'Responsive design'
    ],
}

async def test():
    print("=" * 60)
    print("ZERO-SHOT PLANNING QUALITY TEST")
    print("=" * 60)
    
    start = time.time()
    result = await plan(state)
    elapsed = time.time() - start
    
    steps = result.get('implementation_plan', [])
    layers = result.get('parallel_layers', {})
    
    print(f"\n[METRICS]")
    print(f"  Plan time: {elapsed:.1f}s")
    print(f"  Steps: {len(steps)}")
    print(f"  Layers: {len(layers)}")
    print(f"  Action: {result.get('action')}")
    
    print(f"\n[STEPS DETAIL]")
    for s in steps:
        skills = s.get('skills', [])
        deps = s.get('dependencies', [])
        print(f"  {s.get('order'):2}. [{s.get('action'):6}] {s.get('file_path')}")
        print(f"      Task: {s.get('task', '')[:60]}")
        print(f"      Skills: {skills}")
        if deps:
            print(f"      Deps: {deps}")
        print()
    
    print(f"[LAYERS]")
    for layer, files in sorted(layers.items()):
        print(f"  Layer {layer}: {files}")
    
    # Quality checks
    print(f"\n[QUALITY CHECKS]")
    has_schema = any('schema.prisma' in s.get('file_path', '') for s in steps)
    has_seed = any('seed.ts' in s.get('file_path', '') for s in steps)
    has_api = any('/api/' in s.get('file_path', '') for s in steps)
    has_components = any('/components/' in s.get('file_path', '') for s in steps)
    has_page = any('page.tsx' in s.get('file_path', '') for s in steps)
    
    print(f"  [{'OK' if has_schema else 'MISS'}] Schema step")
    print(f"  [{'OK' if has_seed else 'MISS'}] Seed step")
    print(f"  [{'OK' if has_api else 'MISS'}] API routes")
    print(f"  [{'OK' if has_components else 'MISS'}] Components")
    print(f"  [{'OK' if has_page else 'MISS'}] Page composition")
    
    # Order check
    schema_order = next((s.get('order') for s in steps if 'schema.prisma' in s.get('file_path', '')), 999)
    api_order = min((s.get('order') for s in steps if '/api/' in s.get('file_path', '')), default=999)
    comp_order = min((s.get('order') for s in steps if '/components/' in s.get('file_path', '')), default=999)
    page_order = max((s.get('order') for s in steps if 'page.tsx' in s.get('file_path', '')), default=0)
    
    order_ok = schema_order < api_order <= comp_order < page_order
    print(f"  [{'OK' if order_ok else 'WARN'}] Order: schema({schema_order}) < api({api_order}) < comp({comp_order}) < page({page_order})")

if __name__ == "__main__":
    asyncio.run(test())
