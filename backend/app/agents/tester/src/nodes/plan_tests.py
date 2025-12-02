"""Plan Tests node - Analyze stories and create test plan."""

import json
import logging
import os
import re
import unicodedata
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.core_nodes import detect_testing_context
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)

# Use custom API endpoint if configured
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = ChatOpenAI(
    model=_model,
    temperature=0,
    api_key=_api_key,
    base_url=_base_url,
) if _base_url else ChatOpenAI(model=_model, temperature=0)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM response."""
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    # Extract from markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[_parse_json] Failed: {content[:300]}...")
        raise e


def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:50] if text else "unnamed"


def _detect_test_structure(project_path: str) -> dict:
    """Detect existing test folder structure in the project.
    
    Strategy:
    1. First try: Find from existing test FILES (*.test.ts, *.spec.ts)
    2. Fallback: Check for common test FOLDERS
    
    Returns:
        dict with:
        - integration_folder: Path for integration tests
        - e2e_folder: Path for e2e tests
        - existing_tests: List of existing test files
        - existing_specs: List of existing spec files
    """
    from pathlib import Path
    
    structure = {
        "integration_folder": "tests/integration",  # default
        "e2e_folder": "e2e",  # default
        "existing_tests": [],
        "existing_specs": [],
    }
    
    path = Path(project_path)
    if not path.exists():
        return structure
    
    # 1. First try: Find from existing test FILES
    test_files = list(path.glob("**/*.test.ts")) + list(path.glob("**/*.test.js"))
    test_files = [f for f in test_files if "node_modules" not in str(f)]
    
    if test_files:
        # Sort by path depth (prefer shallower paths)
        test_files.sort(key=lambda f: len(f.parts))
        first_test = test_files[0].relative_to(path)
        structure["integration_folder"] = str(first_test.parent)
        structure["existing_tests"] = [str(f.relative_to(path)) for f in test_files[:5]]
        logger.info(f"[_detect_test_structure] Found integration folder from files: {structure['integration_folder']}")
    else:
        # 2. Fallback: Check for common test FOLDERS
        integration_candidates = [
            "src/__tests__/integration",
            "src/__tests__",
            "__tests__/integration",
            "__tests__",
            "tests/integration",
            "tests",
            "test/integration",
            "test",
        ]
        for folder in integration_candidates:
            if (path / folder).is_dir():
                structure["integration_folder"] = folder
                logger.info(f"[_detect_test_structure] Found integration folder from dir: {folder}")
                break
    
    # E2E detection - similar logic
    spec_files = list(path.glob("**/*.spec.ts")) + list(path.glob("**/*.spec.js"))
    spec_files = [f for f in spec_files if "node_modules" not in str(f)]
    
    if spec_files:
        spec_files.sort(key=lambda f: len(f.parts))
        first_spec = spec_files[0].relative_to(path)
        structure["e2e_folder"] = str(first_spec.parent)
        structure["existing_specs"] = [str(f.relative_to(path)) for f in spec_files[:5]]
        logger.info(f"[_detect_test_structure] Found e2e folder from files: {structure['e2e_folder']}")
    else:
        # Fallback: Check for e2e folders
        e2e_candidates = [
            "src/__tests__/e2e",
            "__tests__/e2e",
            "e2e",
            "tests/e2e",
            "playwright",
        ]
        for folder in e2e_candidates:
            if (path / folder).is_dir():
                structure["e2e_folder"] = folder
                logger.info(f"[_detect_test_structure] Found e2e folder from dir: {folder}")
                break
    
    return structure


async def plan_tests(state: TesterState, agent=None) -> dict:
    """Analyze stories and create test plan.
    
    This node:
    1. Detects testing context (auth, ORM, mocks, ESM warnings)
    2. Analyzes stories to identify testable scenarios
    3. Decides test type (integration vs e2e) for each
    4. Creates a step-by-step test plan
    
    Output:
    - test_plan: List of test steps
    - testing_context: Auth patterns, ORM, existing mocks
    - total_steps: Number of steps
    - current_step: 0 (starting)
    """
    print("[NODE] plan_tests")
    
    stories = state.get("stories", [])
    project_id = state.get("project_id", "")
    
    # Get project path and detect testing context
    project_path = None
    testing_context = {}
    test_structure = {}
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            project_path = project.project_path
            # Detect testing context (auth, ORM, mocks, ESM warnings)
            testing_context = detect_testing_context(project_path)
            # Detect test folder structure
            test_structure = _detect_test_structure(project_path)
            logger.info(f"[plan_tests] Testing context: auth={testing_context.get('auth_library')}, orm={testing_context.get('orm')}")
            logger.info(f"[plan_tests] Test structure: integration={test_structure.get('integration_folder')}, e2e={test_structure.get('e2e_folder')}")
    
    # These are no longer pre-populated, but kept for compatibility
    related_code = state.get("related_code", {})
    project_context = state.get("project_context", "")
    
    if not stories:
        logger.info("[plan_tests] No stories to plan")
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "message": "Không có stories để tạo test plan.",
        }
    
    # Format stories for prompt
    stories_text = json.dumps(stories, indent=2, ensure_ascii=False)
    
    # Format related code
    related_code_text = ""
    if related_code:
        for story_id, code in related_code.items():
            story = next((s for s in stories if s.get("id") == story_id), None)
            if story:
                related_code_text += f"\n### Code for '{story.get('title', 'Unknown')}':\n{code}\n"
    else:
        related_code_text = "No related code found."
    
    try:
        # Call LLM to create test plan
        response = await _llm.ainvoke(
            [
                SystemMessage(content=get_system_prompt("plan_tests")),
                HumanMessage(content=get_user_prompt(
                    "plan_tests",
                    stories=stories_text,
                    related_code=related_code_text[:4000],
                    project_context=project_context[:2000] if project_context else "N/A",
                    test_structure=json.dumps(test_structure, indent=2),
                )),
            ],
            config=_cfg(state, "plan_tests"),
        )
        
        result = _parse_json(response.content)
        test_plan = result.get("test_plan", [])
        
        # Ensure each step has required fields
        for i, step in enumerate(test_plan):
            step["order"] = step.get("order", i + 1)
            step["type"] = step.get("type", "integration")
            
            # Generate file path if not provided
            if not step.get("file_path"):
                story_title = step.get("story_title", "unknown")
                slug = _slugify(story_title)
                if step["type"] == "e2e":
                    step["file_path"] = f"e2e/{slug}.spec.ts"
                else:
                    step["file_path"] = f"tests/integration/story-{slug}.test.ts"
        
        total_steps = len(test_plan)
        
        # Build message
        msg = f"📋 **Test Plan** ({total_steps} bước)\n"
        for step in test_plan:
            test_type = "🔧 Integration" if step["type"] == "integration" else "🌐 E2E"
            msg += f"\n{step['order']}. {test_type}: {step.get('description', 'N/A')}"
            msg += f"\n   📁 {step.get('file_path', 'N/A')}"
        
        logger.info(f"[plan_tests] Created plan with {total_steps} steps")
        
        # Notify user if agent available
        if agent:
            await agent.message_user("response", msg)
        
        return {
            "test_plan": test_plan,
            "testing_context": testing_context,
            "total_steps": total_steps,
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT" if total_steps > 0 else "RESPOND",
        }
        
    except Exception as e:
        logger.error(f"[plan_tests] Error: {e}", exc_info=True)
        error_msg = f"Lỗi khi tạo test plan: {str(e)}"
        if agent:
            await agent.message_user("response", error_msg)
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "error": str(e),
            "message": error_msg,
        }
