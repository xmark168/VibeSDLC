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
    # Only message when handling user message, otherwise work silently
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
    # Auto-triggered → always generate tests
    if state.get("is_auto"):
        return {"action": "GENERATE_TESTS"}
    
    user_message = state.get("user_message", "")
    
    # Empty message with story_ids → generate tests
    if not user_message and state.get("story_ids"):
        return {"action": "GENERATE_TESTS"}
    
    # Use LLM to decide
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
    """Query stories with REVIEW status and set agent_state to processing."""
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
        
        # Update agent_state to "processing" for each story
        if agent and stories_data:
            for story in stories_data:
                try:
                    await agent.update_story_agent_state(
                        story_id=UUID(story["id"]),
                        new_state="processing",
                        progress_message="Đang phân tích và tạo test cases..."
                    )
                except Exception as e:
                    logger.warning(f"[query_stories] Failed to update agent state: {e}")
        
        return {"stories": stories_data}
    except Exception as e:
        logger.error(f"[query_stories] {e}")
        return {"stories": [], "error": str(e)}


async def analyze_stories(state: TesterState) -> dict:
    """Analyze stories → test scenarios."""
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
    """Convert scenarios → test cases."""
    scenarios = state.get("test_scenarios", [])
    if not scenarios:
        return {"test_cases": []}
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("generate_test_cases")),
            HumanMessage(content=get_user_prompt("generate_test_cases", scenarios=json.dumps(scenarios, indent=2)))
        ], config=_cfg(state, "generate_test_cases"))
        
        return {"test_cases": _parse_json(response.content)}
    except Exception as e:
        logger.error(f"[generate_test_cases] {e}")
        return {"test_cases": [], "error": str(e)}


async def generate_test_file(state: TesterState) -> dict:
    """Generate TypeScript test file."""
    test_cases = state.get("test_cases", [])
    project_path = state.get("project_path", "")
    timestamp = state.get("timestamp", "")
    stories = state.get("stories", [])
    
    if not test_cases or not project_path:
        return {"result": {"test_count": 0, "error": "No test cases or project path"}}
    
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
        return {"result": {
            "filename": "integration.test.ts",
            "test_count": 0,
            "skipped_duplicates": skipped,
            "stories_covered": [s["id"] for s in stories]
        }}
    
    # Generate code
    task = "generate_test_file_append" if existing_content else "generate_test_file_new"
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt(task)),
            HumanMessage(content=get_user_prompt(
                task,
                test_cases=json.dumps(new_cases, indent=2),
                existing_titles=str(list(existing_titles)[:20]) if existing_content else ""
            ))
        ], config=_cfg(state, "generate_test_file"))
        
        new_content = _strip_markdown(response.content)
        
        # Write file
        if existing_content:
            pos = existing_content.rfind("});")
            if pos > 0:
                final = existing_content[:pos] + f"\n\n  // === Added {timestamp} ===\n" + new_content + "\n" + existing_content[pos:]
            else:
                final = existing_content + "\n\n" + new_content
            existing_file.write_text(final, encoding='utf-8')
        else:
            existing_file.write_text(new_content, encoding='utf-8')
        
        return {"result": {
            "filename": "integration.test.ts",
            "test_count": len(new_cases),
            "skipped_duplicates": skipped,
            "stories_covered": [s["id"] for s in stories]
        }}
    except Exception as e:
        logger.error(f"[generate_test_file] {e}")
        return {"result": {"error": str(e)}}


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
# SEND RESPONSE (for generate tests flow)
# ============================================================================

async def send_response(state: TesterState, agent=None) -> dict:
    """Send response for generate tests flow."""
    result = state.get("result", {})
    stories = state.get("stories", [])
    error = state.get("error") or result.get("error")
    
    # Build message
    if error:
        msg = f"Có lỗi xảy ra: {error}"
    else:
        test_count = result.get("test_count", 0)
        skipped = result.get("skipped_duplicates", 0)
        filename = result.get("filename", "integration.test.ts")
        
        if test_count == 0 and skipped > 0:
            msg = f"Tests đã có sẵn trong `{filename}`, không cần tạo thêm!"
        elif skipped > 0:
            msg = f"Đã thêm {test_count} tests vào `{filename}` (bỏ qua {skipped} đã có)."
        elif test_count > 0:
            msg = f"Đã tạo {test_count} tests trong `{filename}`."
        else:
            msg = "Không có stories nào trong trạng thái Review để tạo test."
    
    # Send message to story channels (always, for tracking)
    if agent and stories and result.get("test_count", 0) > 0:
        for story in stories:
            try:
                await agent.message_story(
                    story_id=UUID(story["id"]),
                    content=f"✅ Đã tạo {result['test_count']} integration tests",
                    message_type="test_result",
                    details=result,
                )
            except Exception as e:
                logger.warning(f"[send_response] Failed to message story {story['id']}: {e}")
    
    # Only message_user if user-initiated
    if agent and _should_message_user(state):
        await agent.message_user("response", msg)
    
    return {"message": msg}
