"""Tester LangGraph - Integration test generation using LangGraph StateGraph."""

import json
import logging
from datetime import datetime
from typing import TypedDict, Annotated, Literal
from uuid import UUID

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from sqlmodel import Session, select
from pathlib import Path

from app.models import Story, StoryStatus
from app.core.db import engine

logger = logging.getLogger(__name__)


class TesterState(TypedDict):
    """State for Tester LangGraph."""
    # Input
    project_id: str
    story_ids: list[str]
    project_path: str
    tech_stack: str
    timestamp: str
    
    # Processing state
    stories: list[dict]
    test_scenarios: list[dict]
    test_cases: list[dict]
    test_content: str
    
    # Output
    result: dict
    error: str | None


class TesterGraph:
    """LangGraph-based Tester for integration test generation."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph."""
        workflow = StateGraph(TesterState)
        
        # Add nodes
        workflow.add_node("query_stories", self._query_stories_node)
        workflow.add_node("analyze_stories", self._analyze_stories_node)
        workflow.add_node("generate_test_cases", self._generate_test_cases_node)
        workflow.add_node("generate_test_file", self._generate_test_file_node)
        
        # Add edges
        workflow.set_entry_point("query_stories")
        workflow.add_edge("query_stories", "analyze_stories")
        workflow.add_edge("analyze_stories", "generate_test_cases")
        workflow.add_edge("generate_test_cases", "generate_test_file")
        workflow.add_edge("generate_test_file", END)
        
        return workflow.compile()
    
    def _query_stories_node(self, state: TesterState) -> dict:
        """Query stories from database with REVIEW status."""
        logger.info(f"[TesterGraph] Querying stories for project {state['project_id']}")
        
        try:
            with Session(engine) as session:
                query = select(Story).where(
                    Story.project_id == UUID(state['project_id']),
                    Story.status == StoryStatus.REVIEW
                )
                
                if state.get('story_ids'):
                    query = query.where(Story.id.in_([UUID(sid) for sid in state['story_ids']]))
                
                stories = session.exec(query).all()
                
                stories_data = [
                    {
                        "id": str(story.id),
                        "title": story.title,
                        "description": story.description,
                        "acceptance_criteria": story.acceptance_criteria,
                        "story_points": story.story_point,
                        "status": story.status.value,
                        "priority": story.priority
                    }
                    for story in stories
                ]
                
                logger.info(f"[TesterGraph] Retrieved {len(stories_data)} stories with REVIEW status")
                return {"stories": stories_data}
                
        except Exception as e:
            logger.error(f"[TesterGraph] Error querying stories: {e}", exc_info=True)
            return {"stories": [], "error": str(e)}
    
    def _analyze_stories_node(self, state: TesterState) -> dict:
        """Analyze stories and create test scenarios."""
        stories = state.get("stories", [])
        
        if not stories:
            logger.warning("[TesterGraph] No stories to analyze")
            return {"test_scenarios": [], "error": "No stories found"}
        
        logger.info(f"[TesterGraph] Analyzing {len(stories)} stories")
        
        prompt = f"""You are a senior QA Engineer specializing in Next.js and Prisma integration testing.

Analyze these user stories and create comprehensive integration test scenarios:

STORIES:
{json.dumps(stories, indent=2)}

For each story, identify:
1. API endpoint to test (from acceptance criteria)
2. Database operations (CREATE, READ, UPDATE, DELETE)
3. Test scenarios: happy path, error cases, edge cases, validation

Output ONLY valid JSON array of test scenarios:
[
  {{
    "story_id": "...",
    "story_title": "...",
    "api_endpoint": "POST /api/xxx",
    "scenarios": [
      {{
        "name": "Happy path - successful operation",
        "type": "happy_path",
        "db_setup": "Create test user",
        "api_call": "POST /api/xxx with valid data",
        "expected_response": "200 OK with data",
        "db_verification": "Verify record created/updated"
      }}
    ]
  }}
]"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            test_scenarios = json.loads(content)
            logger.info(f"[TesterGraph] Generated {len(test_scenarios)} test scenarios")
            return {"test_scenarios": test_scenarios}
            
        except Exception as e:
            logger.error(f"[TesterGraph] Error analyzing stories: {e}", exc_info=True)
            return {"test_scenarios": [], "error": str(e)}
    
    def _generate_test_cases_node(self, state: TesterState) -> dict:
        """Generate detailed test cases from scenarios."""
        scenarios = state.get("test_scenarios", [])
        
        if not scenarios:
            logger.warning("[TesterGraph] No scenarios to generate test cases")
            return {"test_cases": []}
        
        logger.info(f"[TesterGraph] Generating test cases from {len(scenarios)} scenarios")
        
        prompt = f"""You are a meticulous QA Engineer who writes integration test cases.

Convert these test scenarios into detailed test cases:

SCENARIOS:
{json.dumps(scenarios, indent=2)}

For each scenario, create test case with:
- Test ID: TC-INT-001, TC-INT-002, ...
- Title: Clear description of API + DB verification
- Steps: Arrange (DB setup), Act (API call), Assert (verify response + DB)
- Expected Results: Both API response and DB state

Output ONLY valid JSON array:
[
  {{
    "id": "TC-INT-001",
    "title": "Successful login - verify API response and DB user read",
    "story_id": "...",
    "arrange": "Create test user with hashed password",
    "act": "POST /api/login with valid credentials",
    "assert_api": "200 OK with authToken",
    "assert_db": "User record exists with matching credentials"
  }}
]"""
        
        try:
            response = self.llm.invoke(prompt)
            content = response.content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            test_cases = json.loads(content)
            logger.info(f"[TesterGraph] Generated {len(test_cases)} test cases")
            return {"test_cases": test_cases}
            
        except Exception as e:
            logger.error(f"[TesterGraph] Error generating test cases: {e}", exc_info=True)
            return {"test_cases": [], "error": str(e)}
    
    def _find_existing_test_file(self, tests_dir: Path) -> Path | None:
        """Find existing integration test file to append to."""
        if not tests_dir.exists():
            return None
        
        # Look for main integration test file
        main_file = tests_dir / "integration.test.ts"
        if main_file.exists():
            return main_file
        
        # Or find most recent test file
        test_files = list(tests_dir.glob("*.integration.test.ts"))
        if test_files:
            return max(test_files, key=lambda f: f.stat().st_mtime)
        
        return None
    
    def _extract_existing_test_titles(self, content: str) -> set[str]:
        """Extract test titles from existing test file."""
        import re
        # Match test('title', ...) or it('title', ...)
        pattern = r"(?:test|it)\s*\(\s*['\"]([^'\"]+)['\"]"
        matches = re.findall(pattern, content)
        return set(matches)
    
    def _filter_duplicate_tests(self, test_cases: list[dict], existing_titles: set[str]) -> list[dict]:
        """Filter out test cases that already exist."""
        new_tests = []
        for tc in test_cases:
            title = tc.get("title", "")
            # Check if similar test exists (fuzzy match on key words)
            is_duplicate = False
            for existing in existing_titles:
                # Simple duplicate detection: same title or very similar
                if title.lower() == existing.lower():
                    is_duplicate = True
                    break
                # Check if key parts match (e.g., "login" + "successful")
                title_words = set(title.lower().split())
                existing_words = set(existing.lower().split())
                common_words = title_words & existing_words
                if len(common_words) >= 3:  # At least 3 common words
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                new_tests.append(tc)
            else:
                logger.info(f"[TesterGraph] Skipping duplicate test: {title}")
        
        return new_tests
    
    def _generate_test_file_node(self, state: TesterState) -> dict:
        """Generate TypeScript test file - append to existing or create new."""
        test_cases = state.get("test_cases", [])
        project_path = state.get("project_path", "")
        timestamp = state.get("timestamp", datetime.now().strftime("%Y-%m-%d-%H%M%S"))
        stories = state.get("stories", [])
        
        if not test_cases:
            logger.warning("[TesterGraph] No test cases to generate file")
            return {"result": {"error": "No test cases"}}
        
        tests_dir = Path(project_path) / "tests" / "integration"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for existing test file
        existing_file = self._find_existing_test_file(tests_dir)
        existing_content = ""
        existing_titles = set()
        
        if existing_file:
            existing_content = existing_file.read_text(encoding='utf-8')
            existing_titles = self._extract_existing_test_titles(existing_content)
            logger.info(f"[TesterGraph] Found existing file with {len(existing_titles)} tests: {existing_file.name}")
        
        # Filter out duplicate tests
        new_test_cases = self._filter_duplicate_tests(test_cases, existing_titles)
        
        if not new_test_cases:
            logger.info("[TesterGraph] All test cases already exist, skipping generation")
            return {"result": {
                "filename": existing_file.name if existing_file else None,
                "test_count": 0,
                "skipped_duplicates": len(test_cases),
                "stories_covered": [s.get("id") for s in stories],
                "message": "All tests already exist"
            }}
        
        logger.info(f"[TesterGraph] Generating {len(new_test_cases)} new test cases ({len(test_cases) - len(new_test_cases)} duplicates skipped)")
        
        if existing_file and existing_content:
            # Append mode - generate only new tests
            prompt = f"""You are an expert Next.js test automation engineer.

Generate ONLY the new test functions to append to an existing test file.

EXISTING TESTS IN FILE (DO NOT DUPLICATE):
{list(existing_titles)[:20]}

NEW TEST CASES TO ADD:
{json.dumps(new_test_cases, indent=2)}

Requirements:
1. Generate ONLY the test() functions - no imports, no describe block wrapper
2. Use NextRequest for API testing
3. Use PrismaClient (already imported as 'prisma')
4. AAA pattern (Arrange, Act, Assert)
5. Each test should be independent

Output ONLY the test functions (no markdown):
  test('Test title here', async () => {{
    // Arrange
    ...
    // Act
    ...
    // Assert
    ...
  }});
"""
        else:
            # New file mode - generate complete file
            prompt = f"""You are an expert Next.js test automation engineer.

Generate a complete TypeScript integration test file for Jest + Prisma.

TEST CASES:
{json.dumps(new_test_cases, indent=2)}

Requirements:
1. Use NextRequest for API testing
2. Import API handlers from app/api/
3. Use PrismaClient for DB verification
4. Setup/teardown with beforeAll, afterAll, beforeEach
5. AAA pattern (Arrange, Act, Assert)
6. Include proper TypeScript types

Output ONLY the complete TypeScript test file code (no markdown, no explanation):
import {{ NextRequest }} from 'next/server';
...
"""
        
        try:
            response = self.llm.invoke(prompt)
            new_content = response.content.strip()
            
            # Remove markdown code blocks if present
            if new_content.startswith("```typescript"):
                new_content = new_content[13:]
            elif new_content.startswith("```ts"):
                new_content = new_content[5:]
            elif new_content.startswith("```"):
                new_content = new_content[3:]
            
            if new_content.endswith("```"):
                new_content = new_content[:-3]
            
            new_content = new_content.strip()
            
            if existing_file and existing_content:
                # Append to existing file - insert before closing });
                # Find the last }); which closes the describe block
                insert_pos = existing_content.rfind("});")
                if insert_pos > 0:
                    final_content = (
                        existing_content[:insert_pos] + 
                        "\n\n  // === New tests added " + timestamp + " ===\n" +
                        new_content + "\n" +
                        existing_content[insert_pos:]
                    )
                else:
                    final_content = existing_content + "\n\n" + new_content
                
                existing_file.write_text(final_content, encoding='utf-8')
                filename = existing_file.name
                logger.info(f"[TesterGraph] Appended {len(new_test_cases)} tests to: {existing_file}")
            else:
                # Create new file
                filename = "integration.test.ts"
                test_file = tests_dir / filename
                test_file.write_text(new_content, encoding='utf-8')
                logger.info(f"[TesterGraph] Created new test file: {test_file}")
            
            result = {
                "filename": filename,
                "path": str(tests_dir / filename),
                "test_count": len(new_test_cases),
                "skipped_duplicates": len(test_cases) - len(new_test_cases),
                "stories_covered": [s.get("id") for s in stories]
            }
            
            return {"test_content": new_content, "result": result}
            
        except Exception as e:
            logger.error(f"[TesterGraph] Error generating test file: {e}", exc_info=True)
            return {"result": {"error": str(e)}}
    
    async def generate_tests(
        self,
        project_id: str,
        story_ids: list[str],
        project_path: str,
        tech_stack: str = "nodejs-react"
    ) -> dict:
        """Generate integration tests for stories in REVIEW status.
        
        Args:
            project_id: Project UUID
            story_ids: List of story UUIDs to test
            project_path: Path to project directory
            tech_stack: Technology stack
            
        Returns:
            Result dict with filename, test_count, stories_covered
        """
        logger.info(f"[TesterGraph] Starting integration test generation for project {project_id}")
        
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        
        initial_state: TesterState = {
            "project_id": project_id,
            "story_ids": story_ids or [],
            "project_path": project_path,
            "tech_stack": tech_stack,
            "timestamp": timestamp,
            "stories": [],
            "test_scenarios": [],
            "test_cases": [],
            "test_content": "",
            "result": {},
            "error": None
        }
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        result = final_state.get("result", {})
        error = final_state.get("error")
        
        if error:
            result["error"] = error
        
        return result
