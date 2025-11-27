"""Tester Graph - LangGraph implementation for integration test generation.

Replaces TesterCrew (CrewAI) with LangGraph StateGraph for better control
and streaming capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, Annotated
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from sqlmodel import Session, select

from app.models import Story, StoryStatus
from app.core.db import engine
from app.core.config import settings

logger = logging.getLogger(__name__)


class TesterState(TypedDict):
    """State object shared across all nodes in the graph."""
    
    project_id: str
    story_ids: list[str]
    project_path: str
    tech_stack: str
    timestamp: str
    
    stories: list[dict]
    scenarios: list[dict]
    test_cases: list[dict]
    
    generated_file: str | None
    test_count: int
    stories_covered: list[str]
    
    error: str | None


def _get_llm() -> ChatOpenAI:
    """Get configured LLM instance."""
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=4000,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )


def _query_stories_from_db(project_id: str, story_ids: list[str]) -> list[dict]:
    """Query stories with REVIEW status from database."""
    try:
        with Session(engine) as session:
            query = select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW
            )
            
            if story_ids:
                query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
            
            stories = session.exec(query).all()
            
            return [
                {
                    "id": str(story.id),
                    "title": story.title,
                    "description": story.description,
                    "acceptance_criteria": story.acceptance_criteria,
                    "story_points": story.story_points,
                    "status": story.status.value,
                    "priority": story.priority
                }
                for story in stories
            ]
    except Exception as e:
        logger.error(f"Error querying stories: {e}", exc_info=True)
        return []


def _save_test_file(project_path: str, filename: str, content: str) -> str | None:
    """Save generated test file to project directory."""
    try:
        tests_dir = Path(project_path) / "tests" / "integration"
        tests_dir.mkdir(parents=True, exist_ok=True)
        
        test_file = tests_dir / filename
        test_file.write_text(content, encoding='utf-8')
        
        logger.info(f"Created test file: {test_file}")
        return str(test_file)
    except Exception as e:
        logger.error(f"Error saving test file: {e}", exc_info=True)
        return None


async def analyze_stories_node(state: TesterState) -> dict:
    """Node 1: Query stories from DB and analyze them to create test scenarios."""
    logger.info(f"[AnalyzeNode] Starting analysis for project {state['project_id']}")
    
    stories = _query_stories_from_db(state["project_id"], state["story_ids"])
    
    if not stories:
        logger.warning("[AnalyzeNode] No stories found in REVIEW status")
        return {
            "stories": [],
            "scenarios": [],
            "error": "No stories found in REVIEW status"
        }
    
    logger.info(f"[AnalyzeNode] Found {len(stories)} stories to analyze")
    
    llm = _get_llm()
    
    system_prompt = """You are a senior QA Engineer specializing in Next.js and Prisma integration testing.
Analyze user stories and create comprehensive integration test scenarios.

For each story, extract:
1. API endpoint being tested (e.g., POST /api/users)
2. Database operations (CREATE, READ, UPDATE, DELETE)
3. Test scenarios covering: happy path, error cases, edge cases

Output ONLY valid JSON array, no markdown code blocks."""

    user_prompt = f"""Analyze these user stories in REVIEW status and create test scenarios:

Stories:
{json.dumps(stories, indent=2, ensure_ascii=False)}

Output JSON array format:
[
  {{
    "story_id": "uuid",
    "story_title": "Story Title",
    "api_endpoint": "POST /api/endpoint",
    "http_method": "POST",
    "scenarios": [
      {{
        "scenario_id": "S1",
        "title": "Scenario title",
        "type": "happy_path|error_case|edge_case",
        "description": "What this tests",
        "api_input": {{}},
        "expected_status": 200,
        "db_verification": "What to verify in DB"
      }}
    ]
  }}
]"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        result_str = response.content.strip()
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()
        
        scenarios = json.loads(result_str)
        logger.info(f"[AnalyzeNode] Generated {len(scenarios)} scenario groups")
        
        return {
            "stories": stories,
            "scenarios": scenarios,
            "error": None
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[AnalyzeNode] JSON parse error: {e}")
        return {
            "stories": stories,
            "scenarios": [],
            "error": f"Failed to parse scenarios: {e}"
        }
    except Exception as e:
        logger.error(f"[AnalyzeNode] Error: {e}", exc_info=True)
        return {
            "stories": stories,
            "scenarios": [],
            "error": str(e)
        }


async def generate_test_cases_node(state: TesterState) -> dict:
    """Node 2: Generate detailed test cases from scenarios."""
    if state.get("error"):
        return {"test_cases": []}
    
    if not state.get("scenarios"):
        return {"test_cases": [], "error": "No scenarios to generate test cases from"}
    
    logger.info(f"[TestCasesNode] Generating test cases from {len(state['scenarios'])} scenario groups")
    
    llm = _get_llm()
    
    system_prompt = """You are a meticulous QA Engineer who writes detailed test cases.
Follow the AAA pattern (Arrange, Act, Assert) and include both API and database verification.

Output ONLY valid JSON array, no markdown code blocks."""

    user_prompt = f"""Based on these test scenarios, write detailed integration test cases:

Scenarios:
{json.dumps(state['scenarios'], indent=2, ensure_ascii=False)}

Output JSON array format:
[
  {{
    "test_id": "TC-INT-001",
    "title": "Test case title - API + DB verification",
    "story_id": "uuid",
    "api_endpoint": "POST /api/endpoint",
    "http_method": "POST",
    "test_type": "happy_path|error_case|edge_case",
    "arrange": {{
      "description": "Setup description",
      "test_data": {{}},
      "db_setup": "SQL or Prisma setup needed"
    }},
    "act": {{
      "description": "API call description",
      "request_body": {{}},
      "request_headers": {{}}
    }},
    "assert": {{
      "api_response": {{
        "status_code": 200,
        "body_contains": []
      }},
      "database": {{
        "model": "User",
        "operation": "findUnique",
        "expected_fields": {{}}
      }}
    }}
  }}
]"""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        result_str = response.content.strip()
        if "```json" in result_str:
            result_str = result_str.split("```json")[1].split("```")[0].strip()
        elif "```" in result_str:
            result_str = result_str.split("```")[1].split("```")[0].strip()
        
        test_cases = json.loads(result_str)
        logger.info(f"[TestCasesNode] Generated {len(test_cases)} test cases")
        
        return {
            "test_cases": test_cases,
            "error": None
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"[TestCasesNode] JSON parse error: {e}")
        return {"test_cases": [], "error": f"Failed to parse test cases: {e}"}
    except Exception as e:
        logger.error(f"[TestCasesNode] Error: {e}", exc_info=True)
        return {"test_cases": [], "error": str(e)}


async def generate_test_file_node(state: TesterState) -> dict:
    """Node 3: Generate TypeScript test file from test cases."""
    if state.get("error"):
        return {
            "generated_file": None,
            "test_count": 0,
            "stories_covered": []
        }
    
    if not state.get("test_cases"):
        return {
            "generated_file": None,
            "test_count": 0,
            "stories_covered": [],
            "error": "No test cases to generate file from"
        }
    
    logger.info(f"[GenerateFileNode] Generating test file with {len(state['test_cases'])} test cases")
    
    llm = _get_llm()
    
    system_prompt = """You are a Next.js Test Automation Engineer.
Generate executable Jest integration test code for Next.js API routes with Prisma.

Rules:
- Use NextRequest for API testing
- Import API handlers directly from app/api/
- Use Prisma Client for DB verification
- Include beforeAll, afterAll, beforeEach hooks
- Follow AAA pattern with clear comments
- Use TypeScript with proper types
- Output ONLY the TypeScript code, no markdown code blocks"""

    user_prompt = f"""Generate a complete integration test file for these test cases:

Test Cases:
{json.dumps(state['test_cases'], indent=2, ensure_ascii=False)}

Stories being tested:
{json.dumps(state['stories'], indent=2, ensure_ascii=False)}

Tech Stack: {state['tech_stack']}
Timestamp: {state['timestamp']}

Generate a complete TypeScript test file that:
1. Imports NextRequest, PrismaClient
2. Sets up database connection in beforeAll/afterAll
3. Cleans test data in beforeEach
4. Groups tests by story using describe()
5. Implements each test case using it()
6. Verifies both API response AND database state

Output the complete TypeScript code only, no explanations."""

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        test_content = response.content.strip()
        if "```typescript" in test_content:
            test_content = test_content.split("```typescript")[1].split("```")[0].strip()
        elif "```ts" in test_content:
            test_content = test_content.split("```ts")[1].split("```")[0].strip()
        elif "```" in test_content:
            test_content = test_content.split("```")[1].split("```")[0].strip()
        
        filename = f"review-batch-{state['timestamp']}.integration.test.ts"
        
        file_path = _save_test_file(state["project_path"], filename, test_content)
        
        if not file_path:
            return {
                "generated_file": None,
                "test_count": 0,
                "stories_covered": [],
                "error": "Failed to save test file"
            }
        
        stories_covered = list(set(tc.get("story_id") for tc in state["test_cases"] if tc.get("story_id")))
        
        logger.info(f"[GenerateFileNode] Successfully created {filename}")
        
        return {
            "generated_file": file_path,
            "test_count": len(state["test_cases"]),
            "stories_covered": stories_covered,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"[GenerateFileNode] Error: {e}", exc_info=True)
        return {
            "generated_file": None,
            "test_count": 0,
            "stories_covered": [],
            "error": str(e)
        }


def should_continue_to_test_cases(state: TesterState) -> str:
    """Conditional edge: continue to test cases or end with error."""
    if state.get("error") or not state.get("scenarios"):
        return "end"
    return "generate_test_cases"


def should_continue_to_file(state: TesterState) -> str:
    """Conditional edge: continue to file generation or end with error."""
    if state.get("error") or not state.get("test_cases"):
        return "end"
    return "generate_file"


def create_tester_graph() -> StateGraph:
    """Create and compile the Tester LangGraph."""
    
    graph = StateGraph(TesterState)
    
    graph.add_node("analyze_stories", analyze_stories_node)
    graph.add_node("generate_test_cases", generate_test_cases_node)
    graph.add_node("generate_file", generate_test_file_node)
    
    graph.add_edge(START, "analyze_stories")
    
    graph.add_conditional_edges(
        "analyze_stories",
        should_continue_to_test_cases,
        {
            "generate_test_cases": "generate_test_cases",
            "end": END
        }
    )
    
    graph.add_conditional_edges(
        "generate_test_cases",
        should_continue_to_file,
        {
            "generate_file": "generate_file",
            "end": END
        }
    )
    
    graph.add_edge("generate_file", END)
    
    return graph.compile()


class TesterGraph:
    """LangGraph-based Tester for integration test generation.
    
    Replaces TesterCrew with a more controllable graph-based approach.
    """
    
    def __init__(self):
        self.graph = create_tester_graph()
        logger.info("[TesterGraph] Initialized LangGraph-based tester")
    
    async def generate_tests_from_stories(
        self,
        project_id: str,
        story_ids: list[str],
        project_path: str,
        tech_stack: str = "nodejs-react"
    ) -> dict:
        """Generate integration tests for user stories in REVIEW status.
        
        Args:
            project_id: Project UUID
            story_ids: List of story UUIDs to test
            project_path: Path to project directory
            tech_stack: Technology stack (default: nodejs-react)
            
        Returns:
            Dict with test_file, test_count, stories_covered, error
        """
        logger.info(f"[TesterGraph] Starting test generation for project {project_id}")
        
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        
        initial_state: TesterState = {
            "project_id": project_id,
            "story_ids": story_ids or [],
            "project_path": project_path,
            "tech_stack": tech_stack,
            "timestamp": timestamp,
            "stories": [],
            "scenarios": [],
            "test_cases": [],
            "generated_file": None,
            "test_count": 0,
            "stories_covered": [],
            "error": None
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            return {
                "filename": Path(final_state["generated_file"]).name if final_state.get("generated_file") else None,
                "test_file": final_state.get("generated_file"),
                "test_count": final_state.get("test_count", 0),
                "stories_covered": final_state.get("stories_covered", []),
                "error": final_state.get("error")
            }
            
        except Exception as e:
            logger.error(f"[TesterGraph] Graph execution failed: {e}", exc_info=True)
            return {
                "filename": None,
                "test_file": None,
                "test_count": 0,
                "stories_covered": [],
                "error": str(e)
            }
