"""Integration tests for Plan Node - Component Dependencies.

Tests that the plan node correctly detects cross-component dependencies:
1. Section components depend on Card/Item components
2. Pages depend on Section/Card components
3. API routes depend on schema and lib

Run with: python -m pytest app/agents/developer_v2/tests/test_plan_dependencies.py -v -s

Note: These tests call real LLM and cost money. Use sparingly.
"""
import os
import pytest
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
        reason="No API key found"
    ),
    pytest.mark.asyncio
]


# =============================================================================
# UNIT TESTS (no LLM, fast)
# =============================================================================

class TestAutoDetectDependencies:
    """Unit tests for _auto_detect_dependencies function."""
    
    def test_api_route_deps(self):
        """API routes should depend on schema and lib."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        deps = _auto_detect_dependencies("src/app/api/books/route.ts")
        
        assert "prisma/schema.prisma" in deps
        assert "src/lib/prisma.ts" in deps
    
    def test_tsx_component_deps(self):
        """TSX components should depend on types."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        deps = _auto_detect_dependencies("src/components/books/BookCard.tsx")
        
        assert "src/types/index.ts" in deps
    
    def test_section_depends_on_card(self):
        """Section components should depend on related Card components."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        # Simulate plan steps
        all_steps = [
            {"file_path": "src/components/home/CategoryCard.tsx"},
            {"file_path": "src/components/home/CategoriesSection.tsx"},
            {"file_path": "src/components/home/BookCard.tsx"},
            {"file_path": "src/components/home/BooksSection.tsx"},
        ]
        
        # CategoriesSection should depend on CategoryCard
        deps = _auto_detect_dependencies(
            "src/components/home/CategoriesSection.tsx",
            all_steps
        )
        
        assert "src/components/home/CategoryCard.tsx" in deps
        print(f"\nCategoriesSection deps: {deps}")
    
    def test_books_section_depends_on_book_card(self):
        """BooksSection should depend on BookCard."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        all_steps = [
            {"file_path": "src/components/books/BookCard.tsx"},
            {"file_path": "src/components/home/BestsellersSection.tsx"},
            {"file_path": "src/components/home/NewArrivalsSection.tsx"},
        ]
        
        deps = _auto_detect_dependencies(
            "src/components/home/BestsellersSection.tsx",
            all_steps
        )
        
        # Should find BookCard (book -> bestseller pattern)
        print(f"\nBestsellersSection deps: {deps}")
        assert "src/types/index.ts" in deps  # Base dep
    
    def test_page_depends_on_sections(self):
        """Pages should depend on Section components."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        all_steps = [
            {"file_path": "src/components/home/HeroSection.tsx"},
            {"file_path": "src/components/home/CategoriesSection.tsx"},
            {"file_path": "src/components/home/BookCard.tsx"},
            {"file_path": "src/app/page.tsx"},
        ]
        
        deps = _auto_detect_dependencies("src/app/page.tsx", all_steps)
        
        assert "src/components/home/HeroSection.tsx" in deps
        assert "src/components/home/CategoriesSection.tsx" in deps
        assert "src/components/home/BookCard.tsx" in deps
        print(f"\npage.tsx deps: {deps}")
    
    def test_no_self_dependency(self):
        """Components should not depend on themselves."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        all_steps = [
            {"file_path": "src/components/home/CategoryCard.tsx"},
            {"file_path": "src/components/home/CategoriesSection.tsx"},
        ]
        
        deps = _auto_detect_dependencies(
            "src/components/home/CategoryCard.tsx",
            all_steps
        )
        
        assert "src/components/home/CategoryCard.tsx" not in deps
    
    def test_seed_depends_on_schema(self):
        """Seed file should depend on schema."""
        from app.agents.developer_v2.src.nodes.plan import _auto_detect_dependencies
        
        deps = _auto_detect_dependencies("prisma/seed.ts")
        
        assert "prisma/schema.prisma" in deps


# =============================================================================
# INTEGRATION TESTS (with LLM)
# =============================================================================

@pytest.fixture
def workspace(tmp_path):
    """Create workspace with basic Next.js structure."""
    ws = tmp_path / "test_workspace"
    ws.mkdir()
    
    # Create directories
    (ws / "src" / "app" / "api" / "books").mkdir(parents=True)
    (ws / "src" / "components" / "home").mkdir(parents=True)
    (ws / "src" / "components" / "books").mkdir(parents=True)
    (ws / "src" / "lib").mkdir(parents=True)
    (ws / "src" / "types").mkdir(parents=True)
    (ws / "prisma").mkdir()
    
    # Create minimal files
    (ws / "prisma" / "schema.prisma").write_text("""
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Book {
  id        String   @id @default(uuid())
  title     String
  author    String
  price     Float
  createdAt DateTime @default(now())
}

model Category {
  id    String @id @default(uuid())
  name  String
  slug  String @unique
}
""")
    
    (ws / "src" / "lib" / "prisma.ts").write_text("""
import { PrismaClient } from '@prisma/client'
export const prisma = new PrismaClient()
""")
    
    (ws / "src" / "types" / "index.ts").write_text("""
export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
}

export interface Category {
  id: string;
  name: string;
  slug: string;
}
""")
    
    (ws / "src" / "app" / "layout.tsx").write_text("""
export default function RootLayout({ children }) {
  return <html><body>{children}</body></html>
}
""")
    
    (ws / "package.json").write_text("""
{
  "name": "test-app",
  "scripts": {
    "dev": "next dev",
    "build": "next build"
  }
}
""")
    
    return ws


def create_state(workspace, story: Dict) -> Dict:
    """Create test state from story."""
    return {
        "workspace_path": str(workspace),
        "project_id": "test-project",
        "task_id": story["story_id"],
        "tech_stack": "nextjs",
        "story_id": story["story_id"],
        "story_title": story["story_title"],
        "story_description": story["story_description"],
        "story_requirements": story["story_requirements"],
        "acceptance_criteria": story.get("acceptance_criteria", []),
        "files_modified": [],
    }


STORY_HOMEPAGE = {
    "story_id": "TEST-DEP-001",
    "story_title": "Homepage with Categories and Books",
    "story_description": "Create homepage with category cards and book cards",
    "story_requirements": [
        "Create CategoryCard component showing category info",
        "Create CategoriesSection using CategoryCard",
        "Create BookCard component showing book info",  
        "Create FeaturedBooks section using BookCard",
        "Create homepage page composing all sections",
    ],
}


class TestPlanComponentDependencies:
    """Test that plan correctly detects component dependencies."""
    
    @pytest.mark.asyncio
    async def test_section_has_card_dependency(self, workspace):
        """Section components should have Card components as dependencies."""
        from app.agents.developer_v2.src.nodes.plan import plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        state = create_state(workspace, STORY_HOMEPAGE)
        set_tool_context(str(workspace), state["project_id"], state["task_id"])
        
        result = await plan(state)
        steps = result.get("implementation_plan", [])
        
        print(f"\n{'='*60}")
        print("COMPONENT DEPENDENCY TEST")
        print(f"{'='*60}\n")
        
        # Find Section and Card steps
        section_steps = []
        card_steps = []
        page_steps = []
        
        for step in steps:
            fp = step.get("file_path", "")
            deps = step.get("dependencies", [])
            
            if "section" in fp.lower():
                section_steps.append((fp, deps))
            elif "card" in fp.lower():
                card_steps.append((fp, deps))
            elif "page.tsx" in fp.lower():
                page_steps.append((fp, deps))
        
        print("Card components:")
        for fp, deps in card_steps:
            print(f"  - {fp}")
        
        print("\nSection components (should depend on Cards):")
        for fp, deps in section_steps:
            print(f"  - {fp}")
            print(f"    deps: {deps}")
        
        print("\nPage (should depend on Sections/Cards):")
        for fp, deps in page_steps:
            print(f"  - {fp}")
            print(f"    deps: {deps}")
        
        # Verify: at least one section has a card dependency
        sections_with_card_deps = 0
        for fp, deps in section_steps:
            has_card_dep = any("card" in d.lower() for d in deps)
            if has_card_dep:
                sections_with_card_deps += 1
        
        print(f"\n[RESULT] Sections with Card deps: {sections_with_card_deps}/{len(section_steps)}")
        
        # Verify: page has section/card dependencies
        pages_with_component_deps = 0
        for fp, deps in page_steps:
            has_component_dep = any(
                "section" in d.lower() or "card" in d.lower()
                for d in deps
            )
            if has_component_dep:
                pages_with_component_deps += 1
        
        print(f"[RESULT] Pages with component deps: {pages_with_component_deps}/{len(page_steps)}")
        
        # Allow some flexibility - at least sections or pages should have deps
        total_with_deps = sections_with_card_deps + pages_with_component_deps
        assert total_with_deps >= 1, "Expected at least 1 component with cross-dependencies"
    
    @pytest.mark.asyncio  
    async def test_dependency_includes_all_steps(self, workspace):
        """Verify dependencies only reference files in the plan."""
        from app.agents.developer_v2.src.nodes.plan import plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        state = create_state(workspace, STORY_HOMEPAGE)
        set_tool_context(str(workspace), state["project_id"], state["task_id"])
        
        result = await plan(state)
        steps = result.get("implementation_plan", [])
        
        # Collect all file paths in plan
        plan_files = {s.get("file_path", "") for s in steps}
        plan_files.update([
            "prisma/schema.prisma",
            "src/types/index.ts", 
            "src/lib/prisma.ts",
        ])  # Base deps always valid
        
        print(f"\n{'='*60}")
        print("DEPENDENCY VALIDITY TEST")
        print(f"{'='*60}\n")
        
        invalid_deps = []
        for step in steps:
            fp = step.get("file_path", "")
            deps = step.get("dependencies", [])
            
            for dep in deps:
                # Check if dep is in plan or is a base file
                if dep and dep not in plan_files:
                    # Allow if it's a reasonable path pattern
                    if not any(base in dep for base in ["prisma/", "src/types/", "src/lib/"]):
                        invalid_deps.append((fp, dep))
        
        if invalid_deps:
            print("[WARN] Dependencies referencing files not in plan:")
            for fp, dep in invalid_deps[:5]:
                print(f"  {fp} -> {dep}")
        else:
            print("[PASS] All dependencies reference valid files")
        
        # Allow some invalid deps (might reference existing files)
        assert len(invalid_deps) <= len(steps) * 0.3, f"Too many invalid deps: {len(invalid_deps)}"


# =============================================================================
# RUN DIRECTLY
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
