"""Developer V2 Agent using DeepAgents framework.

Replaces the LangGraph state machine with DeepAgents' agent harness.
Features:
- Built-in filesystem tools (ls, read_file, write_file, edit_file, glob, grep)
- Automatic context eviction (>20k tokens)
- Long-term memory via StoreBackend
- Skills loaded from filesystem
- Human-in-the-loop for commits
"""

import json
import logging
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.tools import tool
from langgraph.store.memory import InMemoryStore

from app.agents.core.base_agent import BaseAgent, TaskContext, TaskResult
from app.agents.core.project_context import ProjectContext
from app.agents.developer_v2.src.tools.cocoindex_tools import (
    get_agents_md,
    get_project_context,
    index_workspace,
    set_tool_context,
)
from app.agents.developer_v2.src.tools.shell_tools import (
    execute_shell,
    semantic_code_search,
    set_shell_context,
)
from app.agents.developer_v2.src.tools.workspace_tools import (
    commit_workspace_changes as _commit_workspace_changes,
)
from app.agents.developer_v2.src.tools.workspace_tools import (
    setup_git_worktree as _setup_git_worktree,
)
from app.agents.developer_v2.workspace_manager import ProjectWorkspaceManager
from app.kafka.event_schemas import AgentTaskType
from app.models import Agent as AgentModel

logger = logging.getLogger(__name__)

# Skills directory
SKILLS_DIR = Path(__file__).parent / "src" / "skills"


def _get_available_skills() -> str:
    """Get list of available skills from filesystem."""
    skills = []

    for tech_stack in SKILLS_DIR.iterdir():
        if tech_stack.is_dir() and not tech_stack.name.startswith("__"):
            for skill_dir in tech_stack.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        skill_id = f"{tech_stack.name}/{skill_dir.name}"
                        # Read first line for description
                        try:
                            content = skill_file.read_text(encoding="utf-8")
                            # Parse YAML frontmatter for description
                            if content.startswith("---"):
                                parts = content.split("---", 2)
                                if len(parts) >= 3:
                                    import yaml

                                    frontmatter = yaml.safe_load(parts[1])
                                    desc = frontmatter.get("description", "")
                                    skills.append(
                                        f"- /skills/{skill_id}/SKILL.md: {desc}"
                                    )
                        except Exception:
                            skills.append(f"- /skills/{skill_id}/SKILL.md")

    return "\n".join(skills) if skills else "No skills available"


def _build_system_prompt(agents_md: str = "", project_context: str = "") -> str:
    """Build system prompt for DeepAgents developer."""
    skills_list = _get_available_skills()

    return f"""You are a Senior Developer implementing user stories.

## Your Capabilities
- Filesystem: ls, read_file, write_file, edit_file, glob, grep
- Custom: setup_workspace, run_tests, commit_changes, semantic_search
- Planning: write_todos, read_todos

## Workflow
1. **Understand**: Read the story carefully, identify requirements
2. **Plan**: Use write_todos to create implementation plan (1 todo = 1 file)
3. **Setup**: Call setup_workspace(story_id) to create git branch
4. **Implement**: For each todo:
   - Read skill from /skills/ if needed for conventions
   - Use semantic_search to find related code
   - Read existing files before modifying
   - Write/edit code following project patterns
   - Run tests with run_tests()
5. **Debug**: If tests fail (max 5 retries):
   - Analyze error output carefully
   - Check /memories/past_errors/ for similar issues
   - Fix the specific issue and retry
   - Save successful fixes to /memories/learned_fixes/
6. **Complete**: Call commit_changes(message) when all tests pass

## Skills (read when implementing specific patterns)
{skills_list}

## Memory Paths (persistent across sessions)
- /memories/past_errors/ - Previous errors and their fixes
- /memories/learned_fixes/ - Successful debug patterns
- /memories/conventions/ - Learned project conventions

## Project Context
{project_context[:2000] if project_context else "No project context loaded"}

## Coding Guidelines
{agents_md[:3000] if agents_md else "No AGENTS.md found"}

## Rules
- ONE todo = ONE file modification
- ALWAYS read existing code before editing
- Use edit_file with EXACT string match for modifications
- Run tests after EACH code change
- Follow existing project patterns and conventions
- Use named exports (no default exports) for components
- Add 'use client' only when using hooks/events
"""


class DeveloperV2DeepAgent(BaseAgent):
    """Developer V2 using DeepAgents framework."""

    def __init__(self, agent_model: AgentModel, **kwargs):
        super().__init__(agent_model, **kwargs)
        logger.info(f"[{self.name}] Initializing Developer V2 DeepAgent")

        self.context = ProjectContext.get(self.project_id)
        self.workspace_manager = ProjectWorkspaceManager(self.project_id)
        self.main_workspace = self.workspace_manager.get_main_workspace()

        # Memory store for persistent context
        self.memory_store = InMemoryStore()

        # Will be initialized on first task
        self._agent = None
        self._current_workspace = None
        self._current_branch = None

        logger.info(
            f"[{self.name}] DeepAgent initialized, workspace: {self.main_workspace}"
        )

    def _create_tools(self) -> list:
        """Create custom tools for the agent."""
        workspace_path = self._current_workspace or str(self.main_workspace)

        @tool
        def setup_workspace(story_id: str) -> str:
            """Setup git worktree and branch for a story.

            Args:
                story_id: The story ID to create branch for
            """
            result = _setup_git_worktree(
                story_id=story_id,
                main_workspace=self.main_workspace,
                agent_name=self.name,
            )

            self._current_workspace = result.get("workspace_path")
            self._current_branch = result.get("branch_name")

            # Update tool contexts
            if self._current_workspace:
                set_shell_context(root_dir=self._current_workspace)
                set_tool_context(
                    project_id=str(self.project_id),
                    workspace_path=self._current_workspace,
                    task_id=story_id,
                )

                # Index workspace for semantic search
                try:
                    index_workspace(
                        str(self.project_id), self._current_workspace, story_id
                    )
                except Exception as e:
                    logger.warning(f"[{self.name}] Index failed: {e}")

            if result.get("workspace_ready"):
                return f"Workspace ready: {self._current_workspace}\nBranch: {self._current_branch}"
            else:
                return f"Warning: Using main workspace (worktree failed): {self._current_workspace}"

        @tool
        def run_tests(test_command: str = "") -> str:
            """Run tests and return results.

            Args:
                test_command: Optional custom test command. If empty, uses default.
            """
            if not self._current_workspace:
                return "Error: Workspace not setup. Call setup_workspace first."

            # Default test commands based on project
            if not test_command:
                package_json = Path(self._current_workspace) / "package.json"
                if package_json.exists():
                    test_command = "pnpm test"
                else:
                    test_command = "pytest"

            # Run lint fix first
            lint_result = execute_shell.invoke(
                {
                    "command": "pnpm lint:fix"
                    if "pnpm" in test_command
                    else "ruff check --fix .",
                    "working_directory": self._current_workspace,
                    "timeout": 60,
                }
            )

            # Run tests
            test_result = execute_shell.invoke(
                {
                    "command": test_command,
                    "working_directory": self._current_workspace,
                    "timeout": 120,
                }
            )

            if isinstance(test_result, str):
                result_data = json.loads(test_result)
            else:
                result_data = test_result

            if result_data.get("exit_code", 0) == 0:
                return f"✅ Tests PASSED\n\nOutput:\n{result_data.get('stdout', '')[:2000]}"
            else:
                return f"❌ Tests FAILED\n\nStdout:\n{result_data.get('stdout', '')[:1500]}\n\nStderr:\n{result_data.get('stderr', '')[:1500]}"

        @tool
        def commit_changes(message: str) -> str:
            """Commit all changes with a message. Requires human approval.

            Args:
                message: Commit message describing the changes
            """
            if not self._current_workspace:
                return "Error: No workspace to commit"

            result = _commit_workspace_changes(
                workspace_path=self._current_workspace,
                title=message,
                branch_name=self._current_branch or "unknown",
                agent_name=self.name,
            )

            return f"Commit result: {result}"

        @tool
        def semantic_search(query: str, top_k: int = 5) -> str:
            """Search codebase using semantic search.

            Args:
                query: Natural language query (e.g., 'user authentication', 'form validation')
                top_k: Number of results to return
            """
            return semantic_code_search.invoke({"query": query, "top_k": top_k})

        return [setup_workspace, run_tests, commit_changes, semantic_search]

    def _create_agent(self, agents_md: str = "", project_context: str = ""):
        """Create the DeepAgent with current context."""
        workspace_path = self._current_workspace or str(self.main_workspace)

        # Backend: project filesystem
        # Note: Skills are in src/skills/ relative to this file
        # Memory is handled via InMemoryStore (in-session only for now)
        backend = FilesystemBackend(root_dir=workspace_path)

        tools = self._create_tools()

        self._agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-20250514",
            tools=tools,
            backend=backend,
            system_prompt=_build_system_prompt(agents_md, project_context),
            interrupt_on={
                "commit_changes": {"allowed_decisions": ["approve", "reject", "edit"]}
            },
            
        )

        return self._agent

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Handle task using DeepAgent."""
        logger.info(f"[{self.name}] Received task: type={task.task_type}")

        await self.context.ensure_loaded()

        if task.task_type == AgentTaskType.IMPLEMENT_STORY:
            return await self._handle_story_processing(task)
        else:
            return await self._handle_user_message(task)

    async def _handle_user_message(self, task: TaskContext) -> TaskResult:
        """Handle direct messages."""
        content = task.content.lower()

        if "help" in content or "giúp" in content:
            msg = """Tôi là Developer , chuyên implement code! 💻

**Cách sử dụng:**
- Kéo story sang In Progress → Tôi tự động bắt đầu
- Hoặc nhắn trực tiếp yêu cầu implement

**Tính năng mới:**
- Long-term memory (nhớ lỗi đã fix)
- Skill-based patterns
- Human-in-the-loop cho commits
"""
            await self.message_user("response", msg)
            return TaskResult(success=True, output=msg)

        # Process as story request
        return await self._process_with_agent(task.content, str(task.task_id))

    async def _handle_story_processing(self, task: TaskContext) -> TaskResult:
        """Handle story processing."""
        try:
            story_data = self._parse_story_content(task)
            story_content = f"""# Story: {story_data.get("title", "Untitled")}

{story_data.get("content", task.content)}

## Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in story_data.get("acceptance_criteria", []))}
"""
            return await self._process_with_agent(
                story_content, story_data.get("story_id", str(task.task_id))
            )
        except Exception as e:
            logger.error(f"[{self.name}] Story processing error: {e}", exc_info=True)
            return TaskResult(success=False, output="", error_message=str(e))

    async def _process_with_agent(self, content: str, story_id: str) -> TaskResult:
        """Process content with DeepAgent."""
        try:
            # Load project context
            agents_md = ""
            project_context = ""
            if self.main_workspace:
                try:
                    agents_md = get_agents_md(str(self.main_workspace))
                    project_context = get_project_context(str(self.main_workspace))
                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to load context: {e}")

            # Create/update agent
            agent = self._create_agent(agents_md, project_context)

            # Set initial context
            set_tool_context(
                project_id=str(self.project_id),
                workspace_path=str(self.main_workspace),
                task_id=story_id,
            )

            # Invoke agent
            logger.info(f"[{self.name}] Invoking DeepAgent for story: {story_id}")
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": content}]}
            )

            # Extract final message
            messages = result.get("messages", [])
            final_message = ""
            if messages:
                last_msg = messages[-1]
                if hasattr(last_msg, "content"):
                    final_message = last_msg.content
                elif isinstance(last_msg, dict):
                    final_message = last_msg.get("content", str(last_msg))

            await self.message_user("response", final_message or "Task completed")

            return TaskResult(
                success=True,
                output=final_message,
                structured_data={
                    "story_id": story_id,
                    "branch_name": self._current_branch,
                    "workspace_path": self._current_workspace,
                },
            )

        except Exception as e:
            logger.error(f"[{self.name}] Agent execution error: {e}", exc_info=True)
            error_msg = f"Lỗi khi xử lý: {str(e)}"
            await self.message_user("error", error_msg)
            return TaskResult(success=False, output="", error_message=str(e))

    def _parse_story_content(self, task: TaskContext) -> dict:
        """Parse story content from task."""
        content = task.content

        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return {
                    "story_id": data.get("story_id", data.get("id", str(task.task_id))),
                    "title": data.get("title", data.get("name", "Untitled")),
                    "content": data.get("content", data.get("description", "")),
                    "acceptance_criteria": data.get(
                        "acceptance_criteria", data.get("ac", [])
                    ),
                }
        except (json.JSONDecodeError, TypeError):
            pass

        lines = content.strip().split("\n")
        title = lines[0] if lines else "Untitled"

        acceptance_criteria = []
        ac_start = -1
        for i, line in enumerate(lines):
            if "acceptance criteria" in line.lower() or "ac:" in line.lower():
                ac_start = i + 1
                break

        if ac_start > 0:
            for line in lines[ac_start:]:
                line = line.strip()
                if line.startswith(("-", "*", "•")):
                    acceptance_criteria.append(line[1:].strip())
                elif line:
                    acceptance_criteria.append(line)

        return {
            "story_id": str(task.task_id),
            "title": title,
            "content": content,
            "acceptance_criteria": acceptance_criteria,
        }

    async def handle_story_event(
        self,
        story_id: str,
        story_title: str,
        story_content: str,
        acceptance_criteria: list[str] | None = None,
        from_status: str = "Todo",
        to_status: str = "InProgress",
    ) -> TaskResult:
        """Handle story status change event."""
        logger.info(
            f"[{self.name}] Story event: {story_id} ({from_status} -> {to_status})"
        )

        if to_status != "InProgress":
            return TaskResult(success=True, output="Story event ignored")

        from uuid import uuid4

        story_data = json.dumps(
            {
                "story_id": story_id,
                "title": story_title,
                "content": story_content,
                "acceptance_criteria": acceptance_criteria or [],
            }
        )

        task = TaskContext(
            task_id=uuid4(),
            task_type=AgentTaskType.IMPLEMENT_STORY,
            priority="high",
            project_id=self.project_id,
            content=story_data,
        )

        return await self.handle_task(task)
