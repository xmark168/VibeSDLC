"""Node functions for Tester graph."""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from uuid import UUID

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from sqlmodel import Session, select

from app.core.db import engine
from app.models import Story, StoryStatus
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback from state."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


async def query_stories(state: TesterState) -> dict:
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


async def analyze_stories(state: TesterState) -> dict:
    """Analyze stories and create test scenarios."""
    stories = state.get("stories", [])
    
    if not stories:
        logger.warning("[TesterGraph] No stories to analyze")
        return {"test_scenarios": [], "error": "No stories found"}
    
    logger.info(f"[TesterGraph] Analyzing {len(stories)} stories")
    
    messages = [
        SystemMessage(content=get_system_prompt("analyze_stories")),
        HumanMessage(content=get_user_prompt("analyze_stories", stories=json.dumps(stories, indent=2)))
    ]
    
    try:
        response = await _llm.ainvoke(messages, config=_cfg(state, "analyze_stories"))
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


async def generate_test_cases(state: TesterState) -> dict:
    """Generate detailed test cases from scenarios."""
    scenarios = state.get("test_scenarios", [])
    
    if not scenarios:
        logger.warning("[TesterGraph] No scenarios to generate test cases")
        return {"test_cases": []}
    
    logger.info(f"[TesterGraph] Generating test cases from {len(scenarios)} scenarios")
    
    messages = [
        SystemMessage(content=get_system_prompt("generate_test_cases")),
        HumanMessage(content=get_user_prompt("generate_test_cases", scenarios=json.dumps(scenarios, indent=2)))
    ]
    
    try:
        response = await _llm.ainvoke(messages, config=_cfg(state, "generate_test_cases"))
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


def _find_existing_test_file(tests_dir: Path) -> Path | None:
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


def _extract_existing_test_titles(content: str) -> set[str]:
    """Extract test titles from existing test file."""
    # Match test('title', ...) or it('title', ...)
    pattern = r"(?:test|it)\s*\(\s*['\"]([^'\"]+)['\"]"
    matches = re.findall(pattern, content)
    return set(matches)


def _filter_duplicate_tests(test_cases: list[dict], existing_titles: set[str]) -> list[dict]:
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


async def generate_test_file(state: TesterState) -> dict:
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
    existing_file = _find_existing_test_file(tests_dir)
    existing_content = ""
    existing_titles = set()
    
    if existing_file:
        existing_content = existing_file.read_text(encoding='utf-8')
        existing_titles = _extract_existing_test_titles(existing_content)
        logger.info(f"[TesterGraph] Found existing file with {len(existing_titles)} tests: {existing_file.name}")
    
    # Filter out duplicate tests
    new_test_cases = _filter_duplicate_tests(test_cases, existing_titles)
    
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
        messages = [
            SystemMessage(content=get_system_prompt("generate_test_file_append")),
            HumanMessage(content=get_user_prompt(
                "generate_test_file_append",
                existing_titles=str(list(existing_titles)[:20]),
                test_cases=json.dumps(new_test_cases, indent=2)
            ))
        ]
    else:
        # New file mode - generate complete file
        messages = [
            SystemMessage(content=get_system_prompt("generate_test_file_new")),
            HumanMessage(content=get_user_prompt(
                "generate_test_file_new",
                test_cases=json.dumps(new_test_cases, indent=2)
            ))
        ]
    
    try:
        response = await _llm.ainvoke(messages, config=_cfg(state, "generate_test_file"))
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
