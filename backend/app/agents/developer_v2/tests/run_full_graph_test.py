"""Test full graph with real LLM - HOMEPAGE_STORY.

Run: uv run python app/agents/developer_v2/tests/run_full_graph_test.py

This test runs the complete workflow:
setup_workspace -> plan -> implement -> review -> run_code
"""
import asyncio
import time
import shutil
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Load env
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

BOILERPLATE_PATH = backend_dir / "app" / "agents" / "templates" / "boilerplate" / "nextjs-boilerplate"
OUTPUT_DIR = backend_dir / "app" / "agents" / "developer_v2" / "tests" / "test_output"

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

HOMEPAGE_STORY = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001", 
    "title": "Homepage with Featured Books",
    "description": """As a first-time visitor, I want to see a clear homepage layout with featured books so that I can quickly understand what the bookstore offers and start browsing.""",
    "requirements": [
        "Display hero section with main value proposition and call-to-action button",
        "Show featured/bestselling textbooks section with book covers, titles, prices",
        "Include prominent search bar at the top of the page",
        "Display trust indicators: return policy, genuine books guarantee",
        "Show category navigation menu organized by grade levels",
    ],
}


class MockAgent:
    """Mock agent for graph execution."""
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.main_workspace = workspace_path
        self.name = "test_developer"


async def run_full_graph():
    """Run the complete graph and collect metrics."""
    from app.agents.developer_v2.src.graph import DeveloperGraph
    
    print("=" * 70)
    print("FULL GRAPH TEST - HOMEPAGE_STORY")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Create fresh workspace
    OUTPUT_DIR.mkdir(exist_ok=True)
    workspace = OUTPUT_DIR / f"workspace_{datetime.now().strftime('%H%M%S')}"
    
    print(f"\n[1/6] Creating workspace...")
    def ignore_patterns(dir, files):
        return [f for f in files if f in ['node_modules', '.git', '.next']]
    shutil.copytree(BOILERPLATE_PATH, workspace, ignore=ignore_patterns)
    print(f"  Workspace: {workspace}")
    
    # Create mock agent
    agent = MockAgent(str(workspace))
    
    # Build graph with parallel execution
    graph = DeveloperGraph(agent=agent, parallel=True)
    
    # Initial state
    initial_state = {
        "workspace_path": str(workspace),
        "main_workspace": str(workspace),
        "project_id": "test-bookstore",
        "task_id": HOMEPAGE_STORY["story_id"],
        "story_id": HOMEPAGE_STORY["story_id"],
        "epic": HOMEPAGE_STORY["epic"],
        "tech_stack": "nextjs",
        "story_title": HOMEPAGE_STORY["title"],
        "story_description": HOMEPAGE_STORY["description"],
        "story_requirements": HOMEPAGE_STORY["requirements"],
        "files_modified": [],
        "use_code_review": True,
        "complexity": "low",  # Skip review to speed up test
    }
    
    # Metrics collection
    metrics = {
        "start_time": time.time(),
        "node_times": {},
        "steps_count": 0,
        "files_generated": [],
        "lgtm_count": 0,
        "lbtm_count": 0,
        "errors": [],
        "run_status": None,
    }
    
    print(f"\n[2/6] Running graph...")
    print("-" * 70)
    
    # Track node execution
    current_node = None
    node_start = None
    
    try:
        # Stream graph execution with increased recursion limit
        # Each implement+review = 2 iterations, so 20 steps needs ~50 limit
        config = {"recursion_limit": 100}
        async for event in graph.graph.astream(initial_state, config=config):
            for node_name, node_output in event.items():
                # Track timing
                if current_node and node_start:
                    metrics["node_times"][current_node] = time.time() - node_start
                
                current_node = node_name
                node_start = time.time()
                
                # Log progress
                if node_name == "plan":
                    steps = node_output.get("implementation_plan", [])
                    metrics["steps_count"] = len(steps)
                    print(f"  [PLAN] {len(steps)} steps planned")
                    for s in steps[:5]:
                        print(f"    - {s.get('file_path', 'unknown')}")
                    if len(steps) > 5:
                        print(f"    ... and {len(steps) - 5} more")
                
                elif node_name == "implement":
                    step_num = node_output.get("current_step", 0)
                    total = node_output.get("total_steps", 0)
                    last_file = node_output.get("last_implemented_file", "")
                    print(f"  [IMPLEMENT] Step {step_num}/{total}: {last_file}")
                
                elif node_name == "review":
                    result = node_output.get("review_result", "")
                    if result == "LGTM":
                        metrics["lgtm_count"] += 1
                    elif result == "LBTM":
                        metrics["lbtm_count"] += 1
                    print(f"  [REVIEW] {result}")
                
                elif node_name == "run_code":
                    run_result = node_output.get("run_result", {})
                    status = run_result.get("status", "UNKNOWN")
                    metrics["run_status"] = status
                    print(f"  [RUN_CODE] Status: {status}")
                    if status == "FAIL":
                        stderr = node_output.get("run_stderr", "")[:500]
                        print(f"    Error: {stderr}")
                
                elif node_name == "analyze_error":
                    print(f"  [ANALYZE_ERROR] Debug attempt {node_output.get('debug_count', 0)}")
        
        # Final timing
        if current_node and node_start:
            metrics["node_times"][current_node] = time.time() - node_start
            
    except Exception as e:
        metrics["errors"].append(str(e))
        print(f"  [ERROR] {e}")
    
    metrics["total_time"] = time.time() - metrics["start_time"]
    
    # Collect generated files
    print(f"\n[3/6] Collecting generated files...")
    for pattern in ["prisma/*.prisma", "prisma/*.ts", "src/**/*.ts", "src/**/*.tsx"]:
        for f in workspace.glob(pattern):
            if f.is_file():
                rel_path = f.relative_to(workspace)
                content = f.read_text(encoding='utf-8', errors='replace')
                metrics["files_generated"].append({
                    "path": str(rel_path),
                    "lines": len(content.split('\n')),
                    "chars": len(content),
                })
    
    # Run quality checks
    print(f"\n[4/6] Running quality checks...")
    quality = {"typecheck": None, "lint": None, "build": None}
    
    # Check if node_modules exists, if not skip quality checks
    node_modules = workspace / "node_modules"
    if not node_modules.exists():
        print("  Skipping quality checks (no node_modules)")
    else:
        import subprocess
        
        # TypeScript check
        try:
            result = subprocess.run(
                "pnpm exec tsc --noEmit",
                cwd=workspace, shell=True, capture_output=True,
                text=True, timeout=120
            )
            quality["typecheck"] = "PASS" if result.returncode == 0 else f"FAIL ({result.stderr[:200]})"
        except Exception as e:
            quality["typecheck"] = f"ERROR: {e}"
        
        # Lint check
        try:
            result = subprocess.run(
                "pnpm run lint",
                cwd=workspace, shell=True, capture_output=True,
                text=True, timeout=120
            )
            quality["lint"] = "PASS" if result.returncode == 0 else f"FAIL ({result.stderr[:200]})"
        except Exception as e:
            quality["lint"] = f"ERROR: {e}"
    
    # Print results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print("\n=== TIMING ===")
    for node, duration in metrics["node_times"].items():
        print(f"  {node}: {duration:.1f}s")
    print(f"  TOTAL: {metrics['total_time']:.1f}s")
    
    print(f"\n=== PLAN ===")
    print(f"  Steps: {metrics['steps_count']}")
    
    print(f"\n=== REVIEW ===")
    print(f"  LGTM: {metrics['lgtm_count']}")
    print(f"  LBTM: {metrics['lbtm_count']}")
    
    print(f"\n=== RUN_CODE ===")
    print(f"  Status: {metrics['run_status']}")
    
    print(f"\n=== FILES GENERATED ({len(metrics['files_generated'])}) ===")
    for f in metrics["files_generated"][:15]:
        print(f"  - {f['path']}: {f['lines']} lines")
    if len(metrics["files_generated"]) > 15:
        print(f"  ... and {len(metrics['files_generated']) - 15} more")
    
    print(f"\n=== QUALITY ===")
    for check, result in quality.items():
        print(f"  {check}: {result}")
    
    if metrics["errors"]:
        print(f"\n=== ERRORS ===")
        for err in metrics["errors"]:
            print(f"  - {err}")
    
    # Show sample generated code
    print("\n" + "=" * 70)
    print("SAMPLE GENERATED CODE")
    print("=" * 70)
    
    sample_files = ["prisma/schema.prisma", "src/app/api/books/featured/route.ts"]
    for sample in sample_files:
        sample_path = workspace / sample
        if sample_path.exists():
            print(f"\n### {sample}")
            print("-" * 50)
            content = sample_path.read_text(encoding='utf-8', errors='replace')
            if len(content) > 2000:
                print(content[:1000])
                print(f"\n... [{len(content) - 2000} chars truncated] ...\n")
                print(content[-1000:])
            else:
                print(content)
    
    print("\n" + "=" * 70)
    print(f"TEST COMPLETE - Workspace saved at: {workspace}")
    print("=" * 70)
    
    return metrics, workspace


if __name__ == "__main__":
    asyncio.run(run_full_graph())
