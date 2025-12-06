"""Quality tests for Developer V2 - Plan & Implement with real LLM calls.

Tests chi tiết chất lượng của:
1. Plan node - tạo plan với skills đúng cho từng step
2. Implement node - sử dụng preloaded skills đúng cách

Run with: uv run pytest app/agents/developer_v2/tests/test_quality.py -v -s

Note: These tests call real LLM and take several minutes. Use sparingly.
"""
import os
import pytest
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent.parent.parent.parent
load_dotenv(backend_dir / ".env")

pytestmark = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key found"
)

# Story definitions from test_dev_v2_real2.py
STORY_1 = {
    "story_id": "EPIC-001-US-001",
    "epic": "EPIC-001",
    "story_title": "Homepage with featured books and categories",
    "story_description": "The homepage serves as the primary entry point for all visitors, showcasing the bookstore's offerings through curated collections and categories.",
    "story_requirements": [
        "Display hero section with 3-5 featured books",
        "Show 'Bestsellers' section with top 10 books",
        "Display 'New Arrivals' section with latest 8 books",
        "Present main book categories with cover images",
        "Ensure all book cards display: cover, title, author, price, rating",
    ],
    "acceptance_criteria": [
        "Given I am on the homepage, When the page loads, Then I see hero section, bestsellers, and new arrivals",
        "Given I see a book card, Then it displays cover, title, author, price, and rating",
    ],
}

STORY_2 = {
    "story_id": "EPIC-001-US-002",
    "epic": "EPIC-001", 
    "story_title": "Search books by title, author, or keyword",
    "story_description": "Search functionality enables visitors to find books by title, author, or keyword with autocomplete.",
    "story_requirements": [
        "Display search bar in header on all pages",
        "Implement autocomplete after 2+ characters",
        "Search across titles, authors, ISBN",
        "Show up to 8 suggestions with thumbnail",
    ],
    "acceptance_criteria": [
        "Given I type 2+ characters, When I wait, Then I see autocomplete suggestions",
        "Given I click a suggestion, Then I navigate to book detail page",
    ],
}


class TestPlanQuality:
    """Test analyze_and_plan node tạo plan với skills đúng."""
    
    @pytest.fixture
    def mock_state(self, tmp_path):
        """Create state for plan node."""
        workspace = tmp_path / "test_plan"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "prisma").mkdir()
        
        # Create minimal prisma schema
        (workspace / "prisma" / "schema.prisma").write_text("""
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}
""")
        
        return {
            "workspace_path": str(workspace),
            "project_id": "test-project",
            "task_id": "test-task",
            "tech_stack": "nextjs",
            "story_id": STORY_1["story_id"],
            "epic": STORY_1["epic"],
            "story_title": STORY_1["story_title"],
            "story_description": STORY_1["story_description"],
            "story_requirements": STORY_1["story_requirements"],
            "acceptance_criteria": STORY_1["acceptance_criteria"],
            "files_modified": [],
        }
    
    @pytest.mark.asyncio
    async def test_plan_has_skills_for_each_step(self, mock_state):
        """Mỗi step trong plan phải có skills field không rỗng."""
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        set_tool_context(mock_state["workspace_path"], mock_state["project_id"], mock_state["task_id"])
        
        start = datetime.now()
        result = await analyze_and_plan(mock_state)
        elapsed = (datetime.now() - start).total_seconds()
        
        plan = result.get("implementation_plan", [])
        
        print(f"\n[INFO] Plan created in {elapsed:.1f}s with {len(plan)} steps")
        
        # Check each step has skills
        steps_with_skills = 0
        steps_without_skills = 0
        
        for i, step in enumerate(plan):
            skills = step.get("skills", [])
            file_path = step.get("file_path", "")
            
            if skills:
                steps_with_skills += 1
                print(f"  Step {i+1}: {file_path} -> skills={skills}")
            else:
                steps_without_skills += 1
                print(f"  Step {i+1}: {file_path} -> NO SKILLS!")
        
        # At least 80% of steps should have skills
        total = len(plan)
        coverage = steps_with_skills / total * 100 if total > 0 else 0
        
        print(f"\n[RESULT] Skills coverage: {steps_with_skills}/{total} ({coverage:.0f}%)")
        
        assert total > 0, "Plan should have steps"
        assert coverage >= 80, f"At least 80% of steps should have skills, got {coverage:.0f}%"
    
    @pytest.mark.asyncio
    async def test_plan_skills_match_file_type(self, mock_state):
        """Skills phải match với file type."""
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        set_tool_context(mock_state["workspace_path"], mock_state["project_id"], mock_state["task_id"])
        
        result = await analyze_and_plan(mock_state)
        plan = result.get("implementation_plan", [])
        
        print(f"\n[INFO] Checking skills match for {len(plan)} steps")
        
        mismatches = []
        
        for step in plan:
            file_path = step.get("file_path", "")
            skills = step.get("skills", [])
            
            # Check expected skills based on file type
            if "prisma" in file_path.lower() or "schema" in file_path.lower():
                if skills and "database-model" not in skills:
                    mismatches.append(f"{file_path}: expected 'database-model', got {skills}")
            
            elif "/api/" in file_path:
                if skills and "api-route" not in skills:
                    mismatches.append(f"{file_path}: expected 'api-route', got {skills}")
            
            elif file_path.endswith(".tsx") and "/components/" in file_path:
                if skills and "frontend-component" not in skills:
                    mismatches.append(f"{file_path}: expected 'frontend-component', got {skills}")
        
        if mismatches:
            print(f"\n[WARN] Mismatches found:")
            for m in mismatches:
                print(f"  - {m}")
        else:
            print(f"\n[PASS] All skills match file types")
        
        # Allow some mismatches but not too many
        assert len(mismatches) <= len(plan) * 0.2, f"Too many skill mismatches: {mismatches}"
    
    @pytest.mark.asyncio
    async def test_plan_dependencies_valid(self, mock_state):
        """Dependencies phải là file paths hợp lệ (strings, not integers)."""
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.tools import set_tool_context
        
        set_tool_context(mock_state["workspace_path"], mock_state["project_id"], mock_state["task_id"])
        
        result = await analyze_and_plan(mock_state)
        plan = result.get("implementation_plan", [])
        
        print(f"\n[INFO] Checking dependencies for {len(plan)} steps")
        
        invalid_deps = []
        
        for step in plan:
            file_path = step.get("file_path", "")
            deps = step.get("dependencies", [])
            
            for dep in deps:
                if not isinstance(dep, str):
                    invalid_deps.append(f"{file_path}: invalid dep type {type(dep)}: {dep}")
                elif dep and not ("/" in dep or "." in dep):
                    invalid_deps.append(f"{file_path}: suspicious dep (not a path?): {dep}")
        
        if invalid_deps:
            print(f"\n[WARN] Invalid dependencies:")
            for d in invalid_deps:
                print(f"  - {d}")
        else:
            print(f"\n[PASS] All dependencies are valid file paths")
        
        assert len(invalid_deps) == 0, f"Invalid dependencies found: {invalid_deps}"


class TestImplementQuality:
    """Test implement node với preloaded skills."""
    
    @pytest.fixture
    def mock_state_with_plan(self, tmp_path):
        """Create state with a plan step that has skills."""
        workspace = tmp_path / "test_implement"
        workspace.mkdir()
        (workspace / "src").mkdir()
        (workspace / "src" / "components").mkdir()
        (workspace / "src" / "app").mkdir()
        (workspace / "src" / "app" / "api").mkdir()
        (workspace / "src" / "app" / "api" / "books").mkdir()
        
        return {
            "workspace_path": str(workspace),
            "project_id": "test-project",
            "task_id": "test-task",
            "tech_stack": "nextjs",
            "current_step": 0,
            "total_steps": 3,
            "implementation_plan": [
                {
                    "order": 1,
                    "description": "Create BookCard component displaying book info with cover, title, author, price",
                    "file_path": "src/components/BookCard.tsx",
                    "action": "create",
                    "dependencies": [],
                    "skills": ["frontend-component", "frontend-design"]
                },
                {
                    "order": 2,
                    "description": "Create API route for fetching featured books",
                    "file_path": "src/app/api/books/featured/route.ts",
                    "action": "create",
                    "dependencies": [],
                    "skills": ["api-route"]
                },
                {
                    "order": 3,
                    "description": "Create homepage with book sections",
                    "file_path": "src/app/page.tsx",
                    "action": "modify",
                    "dependencies": ["src/components/BookCard.tsx"],
                    "skills": ["frontend-component", "frontend-design"]
                }
            ],
            "logic_analysis": [
                ["src/components/BookCard.tsx", "Book card with cover, title, author, price, rating"],
                ["src/app/api/books/featured/route.ts", "GET endpoint returning featured books"]
            ],
            "dependencies_content": {},
            "files_modified": [],
            "review_count": 0,
            "react_loop_count": 0,
            "debug_count": 0,
        }
    
    @pytest.mark.asyncio
    async def test_implement_creates_component_with_skills(self, mock_state_with_plan):
        """Implement tạo component sử dụng skills từ plan."""
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.tools import set_tool_context
        
        state = mock_state_with_plan
        set_tool_context(state["workspace_path"], state["project_id"], state["task_id"])
        
        start = datetime.now()
        result = await implement(state)
        elapsed = (datetime.now() - start).total_seconds()
        
        # Check file was created
        file_path = Path(state["workspace_path"]) / "src" / "components" / "BookCard.tsx"
        files_modified = result.get("files_modified", [])
        
        print(f"\n[INFO] Implement completed in {elapsed:.1f}s")
        print(f"[INFO] Files modified: {files_modified}")
        print(f"[INFO] File exists: {file_path.exists()}")
        
        assert file_path.exists(), f"BookCard.tsx should be created"
        
        # Check content quality
        content = file_path.read_text()
        print(f"[INFO] File size: {len(content)} chars")
        
        # Should have React component patterns
        assert "export" in content, "Should have export"
        assert "function" in content or "const" in content, "Should have function/const"
        assert "BookCard" in content, "Should have BookCard name"
        
        # Should follow skill patterns (use client if needed)
        if "useState" in content or "useEffect" in content or "onClick" in content:
            assert "'use client'" in content or '"use client"' in content, "Should have 'use client' for client components"
        
        print(f"\n[PASS] Component created with valid patterns")
    
    @pytest.mark.asyncio
    async def test_implement_creates_api_route_with_skills(self, mock_state_with_plan):
        """Implement tạo API route sử dụng skills từ plan."""
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.tools import set_tool_context
        
        # Set to step 1 (API route)
        state = {**mock_state_with_plan, "current_step": 1}
        set_tool_context(state["workspace_path"], state["project_id"], state["task_id"])
        
        # Create parent directory
        api_dir = Path(state["workspace_path"]) / "src" / "app" / "api" / "books" / "featured"
        api_dir.mkdir(parents=True, exist_ok=True)
        
        start = datetime.now()
        result = await implement(state)
        elapsed = (datetime.now() - start).total_seconds()
        
        file_path = api_dir / "route.ts"
        
        print(f"\n[INFO] Implement completed in {elapsed:.1f}s")
        print(f"[INFO] File exists: {file_path.exists()}")
        
        assert file_path.exists(), f"route.ts should be created"
        
        content = file_path.read_text()
        print(f"[INFO] File size: {len(content)} chars")
        
        # Should have API route patterns
        has_get = "export async function GET" in content or "export function GET" in content
        has_post = "export async function POST" in content or "export function POST" in content
        has_next_response = "NextResponse" in content or "NextRequest" in content
        
        assert has_get or has_post, "Should have GET or POST handler"
        assert has_next_response or "Response" in content, "Should use Response/NextResponse"
        
        print(f"\n[PASS] API route created with valid patterns")


class TestEndToEnd:
    """Test full flow: plan → implement multiple steps."""
    
    @pytest.fixture
    def workspace(self, tmp_path):
        """Create workspace with basic structure."""
        workspace = tmp_path / "test_e2e"
        workspace.mkdir()
        
        # Create basic structure
        (workspace / "src").mkdir()
        (workspace / "src" / "app").mkdir()
        (workspace / "src" / "components").mkdir()
        (workspace / "src" / "lib").mkdir()
        (workspace / "prisma").mkdir()
        
        # Create minimal files
        (workspace / "prisma" / "schema.prisma").write_text("""
datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}
""")
        
        (workspace / "src" / "lib" / "prisma.ts").write_text("""
import { PrismaClient } from '@prisma/client'
export const prisma = new PrismaClient()
""")
        
        return workspace
    
    @pytest.mark.asyncio
    async def test_plan_then_implement_first_step(self, workspace):
        """Test plan → implement first step."""
        from app.agents.developer_v2.src.nodes.analyze_and_plan import analyze_and_plan
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.tools import set_tool_context
        
        # Initial state
        state = {
            "workspace_path": str(workspace),
            "project_id": "test-e2e",
            "task_id": "test-e2e-task",
            "tech_stack": "nextjs",
            "story_id": STORY_1["story_id"],
            "epic": STORY_1["epic"],
            "story_title": STORY_1["story_title"],
            "story_description": STORY_1["story_description"],
            "story_requirements": STORY_1["story_requirements"][:3],  # Limit for speed
            "acceptance_criteria": STORY_1["acceptance_criteria"][:1],
            "files_modified": [],
        }
        
        set_tool_context(str(workspace), state["project_id"], state["task_id"])
        
        # Step 1: Plan
        print("\n" + "=" * 60)
        print("STEP 1: PLAN")
        print("=" * 60)
        
        start = datetime.now()
        plan_result = await analyze_and_plan(state)
        plan_elapsed = (datetime.now() - start).total_seconds()
        
        plan = plan_result.get("implementation_plan", [])
        print(f"\n[INFO] Plan created in {plan_elapsed:.1f}s with {len(plan)} steps")
        
        for i, step in enumerate(plan):
            print(f"  {i+1}. {step.get('file_path')} -> skills={step.get('skills', [])}")
        
        assert len(plan) > 0, "Plan should have steps"
        
        # Step 2: Implement first step
        print("\n" + "=" * 60)
        print("STEP 2: IMPLEMENT (first step)")
        print("=" * 60)
        
        impl_state = {
            **state,
            **plan_result,
            "current_step": 0,
            "review_count": 0,
            "react_loop_count": 0,
            "debug_count": 0,
        }
        
        start = datetime.now()
        impl_result = await implement(impl_state)
        impl_elapsed = (datetime.now() - start).total_seconds()
        
        files_modified = impl_result.get("files_modified", [])
        print(f"\n[INFO] Implement completed in {impl_elapsed:.1f}s")
        print(f"[INFO] Files modified: {files_modified}")
        
        # Verify file was created
        if plan:
            first_file = plan[0].get("file_path", "")
            if first_file:
                full_path = workspace / first_file
                print(f"[INFO] Checking: {full_path}")
                print(f"[INFO] Exists: {full_path.exists()}")
                
                if full_path.exists():
                    content = full_path.read_text()
                    print(f"[INFO] Size: {len(content)} chars")
                    print(f"\n[PASS] File created successfully!")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Plan time: {plan_elapsed:.1f}s")
        print(f"Implement time: {impl_elapsed:.1f}s")
        print(f"Total: {plan_elapsed + impl_elapsed:.1f}s")
        print(f"Steps planned: {len(plan)}")
        print(f"Files created: {len(files_modified)}")
        
        # At least one file should be created
        assert len(files_modified) > 0 or len(plan) == 0, "Should create at least one file"
