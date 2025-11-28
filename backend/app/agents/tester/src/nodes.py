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
from app.models import Story, StoryStatus, Project
from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_chat_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> list | dict:
    """Parse JSON from LLM response."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    return json.loads(content.strip())


def _strip_markdown(content: str) -> str:
    """Remove markdown code blocks."""
    for prefix in ["```typescript", "```ts", "```"]:
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def _should_message_user(state: TesterState) -> bool:
    """Check if should send message to user - only for user messages."""
    return state.get("task_type") == "message"


# ============================================================================
# SETUP & ROUTING
# ============================================================================

async def setup_context(state: TesterState, agent=None) -> dict:
    """Setup project context."""
    project_id = state.get("project_id")
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project:
            return {
                "project_path": project.project_path or "",
                "tech_stack": project.tech_stack or "nodejs-react",
                "timestamp": datetime.now().strftime("%Y-%m-%d-%H%M%S"),
            }
    return {"error": "Project not found"}


async def router(state: TesterState, agent=None) -> dict:
    """Route to appropriate action based on context."""
    if state.get("is_auto"):
        return {"action": "GENERATE_TESTS"}
    
    user_message = state.get("user_message", "")
    if not user_message and state.get("story_ids"):
        return {"action": "GENERATE_TESTS"}
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("routing")),
            HumanMessage(content=get_user_prompt("routing", user_message=user_message))
        ], config=_cfg(state, "router"))
        
        result = _parse_json(response.content)
        action = result.get("action", "CONVERSATION")
        logger.info(f"[router] Action={action}, reason={result.get('reason')}")
        return {"action": action}
    except Exception as e:
        logger.error(f"[router] {e}")
        return {"action": "CONVERSATION"}


# ============================================================================
# GENERATE TESTS FLOW
# ============================================================================

async def query_stories(state: TesterState, agent=None) -> dict:
    """Query stories with REVIEW status."""
    project_id = state.get("project_id")
    story_ids = state.get("story_ids", [])
    
    try:
        with Session(engine) as session:
            query = select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW
            )
            if story_ids:
                query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
            
            stories = session.exec(query).all()
            stories_data = [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "description": s.description,
                    "acceptance_criteria": s.acceptance_criteria,
                }
                for s in stories
            ]
        
        # Update agent_state to "processing"
        if agent and stories_data:
            for story in stories_data:
                try:
                    await agent.update_story_agent_state(
                        story_id=UUID(story["id"]),
                        new_state="processing",
                        progress_message="Đang phân tích và tạo test cases..."
                    )
                except Exception as e:
                    logger.warning(f"[query_stories] Failed to update state: {e}")
        
        return {"stories": stories_data}
    except Exception as e:
        logger.error(f"[query_stories] {e}")
        return {"stories": [], "error": str(e)}


async def analyze_stories(state: TesterState) -> dict:
    """Analyze stories → test scenarios for both integration and unit tests."""
    stories = state.get("stories", [])
    if not stories:
        return {"test_scenarios": []}
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("analyze_stories")),
            HumanMessage(content=get_user_prompt("analyze_stories", stories=json.dumps(stories, indent=2)))
        ], config=_cfg(state, "analyze_stories"))
        
        return {"test_scenarios": _parse_json(response.content)}
    except Exception as e:
        logger.error(f"[analyze_stories] {e}")
        return {"test_scenarios": [], "error": str(e)}


async def generate_test_cases(state: TesterState) -> dict:
    """Convert scenarios → test cases (both integration and unit)."""
    scenarios = state.get("test_scenarios", [])
    if not scenarios:
        return {"test_cases": {"integration_tests": [], "unit_tests": []}}
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("generate_test_cases")),
            HumanMessage(content=get_user_prompt("generate_test_cases", scenarios=json.dumps(scenarios, indent=2)))
        ], config=_cfg(state, "generate_test_cases"))
        
        test_cases = _parse_json(response.content)
        # Ensure structure
        if isinstance(test_cases, list):
            test_cases = {"integration_tests": test_cases, "unit_tests": []}
        
        return {"test_cases": test_cases}
    except Exception as e:
        logger.error(f"[generate_test_cases] {e}")
        return {"test_cases": {"integration_tests": [], "unit_tests": []}, "error": str(e)}


async def generate_integration_tests(state: TesterState) -> dict:
    """Generate integration test file."""
    test_cases = state.get("test_cases", {}).get("integration_tests", [])
    project_path = state.get("project_path", "")
    timestamp = state.get("timestamp", "")
    stories = state.get("stories", [])
    
    if not test_cases or not project_path:
        return {"result": {"integration": {"test_count": 0}}}
    
    tests_dir = Path(project_path) / "tests" / "integration"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # Check existing file
    existing_file = tests_dir / "integration.test.ts"
    existing_titles = set()
    existing_content = ""
    
    if existing_file.exists():
        existing_content = existing_file.read_text(encoding='utf-8')
        existing_titles = set(re.findall(r"(?:test|it)\s*\(['\"]([^'\"]+)['\"]", existing_content))
    
    # Filter duplicates
    new_cases = [tc for tc in test_cases if tc.get("title", "").lower() not in {t.lower() for t in existing_titles}]
    skipped = len(test_cases) - len(new_cases)
    
    if not new_cases:
        return {"result": {"integration": {
            "filename": "tests/integration/integration.test.ts",
            "test_count": 0,
            "skipped_duplicates": skipped,
        }}}
    
    # Generate code
    task = "generate_integration_test_append" if existing_content else "generate_integration_test_new"
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt(task)),
            HumanMessage(content=get_user_prompt(
                task,
                test_cases=json.dumps(new_cases, indent=2),
                existing_titles=str(list(existing_titles)[:20]) if existing_content else ""
            ))
        ], config=_cfg(state, "generate_integration_tests"))
        
        new_content = _strip_markdown(response.content)
        
        # Write file
        if existing_content:
            pos = existing_content.rfind("});")
            if pos > 0:
                final = existing_content[:pos] + f"\n\n  // === Integration Tests Added {timestamp} ===\n" + new_content + "\n" + existing_content[pos:]
            else:
                final = existing_content + "\n\n" + new_content
            existing_file.write_text(final, encoding='utf-8')
        else:
            existing_file.write_text(new_content, encoding='utf-8')
        
        logger.info(f"[generate_integration_tests] Created {len(new_cases)} tests")
        return {"result": {"integration": {
            "filename": "tests/integration/integration.test.ts",
            "test_count": len(new_cases),
            "skipped_duplicates": skipped,
            "stories_covered": [s["id"] for s in stories]
        }}}
    except Exception as e:
        logger.error(f"[generate_integration_tests] {e}")
        return {"result": {"integration": {"error": str(e)}}}


async def generate_unit_tests(state: TesterState) -> dict:
    """Generate unit test files grouped by target file."""
    test_cases = state.get("test_cases", {}).get("unit_tests", [])
    project_path = state.get("project_path", "")
    timestamp = state.get("timestamp", "")
    current_result = state.get("result", {})
    
    if not test_cases or not project_path:
        return {"result": {**current_result, "unit": {"test_count": 0}}}
    
    tests_dir = Path(project_path) / "tests" / "unit"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # Group test cases by target file
    grouped = {}
    for tc in test_cases:
        target = tc.get("target_file", "misc")
        if target not in grouped:
            grouped[target] = []
        grouped[target].append(tc)
    
    total_created = 0
    total_skipped = 0
    files_created = []
    
    for target_file, cases in grouped.items():
        # Create test file name from target
        test_filename = target_file.replace("/", "_").replace(".ts", ".test.ts").replace(".js", ".test.js")
        if not test_filename.endswith(".test.ts"):
            test_filename += ".test.ts"
        
        existing_file = tests_dir / test_filename
        existing_titles = set()
        existing_content = ""
        
        if existing_file.exists():
            existing_content = existing_file.read_text(encoding='utf-8')
            existing_titles = set(re.findall(r"(?:test|it)\s*\(['\"]([^'\"]+)['\"]", existing_content))
        
        # Filter duplicates
        new_cases = [tc for tc in cases if tc.get("title", "").lower() not in {t.lower() for t in existing_titles}]
        total_skipped += len(cases) - len(new_cases)
        
        if not new_cases:
            continue
        
        # Generate code
        task = "generate_unit_test_append" if existing_content else "generate_unit_test_new"
        try:
            response = await _llm.ainvoke([
                SystemMessage(content=get_system_prompt(task)),
                HumanMessage(content=get_user_prompt(
                    task,
                    test_cases=json.dumps(new_cases, indent=2),
                    target_file=target_file,
                    existing_titles=str(list(existing_titles)[:20]) if existing_content else ""
                ))
            ], config=_cfg(state, f"generate_unit_tests_{target_file}"))
            
            new_content = _strip_markdown(response.content)
            
            # Write file
            if existing_content:
                pos = existing_content.rfind("});")
                if pos > 0:
                    final = existing_content[:pos] + f"\n\n  // === Unit Tests Added {timestamp} ===\n" + new_content + "\n" + existing_content[pos:]
                else:
                    final = existing_content + "\n\n" + new_content
                existing_file.write_text(final, encoding='utf-8')
            else:
                existing_file.write_text(new_content, encoding='utf-8')
            
            total_created += len(new_cases)
            files_created.append(f"tests/unit/{test_filename}")
            
        except Exception as e:
            logger.error(f"[generate_unit_tests] Error for {target_file}: {e}")
    
    logger.info(f"[generate_unit_tests] Created {total_created} tests in {len(files_created)} files")
    return {"result": {**current_result, "unit": {
        "filenames": files_created,
        "test_count": total_created,
        "skipped_duplicates": total_skipped,
    }}}


# ============================================================================
# EXECUTE AND VERIFY (React Agent)
# ============================================================================

EXECUTE_SYSTEM_PROMPT = """You are a QA agent that executes tests and handles failures intelligently.

Your task:
1. Run integration tests first, then unit tests
2. Analyze the results for each suite
3. If ALL tests pass → Report success
4. If tests FAIL:
   - Create a bug story using create_bug_story tool
   - Include failing test names and error messages
   - Specify which suite (integration/unit) failed

Always respond in Vietnamese with a summary of both test suites."""


async def execute_and_verify(state: TesterState, agent=None) -> dict:
    """Execute tests and handle results using React Agent."""
    from langgraph.prebuilt import create_react_agent
    from app.agents.tester.src.tools import get_execution_tools
    
    result = state.get("result", {})
    stories = state.get("stories", [])
    project_id = state.get("project_id", "")
    
    int_count = result.get("integration", {}).get("test_count", 0)
    unit_count = result.get("unit", {}).get("test_count", 0)
    
    # Skip if no tests were generated
    if int_count == 0 and unit_count == 0:
        return {"test_execution": {"skipped": True, "reason": "No new tests generated"}}
    
    try:
        tools = get_execution_tools()
        react_agent = create_react_agent(_llm, tools)
        
        # Build context
        int_file = result.get("integration", {}).get("filename", "")
        unit_files = result.get("unit", {}).get("filenames", [])
        story_context = "\n".join([f"- {s['title']} (ID: {s['id']})" for s in stories])
        first_story_id = stories[0]["id"] if stories else ""
        
        user_message = f"""Chạy tests và xử lý kết quả.

Project ID: {project_id}

**Integration Tests:** {int_count} tests
- File: {int_file}

**Unit Tests:** {unit_count} tests
- Files: {', '.join(unit_files) if unit_files else 'None'}

Stories được test:
{story_context}

Hãy:
1. Chạy integration tests với run_tests(project_id="{project_id}", test_type="integration", test_file="{int_file}") nếu có
2. Chạy unit tests với run_tests(project_id="{project_id}", test_type="unit") nếu có
3. Nếu có test fail → tạo bug story với create_bug_story, parent_story_id="{first_story_id}"
4. Báo cáo tổng hợp kết quả"""

        agent_result = await react_agent.ainvoke(
            {"messages": [("system", EXECUTE_SYSTEM_PROMPT), ("user", user_message)]},
            config=_cfg(state, "execute_and_verify")
        )
        
        final_message = agent_result["messages"][-1].content
        
        # Update story agent state
        if agent and stories:
            for story in stories:
                try:
                    tests_passed = "pass" in final_message.lower() or "thành công" in final_message.lower()
                    await agent.update_story_agent_state(
                        story_id=UUID(story["id"]),
                        new_state="finished" if tests_passed else "processing",
                        progress_message=final_message[:200]
                    )
                except Exception as e:
                    logger.warning(f"[execute_and_verify] Failed to update state: {e}")
        
        return {"test_execution": {"completed": True, "message": final_message}}
        
    except Exception as e:
        logger.error(f"[execute_and_verify] Error: {e}")
        return {"test_execution": {"completed": False, "error": str(e)}}


# ============================================================================
# TEST STATUS (with tools)
# ============================================================================

async def test_status(state: TesterState, agent=None) -> dict:
    """Report test status using tools."""
    try:
        from langgraph.prebuilt import create_react_agent
        from app.agents.tester.src.tools import get_tester_tools
        
        tools = get_tester_tools()
        react_agent = create_react_agent(_chat_llm, tools)
        
        system_msg = get_system_prompt("conversation")
        user_msg = f"{state.get('user_message', 'test status')}\n\nproject_id: {state.get('project_id', '')}"
        
        result = await react_agent.ainvoke(
            {"messages": [("system", system_msg), ("user", user_msg)]},
            config=_cfg(state, "test_status")
        )
        
        msg = result["messages"][-1].content
        
        if agent and _should_message_user(state):
            await agent.message_user("response", msg)
        
        return {"message": msg, "result": {"action": "test_status"}}
    except Exception as e:
        logger.error(f"[test_status] {e}")
        msg = f"Lỗi khi kiểm tra test status: {e}"
        if agent and _should_message_user(state):
            await agent.message_user("response", msg)
        return {"message": msg, "error": str(e)}


# ============================================================================
# CONVERSATION (with tools)
# ============================================================================

async def conversation(state: TesterState, agent=None) -> dict:
    """Handle conversation about testing using tools."""
    try:
        from langgraph.prebuilt import create_react_agent
        from app.agents.tester.src.tools import get_tester_tools
        
        tools = get_tester_tools()
        react_agent = create_react_agent(_chat_llm, tools)
        
        system_msg = get_system_prompt("conversation")
        user_msg = f"{state.get('user_message', '')}\n\nproject_id: {state.get('project_id', '')}"
        
        result = await react_agent.ainvoke(
            {"messages": [("system", system_msg), ("user", user_msg)]},
            config=_cfg(state, "conversation")
        )
        
        msg = result["messages"][-1].content
        
        if agent and _should_message_user(state):
            await agent.message_user("response", msg)
        
        return {"message": msg, "result": {"action": "conversation"}}
    except Exception as e:
        logger.error(f"[conversation] {e}")
        msg = f"Xin lỗi, có lỗi xảy ra: {e}"
        if agent and _should_message_user(state):
            await agent.message_user("response", msg)
        return {"message": msg, "error": str(e)}


# ============================================================================
# SEND RESPONSE
# ============================================================================

async def send_response(state: TesterState, agent=None) -> dict:
    """Send response for generate tests flow."""
    result = state.get("result", {})
    test_execution = state.get("test_execution", {})
    stories = state.get("stories", [])
    error = state.get("error")
    
    int_result = result.get("integration", {})
    unit_result = result.get("unit", {})
    
    # Build message
    if error:
        msg = f"Có lỗi xảy ra: {error}"
    else:
        int_count = int_result.get("test_count", 0)
        unit_count = unit_result.get("test_count", 0)
        total = int_count + unit_count
        
        if total == 0:
            msg = "Không có tests mới được tạo (có thể đã tồn tại hoặc không có stories trong Review)."
        else:
            parts = []
            if int_count > 0:
                parts.append(f"{int_count} integration tests")
            if unit_count > 0:
                parts.append(f"{unit_count} unit tests")
            msg = f"✅ Đã tạo {' và '.join(parts)}."
        
        # Append test execution results
        if test_execution.get("completed"):
            exec_msg = test_execution.get("message", "")
            if exec_msg:
                msg += f"\n\n**Kết quả chạy tests:**\n{exec_msg[:500]}"
    
    # Update story states and send messages
    if agent and stories:
        for story in stories:
            story_id = UUID(story["id"])
            try:
                await agent.update_story_agent_state(
                    story_id=story_id,
                    new_state="finished",
                    progress_message=msg[:200]
                )
                
                total = int_result.get("test_count", 0) + unit_result.get("test_count", 0)
                if total > 0:
                    await agent.message_story(
                        story_id=story_id,
                        content=f"✅ Đã tạo {total} tests (IT: {int_result.get('test_count', 0)}, UT: {unit_result.get('test_count', 0)})",
                        message_type="test_result",
                        details=result,
                    )
            except Exception as e:
                logger.warning(f"[send_response] Failed to update story {story['id']}: {e}")
    
    # Message user if user-initiated
    if agent and _should_message_user(state):
        await agent.message_user("response", msg)
    
    return {"message": msg}
