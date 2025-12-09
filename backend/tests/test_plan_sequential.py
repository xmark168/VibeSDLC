"""Test zero-shot planning for sequential stories.

Tests that story 2 correctly recognizes existing files from story 1.
"""
import asyncio
import time
from app.agents.developer_v2.src.nodes.plan import plan, FileRepository
from app.agents.developer_v2.src.nodes.parallel_utils import group_steps_by_layer

# Workspace with story 1 completed (clean - no story 2 files)
WORKSPACE = 'projects/story1_20251208_222332'

# Story 2: Search functionality (from test_dev_v2_real2.py)
STORY_2 = {
    'workspace_path': WORKSPACE,
    'tech_stack': 'nextjs',
    'project_id': 'test',
    'task_id': 'story2',
    'story_id': 'EPIC-001-US-002',
    'story_title': 'Search for books by title, author, or keyword',
    'story_description': 'The search functionality enables visitors to find books by title, author, or keyword with autocomplete suggestions.',
    'story_requirements': [
        'Display search bar prominently in the header, visible on all pages',
        'Implement autocomplete that shows suggestions after user types 2+ characters',
        'Search across book titles, author names, and ISBN numbers',
        'Show up to 8 autocomplete suggestions with book cover thumbnail, title, and author',
        'Return search results within 1 second for optimal user experience',
    ],
    'acceptance_criteria': [
        'Given I am on any page, When I type 2+ chars in search bar, Then I see autocomplete suggestions',
        'Given I see autocomplete suggestions, When I click on a suggestion, Then I navigate to book detail page',
        'Given I have typed a search query, When I press Enter, Then I see search results page',
    ],
}


async def test_sequential():
    print("=" * 70)
    print("SEQUENTIAL STORY TEST - Zero-Shot Planning Quality")
    print("=" * 70)
    
    # 1. Check FileRepository recognizes existing files
    print("\n[1] FileRepository Analysis")
    repo = FileRepository(WORKSPACE)
    print(f"    Files: {len(repo.file_tree)}")
    print(f"    Components: {list(repo.components.keys())}")
    print(f"    API routes: {len(repo.api_routes)}")
    
    # 2. Run zero-shot planning for story 2
    print("\n[2] Zero-Shot Planning for Story 2")
    start = time.time()
    result = await plan(STORY_2)
    elapsed = time.time() - start
    
    steps = result.get('implementation_plan', [])
    
    print(f"    Plan time: {elapsed:.1f}s")
    print(f"    Steps: {len(steps)}")
    print(f"    Action: {result.get('action')}")
    
    # 3. Show all steps with dependencies
    print("\n[3] Plan Steps Detail")
    for s in steps:
        action = s.get('action', 'unknown')
        file_path = s.get('file_path', '')
        task = s.get('task', '')[:50]
        deps = s.get('dependencies', [])
        
        action_marker = "MOD" if action == "modify" else "NEW"
        print(f"    {s.get('order'):2}. [{action_marker}] {file_path}")
        print(f"        Task: {task}...")
        print(f"        Deps: {deps}")
    
    # 4. Layer Assignment Check (CRITICAL)
    print("\n[4] Layer Assignment (Dependency-Aware)")
    layers = group_steps_by_layer(steps)
    
    for layer_num in sorted(layers.keys()):
        layer_steps = layers[layer_num]
        files = [s.get('file_path', '').split('/')[-1] for s in layer_steps]
        parallel = "PARALLEL" if len(layer_steps) > 1 and layer_num >= 5 else "SEQ"
        print(f"    Layer {layer_num}: {files} ({parallel})")
    
    # 5. Critical Check: SearchBar before Navigation
    print("\n[5] Critical Dependency Checks")
    
    searchbar_step = next((s for s in steps if 'SearchBar' in s.get('file_path', '')), None)
    nav_step = next((s for s in steps if 'Navigation' in s.get('file_path', '')), None)
    
    if searchbar_step and nav_step:
        searchbar_layer = None
        nav_layer = None
        for layer_num, layer_steps in layers.items():
            if searchbar_step in layer_steps:
                searchbar_layer = layer_num
            if nav_step in layer_steps:
                nav_layer = layer_num
        
        # Check Navigation has SearchBar in dependencies
        nav_deps = nav_step.get('dependencies', [])
        has_searchbar_dep = any('SearchBar' in d for d in nav_deps)
        print(f"    [{'OK' if has_searchbar_dep else 'FAIL'}] Navigation depends on SearchBar: {has_searchbar_dep}")
        if nav_deps:
            print(f"        Navigation.dependencies = {nav_deps}")
        
        # Check layers: Navigation should be AFTER SearchBar
        if searchbar_layer is not None and nav_layer is not None:
            layer_order_ok = nav_layer > searchbar_layer
            print(f"    [{'OK' if layer_order_ok else 'FAIL'}] Layer order: SearchBar({searchbar_layer}) < Navigation({nav_layer})")
        else:
            print(f"    [WARN] Could not determine layers: SearchBar={searchbar_layer}, Nav={nav_layer}")
    else:
        print(f"    [WARN] SearchBar or Navigation not in plan")
        print(f"        SearchBar step: {searchbar_step}")
        print(f"        Navigation step: {nav_step}")
    
    # 6. Other quality checks
    print("\n[6] General Quality Checks")
    
    # Navigation.tsx should be MODIFY
    nav_ok = nav_step and nav_step.get('action') == 'modify'
    print(f"    [{'OK' if nav_ok else 'FAIL'}] Navigation.tsx action=modify")
    
    # Should NOT recreate existing components
    existing_comps = {'BookCard', 'HeroSection', 'CategoriesSection', 'BestsellersSection'}
    recreated = [s for s in steps if any(c in s.get('file_path', '') for c in existing_comps) and s.get('action') == 'create']
    no_recreate = len(recreated) == 0
    print(f"    [{'OK' if no_recreate else 'FAIL'}] Not recreating existing components")
    
    # Should have search API
    search_api = any('/api/' in s.get('file_path', '') and 'search' in s.get('file_path', '').lower() for s in steps)
    print(f"    [{'OK' if search_api else 'FAIL'}] Has search API route")
    
    # Should have search page
    search_page = any('search' in s.get('file_path', '').lower() and 'page.tsx' in s.get('file_path', '') for s in steps)
    print(f"    [{'OK' if search_page else 'FAIL'}] Has search results page")
    
    # Summary
    all_checks = [
        nav_ok,
        no_recreate,
        search_api,
        search_page,
        has_searchbar_dep if searchbar_step and nav_step else True,
        layer_order_ok if searchbar_step and nav_step and searchbar_layer and nav_layer else True,
    ]
    all_ok = all(all_checks)
    
    print("\n" + "=" * 70)
    print(f"RESULT: {'PASS' if all_ok else 'NEEDS REVIEW'}")
    print("=" * 70)
    
    return all_ok


if __name__ == "__main__":
    result = asyncio.run(test_sequential())
    exit(0 if result else 1)
