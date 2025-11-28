import asyncio
import os
import shutil
from uuid import UUID, uuid4
from pathlib import Path

from sqlmodel import Session

from app.agents.core.base_agent import TaskContext, TaskResult
from app.agents.developer.developer import Developer
from app.core.db import engine
from app.kafka.event_schemas import AgentTaskType
from app.models import Agent as AgentModel
from app.models import AgentStatus


class ProjectWorkspaceManager:
    """Manages project workspaces and task branches.

    Directory structure:
    backend/app/agents/developer/projects_workspace/
        project_template/workspace_main/    # Template
        project_{project_id}/               # Each project has its own directory
            ws_main/                        # Main branch workspace
            ws_story_{story_id}/            # Task branch workspaces
    """

    def __init__(self, project_id: UUID):
        self.project_id = project_id
        self.backend_root = Path(__file__).parent

        # Projects workspace root
        self.workspace_root = self.backend_root / "app" / "agents" / "developer" / "projects_workspace"

        # This project's directory
        self.project_dir = self.workspace_root / f"project_{project_id}"

        # Template directory
        self.template_dir = self.workspace_root / "project_template" / "workspace_main"

    def get_main_workspace(self) -> Path:
        """Get or create the main workspace (ws_main) for the project."""
        main_workspace = self.project_dir / "ws_main"

        if not main_workspace.exists():
            self._initialize_workspace(main_workspace)
            print(f"✓ Created main workspace: {main_workspace}")
        else:
            print(f"✓ Using existing main workspace: {main_workspace}")

        return main_workspace

    def get_task_workspace(self, story_id: str) -> Path:
        """Get the path for a task-specific workspace (ws_story_{story_id}).

        Note: Task workspaces are created by Git worktree command in crew.py.
        This method just returns the expected path.
        """
        # Extract short story ID (last part after dash, or first 8 chars)
        short_story_id = story_id.split('-')[-1] if '-' in story_id else story_id[:8]
        task_workspace = self.project_dir / f"ws_story_{short_story_id}"

        return task_workspace

    def _initialize_workspace(self, workspace_path: Path):
        """Initialize a new workspace from template.

        IMPORTANT: Does NOT copy node_modules to avoid Windows path length issues.
        The agent should run 'npm install' or 'bun install' in the workspace if needed.
        """
        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"Template directory not found: {self.template_dir}\n"
                f"Please ensure the template exists at this location."
            )

        # Ensure parent directory exists
        workspace_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy template to workspace, excluding node_modules and other large/generated dirs
        def ignore_patterns(directory, files):
            """Ignore node_modules, .next, build artifacts, and other unnecessary dirs."""
            ignore = set()

            # Always ignore these directories
            ignore_dirs = {
                'node_modules',
                '.next',
                'build',
                'dist',
                'out',
                '.turbo',
                '.cache',
                'coverage',
                '.swc',
                '.git',
                '__pycache__',
                '.pytest_cache',
                '.venv',
                'venv'
            }

            for file in files:
                # Ignore directories in the ignore list
                if file in ignore_dirs:
                    ignore.add(file)
                # Ignore .env files (contains secrets)
                elif file.startswith('.env'):
                    ignore.add(file)
                # Ignore lock files (will be regenerated)
                elif file in {'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lockb'}:
                    ignore.add(file)

            return ignore

        # Copy template with ignore patterns
        shutil.copytree(self.template_dir, workspace_path, ignore=ignore_patterns)

        print(f"✓ Initialized workspace from template: {workspace_path}")
        print(f"⚠ Note: node_modules not copied. Run 'npm install' or 'bun install' in workspace if needed.")


class CustomDeveloper(Developer):
    """Developer agent with project workspace management."""

    def __init__(self, agent_model, **kwargs):
        # Initialize workspace manager BEFORE calling super
        self.workspace_manager = ProjectWorkspaceManager(agent_model.project_id)

        # Get main workspace (creates if doesn't exist)
        main_workspace = self.workspace_manager.get_main_workspace()

        print(f"\n{'='*60}")
        print(f"Project ID: {agent_model.project_id}")
        print(f"Main Workspace: {main_workspace}")
        print(f"Working Directory (root_dir): {main_workspace}")
        print(f"{'='*60}\n")

        # Now call super() - this will set self.project_id
        super().__init__(agent_model, **kwargs)

        # Override the crew with correct workspace path
        from app.agents.developer.crew import DeveloperCrew
        self.crew = DeveloperCrew(
            project_id=str(self.project_id),
            root_dir=str(main_workspace),
        )

        # Store main workspace path for reference
        self.main_workspace = main_workspace

    async def handle_task(self, task: TaskContext) -> TaskResult:
        """Override handle_task to inject correct project_dir."""
        # Inject the correct project_dir into task
        task.project_dir = str(self.main_workspace)

        # Call parent's handle_task
        return await super().handle_task(task)


async def main():
    # Sử dụng project ID bạn vừa tạo
    project_id = UUID("33c18a9d-fe00-42d6-afc6-33c10e9f19c7")

    # Tạo agent model với project_id bạn đã tạo
    agent_model = AgentModel(
        id=uuid4(),
        project_id=project_id,
        name="TestDeveloper",
        human_name="TestDev",
        role_type="developer",
        agent_type="developer",
        status=AgentStatus.idle,
    )

    # Thêm vào database và giữ session mở cho đến khi hoàn thành
    with Session(engine) as session:
        session.add(agent_model)
        session.commit()
        session.refresh(agent_model)

        try:
            # Khởi tạo Developer agent với thư mục demo
            developer = CustomDeveloper(agent_model=agent_model)

            # Tạo task context với đầy đủ các tham số yêu cầu
            task = TaskContext(
                task_id=uuid4(),
                task_type=AgentTaskType.MESSAGE,
                priority="medium",
                routing_reason="Code implementation needed",
                content="""
        As a learner, I want to log into my account 
        so that I can access personalized learning content and track my progress.

        *Description:* 
        Users can log into the platform using their registered email and password 
        (or third-party login options if available). The system validates credentials 
        and grants access to the dashboard upon successful authentication.

        *Acceptance Criteria:*
        - Given I am on the Login Page, When I enter a valid email and password and click “Login”, Then I am successfully logged into my account and redirected to my Dashboard.
        - Given I enter an incorrect email or password, When I click “Login”, Then I see an appropriate error message telling me the credentials are invalid.
        - Given I have forgotten my password, When I click the “Forgot Password” link, Then I am redirected to the password recovery flow.
        - Given the platform supports third-party login (e.g., Google Login), When I click the social login button, Then I can authenticate using my social account and be redirected to my Dashboard.
        - Given I am already logged in, When I revisit the Login Page, Then I should be redirected to my Dashboard automatically (unless I log out).
        """,
                message_id=uuid4(),
                user_id=uuid4(),
                project_id=agent_model.project_id,
            )

            print("Running task...")
            result = await developer.handle_task(task)
            print(f"Result: {result.success}")
            print(f"Output: {result.output[:200] if result.output else 'No output'}...")

        except Exception as e:
            print(f"Error: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Xóa khỏi database
            session.delete(agent_model)
            session.commit()


if __name__ == "__main__":
    asyncio.run(main())
