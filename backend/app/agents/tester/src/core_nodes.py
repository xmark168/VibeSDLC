"""Node functions for Tester graph (Simplified)."""

import json
import logging
import os
from pathlib import Path
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session, select

from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.state import TesterState
from app.agents.tester.src._llm import get_llm, default_llm
from app.core.db import engine
from app.models import Project, Story, StoryStatus

logger = logging.getLogger(__name__)


# ============================================================================
# TESTING CONTEXT DETECTION
# ============================================================================


def detect_testing_context(project_path: str) -> dict:
    """Detect testing setup and patterns from the project.

    Returns context about:
    - Auth library (NextAuth, Clerk, custom)
    - Existing mocks in jest.setup.ts
    - ORM (Prisma, Drizzle, etc.)
    - ESM packages to avoid
    """
    workspace = Path(project_path)
    context = {
        "auth_library": None,
        "auth_pattern": "",
        "orm": None,
        "existing_mocks": [],
        "esm_warning": "",
        "prisma_mock_pattern": "",
        "import_alias": "@/",
    }

    if not workspace.exists():
        return context

    # 1. Detect from package.json
    package_json = workspace / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

            # Auth detection
            if "next-auth" in deps:
                context["auth_library"] = "nextauth"
                context["auth_pattern"] = """
NEXTAUTH TESTING PATTERN:
- DO NOT import from /api/auth/callback/* routes (NextAuth handles internally)
- Test the authorize() logic directly by replicating it in test file
- Mock Prisma's user.findUnique for auth tests
- Use bcryptjs for password hashing (already installed)

Example authorize test:
```typescript
async function authorize(credentials) {
  if (!credentials?.username || !credentials?.password) return null;
  const user = await mockFindUnique({ where: { username: credentials.username } });
  if (!user) return null;
  const isValid = await bcrypt.compare(credentials.password, user.password);
  return isValid ? { id: user.id, username: user.username, email: user.email } : null;
}
```"""
            elif "clerk" in deps or "@clerk/nextjs" in deps:
                context["auth_library"] = "clerk"
                context["auth_pattern"] = "Clerk auth - mock @clerk/nextjs hooks"

            # ORM detection
            if "@prisma/client" in deps or "prisma" in deps:
                context["orm"] = "prisma"
                context["prisma_mock_pattern"] = """
PRISMA MOCK PATTERN (use this exact pattern):
```typescript
const mockFindUnique = jest.fn();
const mockCreate = jest.fn();
const mockFindMany = jest.fn();
const mockDelete = jest.fn();

jest.mock("@/lib/prisma", () => ({
  prisma: {
    user: {
      findUnique: (...args: unknown[]) => mockFindUnique(...args),
      create: (...args: unknown[]) => mockCreate(...args),
      findMany: (...args: unknown[]) => mockFindMany(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
    },
    // Add other models as needed
  },
}));
```"""
            elif "drizzle-orm" in deps:
                context["orm"] = "drizzle"

        except Exception as e:
            logger.warning(f"[detect_testing_context] Failed to parse package.json: {e}")

    # 2. Read jest.setup.ts for existing mocks
    jest_setup = workspace / "jest.setup.ts"
    if not jest_setup.exists():
        jest_setup = workspace / "jest.setup.js"

    if jest_setup.exists():
        try:
            setup_content = jest_setup.read_text(encoding="utf-8")

            # Detect mocked modules
            mock_patterns = [
                ("next/navigation", "useRouter, usePathname, useSearchParams"),
                ("next/router", "useRouter"),
                ("matchMedia", "window.matchMedia"),
                ("IntersectionObserver", "IntersectionObserver"),
                ("ResizeObserver", "ResizeObserver"),
            ]

            for module, description in mock_patterns:
                if module in setup_content:
                    context["existing_mocks"].append(f"{module} ({description})")

        except Exception as e:
            logger.warning(f"[detect_testing_context] Failed to read jest.setup: {e}")

    # 3. ESM warning (packages that break Jest)
    context["esm_warning"] = """
ESM PACKAGES TO AVOID (break Jest):
- uuid → Use hardcoded strings: "test-id-123" or `test-${Date.now()}`
- nanoid → Use hardcoded strings
- node-fetch → Use native fetch
- chalk → Don't use in tests

SAFE PACKAGES:
- bcryptjs ✅
- date-fns ✅ (but mock if needed)
- zod ✅
"""

    return context


# ============================================================================
# HELPERS
# ============================================================================


_llm = default_llm
_chat_llm = get_llm("default")  # Will use same model with default temp


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> list | dict:
    """Parse JSON from LLM response with better error handling."""
    original = content
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass

    # Extract from markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[_parse_json] Failed to parse: {original[:500]}...")
        raise e


def _should_message_user(state: TesterState) -> bool:
    """Check if should send message to user - only for user messages."""
    return state.get("task_type") == "message"


async def send_message(state: TesterState, agent, content: str, message_type: str = "update"):
    """Send message to appropriate channel based on context.
    
    - Auto-run (is_auto=True): Send to story channel (visible in story detail)
    - User chat (is_auto=False): Send to main chat (visible in project chat)
    
    Args:
        state: Current state with is_auto and story_ids
        agent: Agent instance with message_user() and message_story() methods
        content: Message content
        message_type: Type for story messages ("update", "test_result", "progress", "error")
    """
    if not agent:
        logger.warning("[send_message] No agent provided, skipping message")
        return
    
    is_auto = state.get("is_auto", False)
    story_ids = state.get("story_ids", [])
    
    logger.debug(f"[send_message] is_auto={is_auto}, story_ids={story_ids}, content={content[:50]}...")
    
    if is_auto and story_ids:
        # Auto-run: message to story channel (not main chat)
        for story_id in story_ids:
            try:
                logger.info(f"[send_message] Sending to story {story_id}: {content[:50]}...")
                await agent.message_story(UUID(story_id), content, message_type)
                logger.info(f"[send_message] Successfully sent to story {story_id}")
            except Exception as e:
                logger.error(f"[send_message] Failed to message story {story_id}: {e}", exc_info=True)
    elif not is_auto:
        # User chat (@mention or direct): message to user
        await agent.message_user("response", content)
    else:
        logger.warning(f"[send_message] is_auto={is_auto} but no story_ids, message dropped: {content[:50]}...")


# ============================================================================
# ROUTER (Entry Point)
# ============================================================================


async def _query_stories_from_db(project_id: str, story_ids: list, agent) -> list:
    """Query stories in REVIEW status from database."""
    from sqlalchemy import or_

    logger.info(f"[_query_stories_from_db] project_id={project_id}, story_ids={story_ids}")

    try:
        with Session(engine) as session:
            query = select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW,
                or_(
                    Story.agent_state.is_(None),
                    Story.agent_state.in_(["pending", "canceled"]),
                ),
            )
            if story_ids:
                query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))

            stories = session.exec(query).all()
            logger.info(f"[_query_stories_from_db] Found {len(stories)} stories from query")

            if not stories:
                logger.info("[_query_stories_from_db] No stories to process")
                return []

            stories_data = [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "description": s.description,
                    "acceptance_criteria": s.acceptance_criteria,
                }
                for s in stories
            ]

            logger.info(f"[_query_stories_from_db] Found {len(stories_data)} stories")

        # Update agent_state to "processing"
        if agent and stories_data:
            for story in stories_data:
                try:
                    await agent.update_story_agent_state(
                        story_id=UUID(story["id"]),
                        new_state="processing",
                        progress_message="Đang phân tích và tạo test cases...",
                    )
                except Exception as e:
                    logger.warning(f"[_query_stories_from_db] Failed to update state: {e}")

        return stories_data

    except Exception as e:
        logger.error(f"[_query_stories_from_db] Error: {e}")
        return []


async def router(state: TesterState, agent=None) -> dict:
    """Route + query stories + get tech_stack.

    This is the entry point node that:
    1. Gets tech_stack from project
    2. Queries stories from DB when auto-triggered
    3. Routes to appropriate action
    """
    project_id = state.get("project_id")
    story_ids = state.get("story_ids", [])
    is_auto = state.get("is_auto", False)
    existing_stories = state.get("stories", [])
    
    logger.info(f"[router] project_id={project_id}, is_auto={is_auto}, story_ids={story_ids}, existing_stories={len(existing_stories)}")

    # 1. Get tech_stack from project (or use from state for local testing)
    tech_stack = state.get("tech_stack", "nextjs")
    try:
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            if project:
                tech_stack = project.tech_stack or tech_stack
    except Exception as e:
        logger.warning(f"[router] Could not query project: {e}")

    # 2. Auto-trigger or story_ids present: query stories and go to PLAN_TESTS
    if state.get("is_auto") or story_ids:
        # Use stories from state if already provided (for local testing)
        stories = state.get("stories", [])
        if not stories:
            stories = await _query_stories_from_db(project_id, story_ids, agent)
        if stories:
            return {
                "action": "PLAN_TESTS",
                "stories": stories,
                "tech_stack": tech_stack,
            }
        # No stories to process
        return {
            "action": "CONVERSATION",
            "tech_stack": tech_stack,
            "message": "Không có stories nào trong REVIEW cần tạo tests.",
        }

    # 3. User message: route via LLM
    user_message = state.get("user_message", "")
    try:
        response = await _llm.ainvoke(
            [
                SystemMessage(content=get_system_prompt("routing")),
                HumanMessage(
                    content=get_user_prompt("routing", user_message=user_message)
                ),
            ],
            config=_cfg(state, "router"),
        )

        result = _parse_json(response.content)
        action = result.get("action", "CONVERSATION")
        logger.info(f"[router] Action={action}, reason={result.get('reason')}")

        # If PLAN_TESTS from user message, also query stories
        if action == "PLAN_TESTS":
            stories = await _query_stories_from_db(project_id, story_ids, agent)
            return {
                "action": action,
                "stories": stories,
                "tech_stack": tech_stack,
            }

        return {"action": action, "tech_stack": tech_stack}
    except Exception as e:
        logger.error(f"[router] {e}")
        return {"action": "CONVERSATION", "tech_stack": tech_stack}


# ============================================================================
# TOOL-BASED NODES
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
            config=_cfg(state, "test_status"),
        )

        msg = result["messages"][-1].content

        await send_message(state, agent, msg)

        return {"message": msg, "result": {"action": "test_status"}}
    except Exception as e:
        logger.error(f"[test_status] {e}")
        msg = f"Lỗi khi kiểm tra test status: {e}"
        await send_message(state, agent, msg, "error")
        return {"message": msg, "error": str(e)}


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
            config=_cfg(state, "conversation"),
        )

        msg = result["messages"][-1].content

        await send_message(state, agent, msg)

        return {"message": msg, "result": {"action": "conversation"}}
    except Exception as e:
        logger.error(f"[conversation] {e}")
        msg = f"Xin lỗi, có lỗi xảy ra: {e}"
        await send_message(state, agent, msg, "error")
        return {"message": msg, "error": str(e)}


# ============================================================================
# SEND RESPONSE
# ============================================================================


async def send_response(state: TesterState, agent=None) -> dict:
    """Send final response after test generation flow."""
    stories = state.get("stories", [])
    error = state.get("error")
    test_plan = state.get("test_plan", [])
    run_status = state.get("run_status", "")
    run_result = state.get("run_result", {})
    files_created = state.get("files_created", [])
    workspace_path = state.get("workspace_path", "")
    branch_name = state.get("branch_name", "")
    workspace_ready = state.get("workspace_ready", False)

    # Commit changes if workspace is ready and tests passed
    commit_msg = ""
    if workspace_ready and workspace_path and files_created:
        try:
            from app.agents.tester.src.tools.workspace_tools import commit_workspace_changes
            
            story_titles = ", ".join(s.get("title", "")[:30] for s in stories[:2]) if stories else "tests"
            commit_result = commit_workspace_changes(
                workspace_path=workspace_path,
                title=story_titles,
                branch_name=branch_name or "test",
                agent_name="tester",
            )
            if commit_result.get("success"):
                commit_msg = f"\n\n📝 {commit_result.get('message', 'Changes committed')}"
                logger.info(f"[send_response] Committed changes: {commit_result}")
        except Exception as e:
            logger.warning(f"[send_response] Failed to commit: {e}")

    # Build message
    if error:
        msg = f"❌ Có lỗi xảy ra: {error}"
    elif run_status == "PASS":
        passed = run_result.get("passed", 0)
        msg = f"✅ Tests passed! ({passed} tests passed)"
        if files_created:
            msg += f"\n\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
        msg += commit_msg
    elif run_status == "FAIL":
        passed = run_result.get("passed", 0)
        failed = run_result.get("failed", 0)
        msg = f"❌ Tests failed! ({passed} passed, {failed} failed)"
        if files_created:
            msg += f"\n\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
    elif not test_plan:
        msg = "Không có tests được tạo."
    else:
        msg = f"✅ Đã tạo test plan với {len(test_plan)} steps."
        if files_created:
            msg += f"\n\nFiles created:\n" + "\n".join(f"  - {f}" for f in files_created)
        msg += commit_msg

    # Update story states
    if agent and stories:
        for story in stories:
            story_id = story["id"]
            try:
                await agent.update_story_agent_state(
                    story_id=UUID(story_id),
                    new_state="finished",
                    progress_message=msg[:200],
                )
            except Exception as e:
                logger.warning(f"[send_response] Failed to update story {story_id}: {e}")

    # Message to appropriate channel
    await send_message(state, agent, msg, "test_result")

    return {"message": msg, "merged": bool(commit_msg)}
