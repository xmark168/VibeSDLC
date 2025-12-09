"""Test Homepage Story with Parallel Implementation.

Run with: uv run python -m pytest app/agents/developer_v2/tests/test_homepage_parallel.py -v -s

This test:
1. Creates a plan for HOMEPAGE_STORY
2. Analyzes the plan quality
3. Runs parallel implementation
4. Reports timing and quality metrics
"""
import os
import time
import asyncio
import logging
import pytest
from pathlib import Path
from datetime import datetime

# Load .env
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("test_homepage")

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key found"
)

# Test data
HOMEPAGE_STORY = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "title": "Homepage with Featured Books",
    "description": """As a first-time visitor, I want to see a clear homepage layout with featured books so that I can quickly understand what the bookstore offers and start browsing.

Create the foundational homepage that serves as the entry point for all customers. This page must establish trust, showcase the bookstore's offerings, and provide clear navigation paths. The homepage should highlight popular textbooks, display trust indicators (return policy, genuine books guarantee), and make the search functionality immediately accessible. This is the first impression that determines whether visitors will continue shopping or leave.""",
    "requirements": [
        "Display hero section with main value proposition and call-to-action button",
        "Show featured/bestselling textbooks section with book covers, titles, prices, and stock status",
        "Include prominent search bar at the top of the page with placeholder text guiding users",
        "Display trust indicators: return policy (7-14 days), genuine books guarantee, contact information (phone, store address)",
        "Show category navigation menu organized by grade levels (6-12, university) and subjects",
        "Include footer with quick links to policies, about us, and contact information",
        "Ensure responsive design that works on mobile, tablet, and desktop devices",
        "Display loading states for dynamic content and handle empty states gracefully"
    ],
    "acceptance_criteria": [
        "Given a user visits the homepage, When the page loads, Then they see the hero section, featured books (at least 8 items), search bar, and trust indicators within 3 seconds",
        "Given a user views featured books, When they hover over a book, Then they see a visual indication (shadow/border) and can click to view details",
        "Given a user is on mobile device, When they access the homepage, Then all elements are properly sized and the layout adapts to screen width without horizontal scrolling",
        "Given the featured books section is empty, When the page loads, Then display a friendly message 'New books coming soon! Check back later' instead of blank space",
        "Given a user clicks on a category in navigation menu, When the page loads, Then they are directed to the filtered book listing page for that category",
        "Given a user clicks on trust indicators (return policy, guarantee), When clicked, Then they are directed to detailed policy pages with full information"
    ]
}


def format_story_content(story: dict) -> str:
    """Format story for LLM input."""
    parts = [
        f"# {story['title']}",
        f"\n## Description\n{story['description']}",
        "\n## Requirements",
    ]
    for i, req in enumerate(story["requirements"], 1):
        parts.append(f"{i}. {req}")
    
    parts.append("\n## Acceptance Criteria")
    for i, ac in enumerate(story["acceptance_criteria"], 1):
        parts.append(f"{i}. {ac}")
    
    return "\n".join(parts)


class TestHomepageParallel:
    """Test Homepage Story with parallel implementation."""
    
    @pytest.fixture
    def workspace(self, tmp_path):
        """Create test workspace with boilerplate structure."""
        ws = tmp_path / "bookstore"
        ws.mkdir()
        
        # Create basic structure
        (ws / "src" / "app").mkdir(parents=True)
        (ws / "src" / "app" / "api").mkdir(parents=True)
        (ws / "src" / "components").mkdir(parents=True)
        (ws / "src" / "lib").mkdir(parents=True)
        (ws / "src" / "types").mkdir(parents=True)
        (ws / "prisma").mkdir()
        
        # Create minimal files
        (ws / "package.json").write_text('{"name": "bookstore", "dependencies": {}}')
        (ws / "prisma" / "schema.prisma").write_text('''
generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Book {
  id          String   @id @default(cuid())
  title       String
  author      String
  price       Float
  imageUrl    String?
  isFeatured  Boolean  @default(false)
  categoryId  String
  category    Category @relation(fields: [categoryId], references: [id])
  createdAt   DateTime @default(now())
}

model Category {
  id    String @id @default(cuid())
  name  String
  slug  String @unique
  books Book[]
}
''')
        
        (ws / "src" / "lib" / "prisma.ts").write_text('''
import { PrismaClient } from "@prisma/client";
export const prisma = new PrismaClient();
''')
        
        (ws / "src" / "types" / "index.ts").write_text('''
export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
  imageUrl?: string;
  isFeatured: boolean;
  categoryId: string;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
}
''')
        
        return ws
    
    @pytest.mark.asyncio
    async def test_plan_quality(self, workspace):
        """Test plan generation quality for Homepage story."""
        from app.agents.developer_v2.src.nodes.plan import plan
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        logger.info("=" * 60)
        logger.info("TEST: Plan Quality for Homepage Story")
        logger.info("=" * 60)
        
        # Prepare state
        state = {
            "workspace_path": str(workspace),
            "project_id": "test-bookstore",
            "task_id": HOMEPAGE_STORY["story_id"],
            "tech_stack": "nextjs",
            "story_summary": HOMEPAGE_STORY["title"],
            "story_content": format_story_content(HOMEPAGE_STORY),
            "files_modified": [],
            "dependencies_content": {
                "prisma/schema.prisma": (workspace / "prisma" / "schema.prisma").read_text(),
                "src/types/index.ts": (workspace / "src" / "types" / "index.ts").read_text(),
            },
        }
        
        # Run plan
        start_time = time.time()
        result = await plan(state)
        plan_time = time.time() - start_time
        
        # Analyze results
        impl_plan = result.get("implementation_plan", [])
        total_steps = result.get("total_steps", 0)
        
        logger.info(f"\n📋 PLAN RESULTS:")
        logger.info(f"  Total steps: {total_steps}")
        logger.info(f"  Time: {plan_time:.1f}s")
        
        # Print each step
        logger.info(f"\n📝 STEPS:")
        for step in impl_plan:
            order = step.get("order", "?")
            file_path = step.get("file_path", "unknown")
            task = step.get("task", step.get("description", ""))[:60]
            skills = step.get("skills", [])
            deps = step.get("dependencies", [])
            
            logger.info(f"  [{order}] {file_path}")
            logger.info(f"      Task: {task}...")
            logger.info(f"      Skills: {skills}")
            if deps:
                logger.info(f"      Deps: {deps}")
        
        # Analyze layer distribution
        from app.agents.developer_v2.src.nodes.parallel_utils import (
            group_steps_by_layer,
            should_use_parallel
        )
        
        layers = group_steps_by_layer(impl_plan)
        can_parallel = should_use_parallel(impl_plan)
        
        logger.info(f"\n🔀 PARALLEL ANALYSIS:")
        logger.info(f"  Can use parallel: {can_parallel}")
        logger.info(f"  Layer distribution:")
        for layer_num in sorted(layers.keys()):
            layer_steps = layers[layer_num]
            mode = "PARALLEL" if len(layer_steps) > 1 else "SEQUENTIAL"
            logger.info(f"    Layer {layer_num}: {len(layer_steps)} steps - {mode}")
            for step in layer_steps:
                logger.info(f"      - {step.get('file_path', 'unknown')}")
        
        # Quality checks
        logger.info(f"\n✅ QUALITY CHECKS:")
        
        # 1. Has schema step?
        has_schema = any("schema" in s.get("file_path", "").lower() for s in impl_plan)
        logger.info(f"  Has schema step: {has_schema}")
        
        # 2. Has API routes?
        api_steps = [s for s in impl_plan if "/api/" in s.get("file_path", "")]
        logger.info(f"  API routes: {len(api_steps)}")
        
        # 3. Has components?
        component_steps = [s for s in impl_plan if "/components/" in s.get("file_path", "")]
        logger.info(f"  Components: {len(component_steps)}")
        
        # 4. Has page?
        page_steps = [s for s in impl_plan if "page.tsx" in s.get("file_path", "")]
        logger.info(f"  Pages: {len(page_steps)}")
        
        # 5. Skills assigned?
        steps_with_skills = [s for s in impl_plan if s.get("skills")]
        logger.info(f"  Steps with skills: {len(steps_with_skills)}/{total_steps}")
        
        # 6. Dependencies assigned?
        steps_with_deps = [s for s in impl_plan if s.get("dependencies")]
        logger.info(f"  Steps with dependencies: {len(steps_with_deps)}/{total_steps}")
        
        # Performance estimate
        if can_parallel:
            seq_time = total_steps * 20  # 20s per step
            par_time = 0
            for layer_steps in layers.values():
                batches = (len(layer_steps) + 2) // 3
                par_time += batches * 20
            
            logger.info(f"\n⏱️ PERFORMANCE ESTIMATE:")
            logger.info(f"  Sequential: ~{seq_time}s")
            logger.info(f"  Parallel: ~{par_time}s")
            logger.info(f"  Speedup: {seq_time/par_time:.1f}x ({(1-par_time/seq_time)*100:.0f}% faster)")
        
        # Assertions
        assert total_steps >= 5, f"Expected at least 5 steps, got {total_steps}"
        assert len(component_steps) >= 2, "Should have at least 2 component steps"
        assert len(page_steps) >= 1, "Should have at least 1 page step"
        
        logger.info(f"\n✅ PLAN QUALITY: PASSED")
        
        return result
    
    @pytest.mark.asyncio
    async def test_parallel_layer_execution(self, workspace):
        """Test that parallel execution respects layer order."""
        from app.agents.developer_v2.src.nodes.parallel_utils import (
            group_steps_by_layer,
            run_layer_parallel,
        )
        
        logger.info("=" * 60)
        logger.info("TEST: Parallel Layer Execution")
        logger.info("=" * 60)
        
        # Simulated plan steps
        steps = [
            {"order": 1, "file_path": "prisma/schema.prisma", "task": "Update schema"},
            {"order": 2, "file_path": "prisma/seed.ts", "task": "Create seed"},
            {"order": 3, "file_path": "src/app/api/books/route.ts", "task": "Books API"},
            {"order": 4, "file_path": "src/app/api/categories/route.ts", "task": "Categories API"},
            {"order": 5, "file_path": "src/components/BookCard.tsx", "task": "BookCard"},
            {"order": 6, "file_path": "src/components/CategoryCard.tsx", "task": "CategoryCard"},
            {"order": 7, "file_path": "src/components/FeaturedBooks.tsx", "task": "FeaturedBooks section"},
            {"order": 8, "file_path": "src/components/HeroSection.tsx", "task": "Hero section"},
            {"order": 9, "file_path": "src/app/page.tsx", "task": "Homepage"},
        ]
        
        layers = group_steps_by_layer(steps)
        
        # Track execution
        execution_log = []
        layer_start_times = {}
        layer_end_times = {}
        
        async def mock_implement(step, state):
            file_path = step["file_path"]
            layer = list(layers.keys())[list(layers.values()).index(
                next(l for l in layers.values() if step in l)
            )]
            
            start = time.time()
            execution_log.append({
                "file": file_path,
                "layer": layer,
                "start": start,
                "action": "START"
            })
            
            # Simulate work (200ms)
            await asyncio.sleep(0.2)
            
            end = time.time()
            execution_log.append({
                "file": file_path,
                "layer": layer,
                "end": end,
                "action": "END"
            })
            
            return {"success": True, "file_path": file_path, "modified_files": [file_path]}
        
        # Execute layers in order
        total_start = time.time()
        all_results = []
        
        for layer_num in sorted(layers.keys()):
            layer_steps = layers[layer_num]
            layer_start_times[layer_num] = time.time()
            
            logger.info(f"\n🔄 Executing Layer {layer_num} ({len(layer_steps)} steps)")
            
            results = await run_layer_parallel(layer_steps, mock_implement, {})
            all_results.extend(results)
            
            layer_end_times[layer_num] = time.time()
            layer_time = layer_end_times[layer_num] - layer_start_times[layer_num]
            logger.info(f"   Layer {layer_num} completed in {layer_time:.2f}s")
        
        total_time = time.time() - total_start
        
        # Analyze results
        logger.info(f"\n📊 EXECUTION ANALYSIS:")
        logger.info(f"  Total time: {total_time:.2f}s")
        logger.info(f"  Steps executed: {len(all_results)}")
        
        # Verify layer order
        logger.info(f"\n🔍 LAYER ORDER VERIFICATION:")
        sorted_layers = sorted(layers.keys())
        order_correct = True
        
        for i in range(len(sorted_layers) - 1):
            current = sorted_layers[i]
            next_layer = sorted_layers[i + 1]
            
            if layer_end_times[current] > layer_start_times[next_layer]:
                logger.error(f"   ❌ Layer {current} ended AFTER layer {next_layer} started!")
                order_correct = False
            else:
                logger.info(f"   ✅ Layer {current} → Layer {next_layer} (correct order)")
        
        # Verify parallel execution within layers
        logger.info(f"\n🔍 PARALLEL EXECUTION VERIFICATION:")
        for layer_num, layer_steps in layers.items():
            if len(layer_steps) > 1:
                # Check if steps started at similar times
                starts = [e for e in execution_log 
                         if e["layer"] == layer_num and e["action"] == "START"]
                if len(starts) > 1:
                    time_diff = max(s["start"] for s in starts) - min(s["start"] for s in starts)
                    is_parallel = time_diff < 0.1  # Started within 100ms
                    status = "✅ PARALLEL" if is_parallel else "⚠️ SEQUENTIAL"
                    logger.info(f"   Layer {layer_num}: {status} (start diff: {time_diff:.3f}s)")
        
        # Performance comparison
        seq_time = len(steps) * 0.2  # 200ms each sequential
        speedup = seq_time / total_time
        
        logger.info(f"\n⏱️ PERFORMANCE:")
        logger.info(f"  Sequential would take: {seq_time:.2f}s")
        logger.info(f"  Parallel took: {total_time:.2f}s")
        logger.info(f"  Speedup: {speedup:.1f}x")
        
        assert order_correct, "Layer execution order was incorrect"
        assert speedup > 1.2, f"Expected speedup > 1.2x, got {speedup:.1f}x"
        
        logger.info(f"\n✅ PARALLEL EXECUTION: PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
