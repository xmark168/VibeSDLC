import asyncio
import os
from uuid import UUID, uuid4
from pathlib import Path

from sqlmodel import Session

from app.agents.core.base_agent import TaskContext
from app.agents.developer.developer import Developer
from app.core.db import engine
from app.kafka.event_schemas import AgentTaskType
from app.models import Agent as AgentModel
from app.models import AgentStatus


class CustomDeveloper(Developer):
    """Developer agent with custom working directory."""

    def __init__(self, agent_model, **kwargs):
        super().__init__(agent_model, **kwargs)
        # Cập nhật lại crew với đường dẫn mới được tạo dựa trên project_id
        from app.agents.developer.crew import DeveloperCrew

        # Tạo thư mục dự án dựa trên project_id (dùng phần đầu của UUID để ngắn gọn)
        project_id_short = str(self.project_id).split('-')[0]  # Lấy phần đầu tiên trước dấu gạch ngang
        project_base_path = Path(__file__).parent / "app" / "agents" / "developer" / f"proj_{project_id_short}"
        project_base_path.mkdir(exist_ok=True)

        # Đường dẫn đến workspace chính cho dự án này
        main_workspace = project_base_path / "ws_main"

        # Nếu thư mục chưa tồn tại, sao chép từ thư mục mẫu
        if not main_workspace.exists():
            source_workspace = Path(__file__).parent / "app" / "agents" / "developer" / "project_test_id" / "workspace_main"
            if source_workspace.exists():
                import shutil
                shutil.copytree(source_workspace, main_workspace)

        self.crew = DeveloperCrew(
            project_id=str(self.project_id),
            root_dir=str(main_workspace),
        )


async def main():
    # Sử dụng project ID bạn vừa tạo
    project_id = UUID("2d7d5f2e-bae4-49d6-9df6-4a4c92a4c8fb")

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
