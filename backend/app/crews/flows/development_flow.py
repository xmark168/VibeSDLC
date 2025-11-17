"""
Development Flow

Orchestrates the development workflow using CrewAI Flow
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from crewai import Crew, Task
from crewai.flow.flow import Flow, listen, start, router
from pydantic import BaseModel

from app.crews.agents import (
    get_business_analyst_agent,
    get_developer_agent,
    get_tester_agent,
    get_team_leader_agent,
)
from app.crews.events.kafka_producer import get_kafka_producer
from app.crews.events.event_schemas import (
    FlowStartedEvent,
    FlowStepCompletedEvent,
    FlowCompletedEvent,
    TaskCreatedEvent,
)


# Flow State Models
class DevelopmentFlowState(BaseModel):
    """State for the development flow"""
    flow_id: str = ""
    project_id: UUID | None = None
    feature_description: str = ""
    triggered_by: str = ""

    # Step outputs
    requirements: dict[str, Any] | None = None
    implementation: dict[str, Any] | None = None
    test_results: dict[str, Any] | None = None
    final_review: dict[str, Any] | None = None

    # Metadata
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: str = "in_progress"  # in_progress, completed, failed


class DevelopmentFlow(Flow[DevelopmentFlowState]):
    """
    Development workflow orchestrated by Team Leader

    Flow: Requirements Analysis -> Implementation -> Testing -> Review
    """

    @start()
    async def initialize(self):
        """
        Initialize the development flow

        Triggered when flow starts
        """
        print(f"🚀 Starting Development Flow: {self.state.flow_id}")

        # Publish flow started event
        producer = await get_kafka_producer()
        event = FlowStartedEvent(
            flow_id=self.state.flow_id,
            flow_type="development_flow",
            project_id=self.state.project_id,
            triggered_by=self.state.triggered_by,
            input_state={"feature_description": self.state.feature_description},
        )
        await producer.publish_flow_started(event)

        return self.state.feature_description

    @listen(initialize)
    async def analyze_requirements(self, feature_description: str):
        """
        Step 1: Business Analyst analyzes requirements

        Creates technical specifications and acceptance criteria
        """
        print(f"📋 Step 1: Analyzing Requirements")

        # Create task for Business Analyst
        ba_agent = get_business_analyst_agent()

        task = Task(
            description=f"""
            Analyze the following feature request and create comprehensive technical specifications:

            Feature: {feature_description}

            Your output should include:
            1. User stories with acceptance criteria
            2. Technical requirements and constraints
            3. Data models and API contracts
            4. Edge cases and error scenarios
            5. Dependencies and integration points
            """,
            expected_output="Comprehensive technical specification document in JSON format",
            agent=ba_agent,
        )

        # Execute task
        crew = Crew(agents=[ba_agent], tasks=[task], verbose=True)
        result = crew.kickoff()

        # Store results in state
        self.state.requirements = {
            "specification": str(result),
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Publish step completed event
        producer = await get_kafka_producer()
        event = FlowStepCompletedEvent(
            flow_id=self.state.flow_id,
            step_name="analyze_requirements",
            output=self.state.requirements,
            next_step="implement_feature",
        )
        await producer.publish_flow_step_completed(event)

        return self.state.requirements

    @listen(analyze_requirements)
    async def implement_feature(self, requirements: dict[str, Any]):
        """
        Step 2: Developer implements the feature

        Writes code based on specifications
        """
        print(f"💻 Step 2: Implementing Feature")

        # Create task for Developer
        dev_agent = get_developer_agent()

        task = Task(
            description=f"""
            Implement the following feature based on the technical specifications:

            Specifications: {requirements.get('specification')}

            Your implementation should include:
            1. Clean, production-ready code
            2. Proper error handling
            3. Unit tests
            4. Documentation (docstrings, comments)
            5. Git commits with descriptive messages

            Follow best practices for:
            - SOLID principles
            - Security (input validation, no SQL injection, XSS protection)
            - Performance
            - Maintainability
            """,
            expected_output="Implementation summary with file changes, test coverage, and commit details",
            agent=dev_agent,
        )

        # Execute task
        crew = Crew(agents=[dev_agent], tasks=[task], verbose=True)
        result = crew.kickoff()

        # Store results in state
        self.state.implementation = {
            "summary": str(result),
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Publish step completed event
        producer = await get_kafka_producer()
        event = FlowStepCompletedEvent(
            flow_id=self.state.flow_id,
            step_name="implement_feature",
            output=self.state.implementation,
            next_step="run_tests",
        )
        await producer.publish_flow_step_completed(event)

        return self.state.implementation

    @listen(implement_feature)
    async def run_tests(self, implementation: dict[str, Any]):
        """
        Step 3: Tester runs comprehensive tests

        Validates implementation against requirements
        """
        print(f"🧪 Step 3: Running Tests")

        # Create task for Tester
        tester_agent = get_tester_agent()

        task = Task(
            description=f"""
            Test the implemented feature comprehensively:

            Implementation: {implementation.get('summary')}

            Your testing should cover:
            1. Unit tests (verify all functions work correctly)
            2. Integration tests (verify components work together)
            3. Edge cases and error scenarios
            4. Security vulnerabilities (SQL injection, XSS, etc.)
            5. Performance (response times, memory usage)

            Run all tests and provide:
            - Test results summary
            - Code coverage percentage
            - List of bugs found (if any)
            - Recommendations for improvements
            """,
            expected_output="Comprehensive test report with results, coverage, and recommendations",
            agent=tester_agent,
        )

        # Execute task
        crew = Crew(agents=[tester_agent], tasks=[task], verbose=True)
        result = crew.kickoff()

        # Store results in state
        self.state.test_results = {
            "report": str(result),
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Publish step completed event
        producer = await get_kafka_producer()
        event = FlowStepCompletedEvent(
            flow_id=self.state.flow_id,
            step_name="run_tests",
            output=self.state.test_results,
            next_step="final_review",
        )
        await producer.publish_flow_step_completed(event)

        return self.state.test_results

    @listen(run_tests)
    async def final_review(self, test_results: dict[str, Any]):
        """
        Step 4: Team Leader performs final review

        Ensures quality and approves for deployment
        """
        print(f"✅ Step 4: Final Review")

        # Create task for Team Leader
        tl_agent = get_team_leader_agent()

        task = Task(
            description=f"""
            Perform a final review of the completed feature:

            Requirements: {self.state.requirements}
            Implementation: {self.state.implementation}
            Test Results: {test_results.get('report')}

            Your review should assess:
            1. Does the implementation meet all requirements?
            2. Is the code quality acceptable (clean, maintainable, documented)?
            3. Are tests comprehensive with good coverage?
            4. Are there any security concerns?
            5. Is it ready for production deployment?

            Provide:
            - Overall quality assessment
            - List of issues (if any)
            - Approval decision (approved/needs_revision)
            - Recommendations for future improvements
            """,
            expected_output="Final review report with approval decision",
            agent=tl_agent,
        )

        # Execute task
        crew = Crew(agents=[tl_agent], tasks=[task], verbose=True)
        result = crew.kickoff()

        # Store results in state
        self.state.final_review = {
            "report": str(result),
            "completed_at": datetime.utcnow().isoformat(),
        }

        # Mark flow as completed
        self.state.status = "completed"
        self.state.completed_at = datetime.utcnow()

        # Publish flow completed event
        producer = await get_kafka_producer()
        event = FlowCompletedEvent(
            flow_id=self.state.flow_id,
            final_state=self.state.model_dump(),
            total_execution_time_ms=int(
                (self.state.completed_at - self.state.started_at).total_seconds() * 1000
            ),
        )
        await producer.publish_flow_completed(event)

        print(f"🎉 Development Flow Completed: {self.state.flow_id}")

        return self.state.final_review


async def create_development_flow(
    project_id: UUID,
    feature_description: str,
    triggered_by: str
) -> DevelopmentFlow:
    """
    Create and initialize a development flow

    Args:
        project_id: Project UUID
        feature_description: Description of feature to implement
        triggered_by: User ID who triggered the flow

    Returns:
        Configured DevelopmentFlow instance
    """
    flow_id = str(uuid4())

    # Create flow instance - it manages its own state internally
    flow = DevelopmentFlow()

    # Initialize the state after creation
    flow.state.flow_id = flow_id
    flow.state.project_id = project_id
    flow.state.feature_description = feature_description
    flow.state.triggered_by = triggered_by
    flow.state.started_at = datetime.utcnow()
    flow.state.status = "in_progress"

    return flow
