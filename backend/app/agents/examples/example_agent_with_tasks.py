"""Example Agent Using @on_task Decorators

This is a complete example showing how to use the new task abstraction layer.
"""

from crewai import Agent, Crew, Task, Process
from app.agents.core.base_role import BaseAgentRole
from app.agents.core.crew_hooks import on_task
from app.kafka.event_schemas import AgentTaskType


class ExampleDeveloperAgent(BaseAgentRole):
    """Example developer agent with @on_task handlers."""

    @property
    def role_name(self) -> str:
        return "ExampleDeveloper"

    @property
    def agent_type(self) -> str:
        return "developer"

    @property
    def kafka_topic(self) -> str:
        from app.kafka.event_schemas import get_project_topic
        return get_project_topic(self.project_id)

    # ===== @on_task Handlers =====

    @on_task(AgentTaskType.IMPLEMENT_STORY)
    def handle_implement_story(self, context):
        """Auto-triggered when IMPLEMENT_STORY task assigned.

        Context will contain:
        - task_id, task_type, title, description
        - story_id, project_id
        - Any custom data from task.context
        """
        print(f"[ExampleDev] Implementing story: {context['title']}")

        # Create crew for implementation
        return Crew(
            agents=[self.create_agent()],
            tasks=[
                Task(
                    description=f"Implement the following story:\n{context['description']}",
                    expected_output="Source code files and tests",
                    agent=self.create_agent()
                )
            ],
            process=Process.sequential,
            verbose=True
        )
        # → Crew will be auto-kicked off
        # → Progress tracked via self.task_queue
        # → Result published when complete

    @on_task(AgentTaskType.FIX_BUG)
    def handle_fix_bug(self, context):
        """Auto-triggered when FIX_BUG task assigned."""
        print(f"[ExampleDev] Fixing bug: {context['title']}")

        return Crew(
            agents=[self.create_agent()],
            tasks=[
                Task(
                    description=f"Fix bug:\n{context['description']}",
                    expected_output="Bug fix with tests"
                )
            ],
            process=Process.sequential
        )

    @on_task(AgentTaskType.MESSAGE)
    async def handle_message(self, task):
        """Handle direct user messages (no crew needed).

        For simple responses that don't need crew execution.
        """
        # Extract message content
        if hasattr(task, 'context'):
            content = task.context.get('content', '')
        else:
            content = task.get('context', {}).get('content', '')

        print(f"[ExampleDev] Received message: {content}")

        # Can use task_queue directly for progress
        task_id = task.task_id if hasattr(task, 'task_id') else task.get('task_id')

        await self.task_queue.report_progress(
            task_id=task_id,
            progress_percentage=50,
            current_step="Processing message",
            steps_completed=1,
            total_steps=2
        )

        # Generate response (simple logic, no crew)
        response = f"Developer here! You said: {content}"

        await self.task_queue.report_progress(
            task_id=task_id,
            progress_percentage=100,
            current_step="Response generated",
            steps_completed=2,
            total_steps=2
        )

        # Return result (will be published via task_queue)
        return {
            "response": response,
            "agent": "ExampleDeveloper"
        }

    @on_task(AgentTaskType.USER_STORY)
    def handle_user_story(self, context):
        """Handle USER_STORY tasks (typically for BA agents)."""
        print(f"[ExampleDev] Creating user stories from: {context['title']}")

        # This would typically be BA's job, but showing example
        return Crew(
            agents=[self.create_agent()],
            tasks=[
                Task(
                    description=f"Analyze requirements and create user stories:\n{context['description']}",
                    expected_output="List of user stories in JSON format"
                )
            ],
            process=Process.sequential
        )

    # ===== Required Abstract Methods =====

    def create_agent(self) -> Agent:
        """Create CrewAI agent."""
        return Agent(
            role="Software Developer",
            goal="Write high-quality, tested code",
            backstory="Expert Python developer with 10 years experience",
            verbose=True,
            allow_delegation=False
        )

    def create_tasks(self, context):
        """Create tasks (used by create_agent's crew)."""
        return [
            Task(
                description=f"Complete: {context.get('description', 'task')}",
                expected_output="Completed work"
            )
        ]

    async def process_message(self, message):
        """Process message from Kafka (legacy method, still required)."""
        # This is for backward compatibility
        # New approach uses @on_task instead
        print(f"[ExampleDev] Legacy message handler: {message}")
        return {"status": "processed"}


# ===== Usage Example =====

if __name__ == "__main__":
    import asyncio
    from uuid import uuid4
    from app.agents.core.task_dispatcher import get_task_dispatcher
    from app.kafka.event_schemas import AgentTaskAssignedEvent

    async def example_usage():
        """Show how to assign tasks to agents."""

        # Get dispatcher
        dispatcher = await get_task_dispatcher()

        # Create task
        task = AgentTaskAssignedEvent(
            task_id=uuid4(),
            task_type=AgentTaskType.IMPLEMENT_STORY,
            agent_id=uuid4(),  # Target agent UUID
            agent_name="ExampleDeveloper",
            assigned_by="Team Leader",
            title="Build user login feature",
            description="Implement OAuth2 login with JWT tokens",
            priority="high",
            story_id=uuid4(),
            project_id=uuid4(),
            context={
                "story_points": 5,
                "acceptance_criteria": [
                    "User can login with Google",
                    "JWT token issued on success",
                    "Token stored securely"
                ]
            }
        )

        # Assign task
        success = await dispatcher.assign_task(
            task=task,
            agent_id=task.agent_id,
            project_id=task.project_id
        )

        if success:
            print(f"✓ Task assigned to agent {task.agent_id}")
            print("→ Task published to AGENT_TASKS topic")
            print("→ Partitioned by agent_id")
            print("→ Agent will receive it")
            print("→ @on_task(IMPLEMENT_STORY) will be triggered")
            print("→ Crew will be created and kicked off")
            print("→ Progress reported via task_queue")
            print("→ Result published when complete")

    # Run example
    # asyncio.run(example_usage())
