"""Node functions for Tester graph."""

import asyncio
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

# CocoIndex imports
from app.agents.developer_v2.src.tools.cocoindex_tools import (
    search_codebase_async,
    index_workspace,
    get_project_context,
    get_boilerplate_examples,
    detect_project_structure,
)

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
            data = json.loads(package_json.read_text(encoding='utf-8'))
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
            setup_content = jest_setup.read_text(encoding='utf-8')
            
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

_llm = ChatOpenAI(model="gpt-4.1", temperature=0)
_chat_llm = ChatOpenAI(model="gpt-4.1", temperature=0.7)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> list | dict:
    """Parse JSON from LLM response with better error handling."""
    original = content
    try:
        # Try direct parse first
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
# COCOINDEX - SEARCH RELATED CODE
# ============================================================================

async def search_related_code(state: TesterState, agent=None) -> dict:
    """Search codebase for code related to stories using CocoIndex.
    
    This helps generate more accurate tests by understanding the actual implementation.
    """
    project_id = state.get("project_id")
    project_path = state.get("project_path", "")
    stories = state.get("stories", [])
    
    if not project_path or not stories:
        logger.info("[search_related_code] No project path or stories, skipping CocoIndex search")
        return {"related_code": {}, "project_context": "", "index_ready": False}
    
    # Try to index workspace
    index_ready = False
    try:
        task_id = state.get("task_id")
        index_ready = index_workspace(project_id, project_path, task_id)
        if index_ready:
            logger.info(f"[search_related_code] CocoIndex ready for {project_path}")
        else:
            logger.warning(f"[search_related_code] CocoIndex indexing failed, will skip semantic search")
    except Exception as e:
        logger.warning(f"[search_related_code] CocoIndex not available: {e}")
    
    # Get project context (structure, AGENTS.md, etc.)
    project_context = ""
    try:
        project_context = get_project_context(project_path)
        logger.info(f"[search_related_code] Got project context ({len(project_context)} chars)")
    except Exception as e:
        logger.warning(f"[search_related_code] Failed to get project context: {e}")
    
    # Get test examples from project
    test_examples = ""
    try:
        # Look for existing test patterns
        test_examples = get_boilerplate_examples(project_path, "api")
        if not test_examples:
            test_examples = get_boilerplate_examples(project_path, "page")
        logger.info(f"[search_related_code] Got test examples ({len(test_examples)} chars)")
    except Exception as e:
        logger.warning(f"[search_related_code] Failed to get test examples: {e}")
    
    # Detect testing context (auth, ORM, existing mocks, ESM warnings)
    testing_context = {}
    try:
        testing_context = detect_testing_context(project_path)
        logger.info(f"[search_related_code] Detected testing context: auth={testing_context.get('auth_library')}, orm={testing_context.get('orm')}, mocks={len(testing_context.get('existing_mocks', []))}")
    except Exception as e:
        logger.warning(f"[search_related_code] Failed to detect testing context: {e}")
    
    # Search for code related to each story (parallel)
    related_code = {}
    
    if index_ready:
        async def search_for_story(story: dict) -> tuple[str, str]:
            story_id = story["id"]
            story_title = story.get("title", "")
            story_desc = story.get("description", "")[:300]
            
            # Build search query from story
            query = f"{story_title} {story_desc}"
            
            try:
                task_id = state.get("task_id")
                code = await search_codebase_async(project_id, query, top_k=5, task_id=task_id)
                return story_id, code
            except Exception as e:
                logger.warning(f"[search_related_code] Search failed for story {story_id}: {e}")
                return story_id, ""
        
        # Search all stories in parallel
        tasks = [search_for_story(s) for s in stories]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"[search_related_code] Search task error: {r}")
                continue
            if r:
                story_id, code = r
                if code and code != "No relevant code found." and code != "CocoIndex not available.":
                    related_code[story_id] = code
        
        logger.info(f"[search_related_code] Found related code for {len(related_code)}/{len(stories)} stories")
    
    return {
        "related_code": related_code,
        "project_context": project_context,
        "test_examples": test_examples,
        "testing_context": testing_context,
        "index_ready": index_ready,
    }


# ============================================================================
# GENERATE TESTS FLOW
# ============================================================================

async def query_stories(state: TesterState, agent=None) -> dict:
    """Query stories with REVIEW status that haven't been processed yet."""
    from sqlalchemy import or_
    
    project_id = state.get("project_id")
    story_ids = state.get("story_ids", [])
    
    try:
        with Session(engine) as session:
            # Only query stories that are NOT already processing/finished
            # This prevents duplicate test generation when multiple stories are dragged at once
            query = select(Story).where(
                Story.project_id == UUID(project_id),
                Story.status == StoryStatus.REVIEW,
                or_(
                    Story.agent_state.is_(None),  # Never processed
                    Story.agent_state.in_(["pending", "canceled"])  # Can be reprocessed
                )
            )
            if story_ids:
                query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
            
            stories = session.exec(query).all()
            
            if not stories:
                logger.info(f"[query_stories] No new stories to process (all may be processing/finished)")
                return {"stories": []}
            
            stories_data = [
                {
                    "id": str(s.id),
                    "title": s.title,
                    "description": s.description,
                    "acceptance_criteria": s.acceptance_criteria,
                }
                for s in stories
            ]
            logger.info(f"[query_stories] Found {len(stories_data)} stories to process")
        
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
    """Analyze stories → test scenarios using CocoIndex context."""
    stories = state.get("stories", [])
    if not stories:
        return {"test_scenarios": []}
    
    # Get CocoIndex context
    related_code = state.get("related_code", {})
    project_context = state.get("project_context", "")
    
    # Format related code for prompt
    related_code_text = ""
    if related_code:
        for story_id, code in related_code.items():
            story = next((s for s in stories if s["id"] == story_id), None)
            if story:
                related_code_text += f"\n### Code related to '{story['title']}':\n{code}\n"
    else:
        related_code_text = "No related code found (CocoIndex not available or no matches)"
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("analyze_stories")),
            HumanMessage(content=get_user_prompt(
                "analyze_stories",
                stories=json.dumps(stories, indent=2),
                related_code=related_code_text,
                project_context=project_context[:3000] if project_context else "No project context available"
            ))
        ], config=_cfg(state, "analyze_stories"))
        
        return {"test_scenarios": _parse_json(response.content)}
    except Exception as e:
        logger.error(f"[analyze_stories] {e}")
        return {"test_scenarios": [], "error": str(e)}


async def generate_test_cases(state: TesterState) -> dict:
    """Convert scenarios → integration test cases only."""
    scenarios = state.get("test_scenarios", [])
    if not scenarios:
        return {"test_cases": {"integration_tests": []}}
    
    try:
        response = await _llm.ainvoke([
            SystemMessage(content=get_system_prompt("generate_test_cases")),
            HumanMessage(content=get_user_prompt("generate_test_cases", scenarios=json.dumps(scenarios, indent=2)))
        ], config=_cfg(state, "generate_test_cases"))
        
        test_cases = _parse_json(response.content)
        # Ensure structure - only integration tests
        if isinstance(test_cases, list):
            test_cases = {"integration_tests": test_cases}
        elif isinstance(test_cases, dict):
            test_cases = {"integration_tests": test_cases.get("integration_tests", [])}
        
        return {"test_cases": test_cases}
    except Exception as e:
        logger.error(f"[generate_test_cases] {e}")
        return {"test_cases": {"integration_tests": []}, "error": str(e)}


def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    import unicodedata
    # Normalize unicode and convert to ASCII
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Replace spaces and special chars with hyphen
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:50] if text else 'unnamed'


async def generate_integration_tests(state: TesterState) -> dict:
    """Generate integration test files - one file per story, processed in parallel."""
    import asyncio
    
    test_cases = state.get("test_cases", {}).get("integration_tests", [])
    project_path = state.get("project_path", "")
    stories = state.get("stories", [])
    
    # Get CocoIndex context for code generation
    project_context = state.get("project_context", "")
    test_examples = state.get("test_examples", "")
    testing_context = state.get("testing_context", {})
    
    if not test_cases or not project_path:
        return {"result": {"integration": {"test_count": 0, "files": []}}}
    
    tests_dir = Path(project_path) / "tests" / "integration"
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # Create story lookup map
    story_map = {s["id"]: s for s in stories}
    
    # Group test cases by story_id
    grouped_by_story = {}
    for tc in test_cases:
        story_id = tc.get("story_id", "unknown")
        if story_id not in grouped_by_story:
            grouped_by_story[story_id] = []
        grouped_by_story[story_id].append(tc)
    
    async def process_story(story_id: str, story_test_cases: list) -> dict | None:
        """Process a single story - generate and write test file."""
        story = story_map.get(story_id, {})
        story_title = story.get("title", "unknown")
        story_slug = _slugify(story_title)
        
        # Generate filename: story-{slug}.test.ts
        test_filename = f"story-{story_slug}.test.ts"
        test_file_path = tests_dir / test_filename
        
        # Check existing file for this story
        existing_titles = set()
        existing_content = ""
        
        if test_file_path.exists():
            existing_content = test_file_path.read_text(encoding='utf-8')
            existing_titles = set(re.findall(r"(?:test|it)\s*\(['\"]([^'\"]+)['\"]", existing_content))
        
        # Filter duplicates
        new_cases = [tc for tc in story_test_cases if tc.get("title", "").lower() not in {t.lower() for t in existing_titles}]
        skipped = len(story_test_cases) - len(new_cases)
        
        if not new_cases:
            return {"skipped": skipped, "created": 0, "file_info": None}
        
        # Generate code
        task = "generate_integration_test_append" if existing_content else "generate_integration_test_new"
        try:
            # Build testing context string
            testing_ctx_str = ""
            if testing_context:
                if testing_context.get("auth_pattern"):
                    testing_ctx_str += f"\n{testing_context['auth_pattern']}\n"
                if testing_context.get("prisma_mock_pattern"):
                    testing_ctx_str += f"\n{testing_context['prisma_mock_pattern']}\n"
                if testing_context.get("esm_warning"):
                    testing_ctx_str += f"\n{testing_context['esm_warning']}\n"
                if testing_context.get("existing_mocks"):
                    testing_ctx_str += f"\nEXISTING MOCKS (already in jest.setup.ts - DO NOT recreate):\n- " + "\n- ".join(testing_context["existing_mocks"]) + "\n"
            
            response = await _llm.ainvoke([
                SystemMessage(content=get_system_prompt(task)),
                HumanMessage(content=get_user_prompt(
                    task,
                    test_cases=json.dumps(new_cases, indent=2),
                    story_title=story_title,
                    existing_titles=str(list(existing_titles)[:20]) if existing_content else "",
                    project_context=project_context[:2000] if project_context else "",
                    test_examples=test_examples[:1500] if test_examples else "",
                    testing_context=testing_ctx_str
                ))
            ], config=_cfg(state, f"generate_integration_tests_{story_slug}"))
            
            new_content = _strip_markdown(response.content)
            
            # Write file
            if existing_content:
                pos = existing_content.rfind("});")
                if pos > 0:
                    final = existing_content[:pos] + "\n\n" + new_content + "\n" + existing_content[pos:]
                else:
                    final = existing_content + "\n\n" + new_content
                test_file_path.write_text(final, encoding='utf-8')
            else:
                test_file_path.write_text(new_content, encoding='utf-8')
            
            logger.info(f"[generate_integration_tests] Created {len(new_cases)} tests for story '{story_title}'")
            
            return {
                "skipped": skipped,
                "created": len(new_cases),
                "file_info": {
                    "filename": f"tests/integration/{test_filename}",
                    "story_id": story_id,
                    "story_title": story_title,
                    "test_count": len(new_cases)
                }
            }
        except Exception as e:
            logger.error(f"[generate_integration_tests] Error for story {story_id}: {e}")
            return {"skipped": skipped, "created": 0, "file_info": None, "error": str(e)}
    
    # Process all stories in parallel
    tasks = [process_story(story_id, cases) for story_id, cases in grouped_by_story.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Aggregate results
    total_created = 0
    total_skipped = 0
    files_created = []
    
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"[generate_integration_tests] Task exception: {r}")
            continue
        if r:
            total_skipped += r.get("skipped", 0)
            total_created += r.get("created", 0)
            if r.get("file_info"):
                files_created.append(r["file_info"])
    
    logger.info(f"[generate_integration_tests] Parallel processing done: {total_created} tests in {len(files_created)} files")
    
    return {"result": {"integration": {
        "files": files_created,
        "test_count": total_created,
        "skipped_duplicates": total_skipped,
    }}}


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
1. Run integration tests
2. Analyze the results
3. If ALL tests pass → Report success
4. If tests FAIL:
   - Create a bug story using create_bug_story tool
   - Include failing test names and error messages

Always respond in Vietnamese with a summary of test results."""


async def execute_and_verify(state: TesterState, agent=None) -> dict:
    """Execute integration tests and handle results using React Agent."""
    from langgraph.prebuilt import create_react_agent
    from app.agents.tester.src.tools import get_execution_tools
    
    result = state.get("result", {})
    stories = state.get("stories", [])
    project_id = state.get("project_id", "")
    
    int_result = result.get("integration", {})
    int_count = int_result.get("test_count", 0)
    files_created = int_result.get("files", [])
    
    # Skip if no tests were generated
    if int_count == 0:
        return {"test_execution": {"skipped": True, "reason": "No new tests generated"}}
    
    try:
        tools = get_execution_tools()
        react_agent = create_react_agent(_llm, tools)
        
        # Build context - list all test files
        files_list = "\n".join([f"  - {f['filename']} ({f['test_count']} tests, story: {f['story_title']})" for f in files_created])
        story_context = "\n".join([f"- {s['title']} (ID: {s['id']})" for s in stories])
        first_story_id = stories[0]["id"] if stories else ""
        
        user_message = f"""Chạy integration tests và xử lý kết quả.

Project ID: {project_id}

**Integration Tests:** {int_count} tests trong {len(files_created)} files:
{files_list}

Stories được test:
{story_context}

Hãy:
1. Chạy tất cả integration tests với run_tests(project_id="{project_id}", test_type="integration")
2. Nếu có test fail → tạo bug story với create_bug_story, parent_story_id="{first_story_id}"
3. Báo cáo kết quả"""

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
    files_created = int_result.get("files", [])
    
    # Create lookup for story -> file info
    story_file_map = {f["story_id"]: f for f in files_created}
    
    # Build message
    if error:
        msg = f"Có lỗi xảy ra: {error}"
    else:
        int_count = int_result.get("test_count", 0)
        
        if int_count == 0:
            msg = "Không có tests mới được tạo (có thể đã tồn tại hoặc không có stories trong Review)."
        else:
            msg = f"✅ Đã tạo {int_count} integration tests trong {len(files_created)} files:"
            for f in files_created:
                msg += f"\n  - {f['filename']} ({f['test_count']} tests)"
        
        # Append test execution results
        if test_execution.get("completed"):
            exec_msg = test_execution.get("message", "")
            if exec_msg:
                msg += f"\n\n**Kết quả chạy tests:**\n{exec_msg[:500]}"
    
    # Update story states and send messages per story
    if agent and stories:
        for story in stories:
            story_id = story["id"]
            story_uuid = UUID(story_id)
            file_info = story_file_map.get(story_id, {})
            story_test_count = file_info.get("test_count", 0)
            
            try:
                await agent.update_story_agent_state(
                    story_id=story_uuid,
                    new_state="finished",
                    progress_message=msg[:200]
                )
                
                if story_test_count > 0:
                    await agent.message_story(
                        story_id=story_uuid,
                        content=f"✅ Đã tạo {story_test_count} integration tests → {file_info.get('filename', '')}",
                        message_type="test_result",
                        details=file_info,
                    )
            except Exception as e:
                logger.warning(f"[send_response] Failed to update story {story_id}: {e}")
    
    # Message user if user-initiated
    if agent and _should_message_user(state):
        await agent.message_user("response", msg)
    
    return {"message": msg}
