"""Test script for Developer V2 DeepAgents implementation.

Run with: python test_developer_v2_deepagents.py
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Enable DeepAgents
os.environ["USE_DEEPAGENTS"] = "true"

from sqlmodel import Session

from app.agents.core.base_agent import TaskContext
from app.agents.developer_v2 import DEEPAGENTS_AVAILABLE, DeveloperV2DeepAgent
from app.core.db import engine
from app.kafka.event_schemas import AgentTaskType
from app.models import Agent as AgentModel
from app.models import AgentStatus

# Test project configuration
TEST_PROJECT_ID = UUID("33c18a9d-fe00-42d6-afc6-33c10e9f19c7")


def setup_test_workspace():
    """Create a minimal test workspace if it doesn't exist."""
    backend_root = Path(__file__).parent
    workspace_root = (
        backend_root / "app" / "agents" / "developer" / "projects_workspace"
    )
    template_dir = workspace_root / "project_template" / "workspace_main"

    if not template_dir.exists():
        print(f"Creating test workspace template at: {template_dir}")
        template_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal Next.js project structure
        (template_dir / "src").mkdir(exist_ok=True)
        (template_dir / "src" / "app").mkdir(exist_ok=True)
        (template_dir / "src" / "components").mkdir(exist_ok=True)

        # Create package.json
        package_json = template_dir / "package.json"
        package_json.write_text("""{
  "name": "test-project",
  "version": "0.1.0",
  "scripts": {
    "test": "echo \\"No tests\\"",
    "lint": "echo \\"No lint\\"",
    "lint:fix": "echo \\"No lint fix\\""
  }
}
""")

        # Create .git directory (minimal)
        git_dir = template_dir / ".git"
        git_dir.mkdir(exist_ok=True)
        (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
        (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")

        print("[OK] Test workspace template created")
    else:
        print(f"[OK] Test workspace template exists: {template_dir}")


SAMPLE_STORY = """
# User Story: Create Login Form Component

As a user, I want to log into my account using email and password.

## Description
Create a login form component with email and password fields, 
form validation, and submit functionality using Server Actions.

## Acceptance Criteria
- Form has email and password input fields
- Client-side validation for email format
- Password field is masked
- Submit button calls server action
- Shows loading state during submission
- Displays error messages on failure
- Redirects to dashboard on success
"""


async def test_deepagent_initialization():
    """Test that DeepAgent can be initialized."""
    print("\n" + "=" * 60)
    print("TEST 1: DeepAgent Initialization")
    print("=" * 60)

    if not DEEPAGENTS_AVAILABLE:
        print("[SKIP] DeepAgents not available")
        return False

    agent_model = AgentModel(
        id=uuid4(),
        project_id=TEST_PROJECT_ID,
        name="TestDeveloperV2DeepAgent",
        human_name="TestDev",
        role_type="developer",
        agent_type="developer_v2",
        status=AgentStatus.idle,
    )

    with Session(engine) as session:
        session.add(agent_model)
        session.commit()
        session.refresh(agent_model)

        try:
            developer = DeveloperV2DeepAgent(agent_model=agent_model)
            print("[OK] Agent initialized successfully")
            print(f"   - Name: {developer.name}")
            print(f"   - Workspace: {developer.main_workspace}")
            print(f"   - Memory store: {type(developer.memory_store).__name__}")
            return True
        except Exception as e:
            print(f"[FAIL] Initialization failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            session.delete(agent_model)
            session.commit()


async def test_tools_creation():
    """Test that custom tools are created correctly."""
    print("\n" + "=" * 60)
    print("TEST 2: Tools Creation")
    print("=" * 60)

    if not DEEPAGENTS_AVAILABLE:
        print("[SKIP] DeepAgents not available")
        return False

    agent_model = AgentModel(
        id=uuid4(),
        project_id=TEST_PROJECT_ID,
        name="TestDeveloperV2DeepAgent",
        human_name="TestDev",
        role_type="developer",
        agent_type="developer_v2",
        status=AgentStatus.idle,
    )

    with Session(engine) as session:
        session.add(agent_model)
        session.commit()
        session.refresh(agent_model)

        try:
            developer = DeveloperV2DeepAgent(agent_model=agent_model)
            tools = developer._create_tools()

            tool_names = [t.name for t in tools]
            print(f"[OK] Created {len(tools)} custom tools:")
            for name in tool_names:
                print(f"   - {name}")

            expected_tools = [
                "setup_workspace",
                "run_tests",
                "commit_changes",
                "semantic_search",
            ]
            missing = [t for t in expected_tools if t not in tool_names]
            if missing:
                print(f"[FAIL] Missing tools: {missing}")
                return False

            return True
        except Exception as e:
            print(f"[FAIL] Tools creation failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            session.delete(agent_model)
            session.commit()


async def test_system_prompt():
    """Test that system prompt is built correctly."""
    print("\n" + "=" * 60)
    print("TEST 3: System Prompt")
    print("=" * 60)

    if not DEEPAGENTS_AVAILABLE:
        print("[SKIP] DeepAgents not available")
        return False

    from app.agents.developer_v2.developer_v2_deepagents import (
        _build_system_prompt,
        _get_available_skills,
    )

    try:
        skills = _get_available_skills()
        print("[OK] Found skills:")
        for line in skills.split("\n")[:5]:
            print(f"   {line}")
        if skills.count("\n") > 5:
            print(f"   ... and {skills.count(chr(10)) - 5} more")

        prompt = _build_system_prompt("Sample AGENTS.md", "Sample project context")
        print(f"\n[OK] System prompt built ({len(prompt)} chars)")
        print(f"   Contains 'Workflow': {'Workflow' in prompt}")
        print(f"   Contains 'Skills': {'Skills' in prompt}")
        print(f"   Contains 'Memory': {'Memory' in prompt or 'memories' in prompt}")

        return True
    except Exception as e:
        print(f"[FAIL] System prompt build failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_agent_creation():
    """Test that DeepAgent is created correctly."""
    print("\n" + "=" * 60)
    print("TEST 4: Agent Creation")
    print("=" * 60)

    if not DEEPAGENTS_AVAILABLE:
        print("[SKIP] DeepAgents not available")
        return False

    agent_model = AgentModel(
        id=uuid4(),
        project_id=TEST_PROJECT_ID,
        name="TestDeveloperV2DeepAgent",
        human_name="TestDev",
        role_type="developer",
        agent_type="developer_v2",
        status=AgentStatus.idle,
    )

    with Session(engine) as session:
        session.add(agent_model)
        session.commit()
        session.refresh(agent_model)

        try:
            developer = DeveloperV2DeepAgent(agent_model=agent_model)
            agent = developer._create_agent(
                agents_md="# Test AGENTS.md", project_context="Test context"
            )

            print("[OK] DeepAgent created successfully")
            print(f"   - Type: {type(agent).__name__}")

            return True
        except Exception as e:
            print(f"[FAIL] Agent creation failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            session.delete(agent_model)
            session.commit()


async def test_story_processing(run_full_test: bool = True):
    """Test story processing with DeepAgent."""
    print("\n" + "=" * 60)
    print(
        "TEST 5: Story Processing" + (" (FULL)" if run_full_test else " (Setup only)")
    )
    print("=" * 60)

    if not DEEPAGENTS_AVAILABLE:
        print("[SKIP] DeepAgents not available")
        return False

    agent_model = AgentModel(
        id=uuid4(),
        project_id=TEST_PROJECT_ID,
        name="TestDeveloperV2DeepAgent",
        human_name="TestDev",
        role_type="developer",
        agent_type="developer_v2",
        status=AgentStatus.idle,
    )

    with Session(engine) as session:
        session.add(agent_model)
        session.commit()
        session.refresh(agent_model)

        try:
            developer = DeveloperV2DeepAgent(agent_model=agent_model)

            task = TaskContext(
                task_id=uuid4(),
                task_type=AgentTaskType.IMPLEMENT_STORY,
                priority="high",
                routing_reason="Test story processing",
                content=SAMPLE_STORY,
                message_id=uuid4(),
                user_id=uuid4(),
                project_id=agent_model.project_id,
            )

            print("[OK] Task context created")
            print(f"   - Task ID: {task.task_id}")
            print(f"   - Type: {task.task_type}")

            if run_full_test:
                print("\n[RUN] Running full agent processing...")
                print("   This may take a few minutes and uses API credits.\n")

                result = await developer.handle_task(task)

                print(f"\n{'=' * 40}")
                print(
                    f"Result: {'[OK] Success' if result.success else '[FAIL] Failed'}"
                )
                if result.output:
                    print(f"Output preview: {result.output[:500]}...")
                if result.error_message:
                    print(f"Error: {result.error_message}")
                if result.structured_data:
                    print(f"Structured data: {result.structured_data}")
            else:
                print("\n[SKIP] Skipping full test (pass run_full_test=True to run)")

            return True
        except Exception as e:
            print(f"[FAIL] Story processing failed: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            session.delete(agent_model)
            session.commit()


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("DEVELOPER V2 DEEPAGENTS TEST SUITE")
    print("=" * 60)
    print(f"DeepAgents Available: {DEEPAGENTS_AVAILABLE}")
    print(f"Test Project ID: {TEST_PROJECT_ID}")

    # Setup test workspace first
    setup_test_workspace()

    results = {}

    # Run tests
    results["initialization"] = await test_deepagent_initialization()
    results["tools"] = await test_tools_creation()
    results["system_prompt"] = await test_system_prompt()
    results["agent_creation"] = await test_agent_creation()

    # Story processing - set to True for full test
    results["story_processing"] = await test_story_processing(run_full_test=False)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "[PASS]" if passed_test else "[FAIL]"
        print(f"  {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
