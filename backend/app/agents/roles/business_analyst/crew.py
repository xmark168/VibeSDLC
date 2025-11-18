"""Business Analyst Crew - Multi-phase requirements → backlog workflow.

This crew orchestrates the complete BA workflow:
1. Analysis Phase: Gather requirements via conversation
2. Brief Phase: Create Product Brief from requirements
3. Solution Phase: Design business flows
4. Backlog Phase: Create Epics & User Stories
"""

import logging
import yaml
import re
from pathlib import Path
from typing import Any, Dict, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from crewai import Agent, Task, Crew
from sqlmodel import Session

from app.agents.roles.base_crew import BaseAgentCrew
from app.agents.roles.business_analyst.tools import get_ba_tools
from app.models import (
    BASession, BASessionStatus, Requirement, RequirementCategory,
    ProductBrief, BusinessFlow, Epic, Story,
    EpicStatus, StoryType, StoryPriority
)
from app.core.config import settings

# Import Pydantic models for structured outputs
from pydantic import BaseModel, Field
from typing import List as ListType

logger = logging.getLogger(__name__)


# ==================== PYDANTIC OUTPUT MODELS ====================

class FlowDesign(BaseModel):
    """Single business flow design"""
    name: str
    description: str
    steps: ListType[str]
    actors: ListType[str]


class FlowsOutput(BaseModel):
    """Output model for flows design task"""
    business_flows: ListType[FlowDesign]


class ProductBriefData(BaseModel):
    """Product Brief document structure"""
    product_summary: str
    problem_statement: str
    target_users: str
    product_goals: str
    scope: str
    revision_count: int = 0


class EpicData(BaseModel):
    """Single Epic structure"""
    id: str
    name: str
    description: str
    domain: str


class StoryData(BaseModel):
    """Single User Story structure"""
    epic_id: str
    title: str
    description: str
    acceptance_criteria: ListType[str]
    story_points: int
    priority: str = "Medium"
    dependencies: ListType[str] = []


class BacklogOutput(BaseModel):
    """Combined output for backlog creation"""
    epics: ListType[EpicData]
    stories: ListType[StoryData]


# ==================== BUSINESS ANALYST CREW ====================

class BusinessAnalystCrew(BaseAgentCrew):
    """Business Analyst Crew - multi-phase workflow from requirements to backlog.

    Workflow Phases:
    1. ANALYSIS: Gather requirements through conversation
    2. BRIEF: Create Product Brief from requirements
    3. SOLUTION: Design business flows
    4. BACKLOG: Create Epics & User Stories
    """

    def __init__(self, config_path: Optional[Path] = None, db_session: Session = None):
        super().__init__(config_path)
        self.db_session = db_session
        self.ba_session: Optional[BASession] = None
        self.project_id: Optional[UUID] = None

        # Load agents and tasks configs
        self._load_ba_configs()

    def _load_ba_configs(self):
        """Load agents.yaml and tasks.yaml configurations."""
        config_dir = Path(__file__).parent

        # Load agents config
        agents_path = config_dir / "agents.yaml"
        if agents_path.exists():
            with open(agents_path, "r", encoding="utf-8") as f:
                self.agents_config = yaml.safe_load(f)
        else:
            self.agents_config = {}
            logger.warning(f"agents.yaml not found at {agents_path}")

        # Load tasks config
        tasks_path = config_dir / "tasks.yaml"
        if tasks_path.exists():
            with open(tasks_path, "r", encoding="utf-8") as f:
                self.tasks_config = yaml.safe_load(f)
        else:
            self.tasks_config = {}
            logger.warning(f"tasks.yaml not found at {tasks_path}")

    @property
    def crew_name(self) -> str:
        return "Business Analyst"

    @property
    def agent_type(self) -> str:
        return "business_analyst"

    def _get_default_config_path(self) -> Path:
        """Get default config path."""
        return Path(__file__).parent / "config.yaml"

    # ==================== AGENT CREATION ====================

    def _create_agent_from_config(self, agent_name: str, tools: list = None) -> Agent:
        """Create an agent from agents.yaml config.

        Args:
            agent_name: Name of agent in agents.yaml
            tools: Optional list of tools for the agent

        Returns:
            Configured CrewAI Agent
        """
        config = self.agents_config.get(agent_name, {})

        # Get model from settings (with fallback)
        model = settings.STRONG_MODEL or settings.MODEL or "openai/gpt-4.1"
        logger.info(f"Using model: {model}")

        return Agent(
            role=config.get("role", agent_name.replace("_", " ").title()),
            goal=config.get("goal", ""),
            backstory=config.get("backstory", ""),
            verbose=True,
            allow_delegation=False,
            tools=tools or [],
            llm=model,
        )

    def create_agent(self) -> Agent:
        """Create the main Business Analyst agent.

        Returns:
            Configured CrewAI Agent
        """
        tools = []
        if self.ba_session and self.db_session:
            tools = get_ba_tools(
                session=self.ba_session,
                db_session=self.db_session,
                project_id=self.project_id
            )

        self.agent = self._create_agent_from_config("business_analyst", tools)
        return self.agent

    # ==================== SESSION MANAGEMENT ====================

    def create_session(self, project_id: UUID, user_id: UUID) -> BASession:
        """Create a new BA session for the workflow.

        Args:
            project_id: Project UUID
            user_id: User UUID

        Returns:
            New BASession
        """
        self.project_id = project_id

        self.ba_session = BASession(
            project_id=project_id,
            user_id=user_id,
            status=BASessionStatus.ANALYSIS,
            current_phase="analysis",
            conversation_history=[],
            turn_count=0,
            phase_transitions=[],
            session_metadata={}
        )

        self.db_session.add(self.ba_session)
        self.db_session.commit()
        self.db_session.refresh(self.ba_session)

        logger.info(f"Created BA session {self.ba_session.id} for project {project_id}")
        return self.ba_session

    def load_session(self, session_id: UUID) -> BASession:
        """Load an existing BA session.

        Args:
            session_id: Session UUID

        Returns:
            Loaded BASession
        """
        self.ba_session = self.db_session.query(BASession).filter(
            BASession.id == session_id
        ).first()

        if self.ba_session:
            self.project_id = self.ba_session.project_id

        return self.ba_session

    def _transition_phase(self, new_phase: str, reason: str = ""):
        """Transition to a new phase.

        Args:
            new_phase: Target phase
            reason: Reason for transition
        """
        old_phase = self.ba_session.current_phase

        transition = {
            "from": old_phase,
            "to": new_phase,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        transitions = self.ba_session.phase_transitions or []
        transitions.append(transition)
        self.ba_session.phase_transitions = transitions
        self.ba_session.current_phase = new_phase

        # Update status
        status_map = {
            "analysis": BASessionStatus.ANALYSIS,
            "brief": BASessionStatus.BRIEF,
            "solution": BASessionStatus.SOLUTION,
            "backlog": BASessionStatus.BACKLOG,
            "completed": BASessionStatus.COMPLETED
        }
        self.ba_session.status = status_map.get(new_phase, BASessionStatus.ANALYSIS)

        self.db_session.commit()
        logger.info(f"Phase transition: {old_phase} → {new_phase}")

    # ==================== TASK CREATION ====================

    def create_tasks(self, context: Dict[str, Any]) -> List[Task]:
        """Create tasks based on current phase.

        Args:
            context: Execution context

        Returns:
            List of tasks for current phase
        """
        if self.agent is None:
            self.create_agent()

        phase = context.get("phase", "analysis")

        if phase == "analysis":
            return [self._create_analysis_task(context)]
        elif phase == "brief":
            return [self._create_brief_task(context)]
        elif phase == "solution":
            return [self._create_solution_task(context)]
        elif phase == "backlog":
            return [self._create_backlog_task(context)]
        else:
            return [self._create_analysis_task(context)]

    def _create_analysis_task(self, context: Dict[str, Any]) -> Task:
        """Create requirements analysis task."""
        task_config = self.tasks_config.get("analysis_task", {})

        # Refresh session from database to get latest conversation
        if self.ba_session:
            self.db_session.refresh(self.ba_session)

        # Build conversation context
        conversation_context = self._get_conversation_context()

        description = task_config.get("description", "").format(
            conversation_context=conversation_context,
            user_message=context.get("user_message", ""),
            turn_count=self.ba_session.turn_count if self.ba_session else 0,
            total_requirements=self._get_requirements_count()
        )

        return Task(
            description=description,
            expected_output=task_config.get("expected_output", ""),
            agent=self._create_agent_from_config(
                "business_analyst",
                get_ba_tools(self.ba_session, self.db_session, self.project_id) if self.ba_session else []
            )
        )

    def _create_brief_task(self, context: Dict[str, Any]) -> Task:
        """Create Product Brief creation task."""
        task_config = self.tasks_config.get("product_brief_creation_task", {})

        requirements_summary = self._get_requirements_summary()
        current_brief = context.get("current_brief", "None")
        revision_feedback = context.get("revision_feedback", "None")

        description = task_config.get("description", "").format(
            requirements_summary=requirements_summary,
            current_brief=current_brief,
            revision_feedback=revision_feedback
        )

        return Task(
            description=description,
            expected_output=task_config.get("expected_output", ""),
            agent=self._create_agent_from_config(
                "product_brief_writer",
                get_ba_tools(self.ba_session, self.db_session, self.project_id) if self.ba_session else []
            ),
            output_pydantic=ProductBriefData
        )

    def _create_solution_task(self, context: Dict[str, Any]) -> Task:
        """Create solution design task."""
        task_config = self.tasks_config.get("solution_design_flows_task", {})

        product_brief = self._get_product_brief_text()
        requirements_summary = self._get_requirements_summary()
        current_solution = context.get("current_solution", "None")
        revision_feedback = context.get("revision_feedback", "None")

        description = task_config.get("description", "").format(
            product_brief=product_brief,
            requirements_summary=requirements_summary,
            current_solution=current_solution,
            revision_feedback=revision_feedback
        )

        return Task(
            description=description,
            expected_output=task_config.get("expected_output", ""),
            agent=self._create_agent_from_config(
                "solution_designer",
                get_ba_tools(self.ba_session, self.db_session, self.project_id) if self.ba_session else []
            ),
            output_pydantic=FlowsOutput
        )

    def _create_backlog_task(self, context: Dict[str, Any]) -> Task:
        """Create backlog (Epics & Stories) task."""
        task_config = self.tasks_config.get("epic_story_creation_task", {})

        product_brief = self._get_product_brief_text()
        solution_summary = self._get_solution_summary()
        current_backlog = context.get("current_backlog", "None")
        revision_feedback = context.get("revision_feedback", "None")

        description = task_config.get("description", "").format(
            product_brief=product_brief,
            solution_summary=solution_summary,
            current_backlog=current_backlog,
            revision_feedback=revision_feedback
        )

        return Task(
            description=description,
            expected_output=task_config.get("expected_output", ""),
            agent=self._create_agent_from_config(
                "epic_story_writer",
                get_ba_tools(self.ba_session, self.db_session, self.project_id) if self.ba_session else []
            ),
            output_pydantic=BacklogOutput
        )

    # ==================== HELPER METHODS ====================

    def _get_conversation_context(self) -> str:
        """Get formatted conversation history."""
        if not self.ba_session or not self.ba_session.conversation_history:
            return "No previous conversation."

        history = self.ba_session.conversation_history[-10:]  # Last 10 messages
        formatted = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}")

        return "\n".join(formatted)

    def _get_requirements_count(self) -> int:
        """Get total requirements count."""
        if not self.ba_session:
            return 0

        return self.db_session.query(Requirement).filter(
            Requirement.session_id == self.ba_session.id
        ).count()

    def _get_requirements_summary(self) -> str:
        """Get formatted requirements summary."""
        if not self.ba_session:
            return "No requirements collected."

        reqs = self.db_session.query(Requirement).filter(
            Requirement.session_id == self.ba_session.id
        ).all()

        if not reqs:
            return "No requirements collected."

        # Group by category
        grouped = {}
        for r in reqs:
            cat = r.category.value
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(r.content)

        text = []
        for cat, items in grouped.items():
            text.append(f"## {cat.replace('_', ' ').title()}")
            for i, item in enumerate(items, 1):
                text.append(f"{i}. {item}")
            text.append("")

        return "\n".join(text)

    def _get_product_brief_text(self) -> str:
        """Get formatted Product Brief."""
        if not self.ba_session:
            return "No Product Brief created."

        brief = self.db_session.query(ProductBrief).filter(
            ProductBrief.session_id == self.ba_session.id
        ).first()

        if not brief or not brief.product_summary:
            return "No Product Brief created."

        return f"""# PRODUCT BRIEF

## Product Summary
{brief.product_summary}

## Problem Statement
{brief.problem_statement}

## Target Users
{brief.target_users}

## Product Goals
{brief.product_goals}

## Scope
{brief.scope}
"""

    def _get_solution_summary(self) -> str:
        """Get formatted solution (business flows)."""
        if not self.ba_session:
            return "No solution designed."

        flows = self.db_session.query(BusinessFlow).filter(
            BusinessFlow.session_id == self.ba_session.id
        ).order_by(BusinessFlow.flow_order).all()

        if not flows:
            return "No business flows designed."

        text = ["## Business Flows"]
        for i, flow in enumerate(flows, 1):
            text.append(f"\n### {i}. {flow.name}")
            text.append(f"**Description:** {flow.description}")
            if flow.steps:
                text.append("**Steps:**")
                for j, step in enumerate(flow.steps, 1):
                    text.append(f"  {j}. {step}")
            if flow.actors:
                text.append(f"**Actors:** {', '.join(flow.actors)}")

        return "\n".join(text)

    # ==================== PHASE EXECUTION ====================

    async def execute_analysis(
        self,
        user_message: str,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute analysis phase - process user message and extract requirements.

        Args:
            user_message: User's input message
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Analysis result with extracted requirements and response
        """
        # Ensure session exists
        if not self.ba_session:
            self.create_session(project_id, user_id)

        # Add user message to history
        history = self.ba_session.conversation_history or []
        history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.ba_session.conversation_history = history
        self.ba_session.turn_count += 1
        self.db_session.commit()
        self.db_session.refresh(self.ba_session)  # Refresh to ensure data is synced

        # Execute analysis task
        context = {
            "phase": "analysis",
            "user_message": user_message,
        }

        # CRITICAL: Reset crew to force task recreation with updated context
        # Without this, the crew caches old tasks with stale conversation data
        self.reset()

        result = await self.execute(context, project_id, user_id)

        # Parse and store requirements from result
        if result.get("success"):
            output = result.get("output", "")
            extracted = self._parse_analysis_output(output)

            # Add assistant response to history
            history = self.ba_session.conversation_history or []
            history.append({
                "role": "assistant",
                "content": extracted.get("response", ""),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.ba_session.conversation_history = history
            self.db_session.commit()

            result["extracted_requirements"] = extracted.get("requirements", {})
            result["assistant_response"] = extracted.get("response", "")

        return result

    def _parse_analysis_output(self, output: str) -> Dict[str, Any]:
        """Parse analysis task output to extract requirements and response.

        Args:
            output: Raw task output

        Returns:
            Dict with requirements and response
        """
        result = {
            "requirements": {
                "problem_goals": [],
                "users_stakeholders": [],
                "features_scope": []
            },
            "response": ""
        }

        # Extract requirements section
        req_match = re.search(
            r'=== EXTRACTED REQUIREMENTS ===(.*?)=== END REQUIREMENTS ===',
            output,
            re.DOTALL
        )

        if req_match:
            req_text = req_match.group(1)

            # Parse each category
            for category in ["PROBLEM_GOALS", "USERS_STAKEHOLDERS", "FEATURES_SCOPE"]:
                pattern = rf'{category}:\s*((?:- .*\n?)*)'
                cat_match = re.search(pattern, req_text)
                if cat_match:
                    items = re.findall(r'- (.+)', cat_match.group(1))
                    key = category.lower()
                    result["requirements"][key] = items

                    # Save to database
                    for item in items:
                        if item.strip():
                            req = Requirement(
                                session_id=self.ba_session.id,
                                project_id=self.project_id,
                                category=RequirementCategory(key),
                                content=item.strip(),
                                turn_number=self.ba_session.turn_count
                            )
                            self.db_session.add(req)

            self.db_session.commit()

        # Extract response section
        resp_match = re.search(
            r'=== USER RESPONSE ===(.*?)=== END RESPONSE ===',
            output,
            re.DOTALL
        )

        if resp_match:
            result["response"] = resp_match.group(1).strip()

        return result

    async def execute_brief_phase(
        self,
        revision_feedback: str = None,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute brief phase - create Product Brief.

        Args:
            revision_feedback: Optional feedback for revision
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Result with Product Brief
        """
        if self.ba_session.current_phase == "analysis":
            self._transition_phase("brief", "Analysis complete, creating Product Brief")

        # Get current brief if it exists (for refinement mode)
        current_brief_text = "None"
        if revision_feedback:
            existing_brief = self.db_session.query(ProductBrief).filter(
                ProductBrief.session_id == self.ba_session.id
            ).first()

            if existing_brief and existing_brief.product_summary:
                # Format current brief for agent to refine
                current_brief_text = f"""Product Summary: {existing_brief.product_summary}

Problem Statement:
{existing_brief.problem_statement}

Target Users:
{existing_brief.target_users}

Product Goals:
{existing_brief.product_goals}

Scope:
{existing_brief.scope}

Revision Count: {existing_brief.revision_count}"""

        context = {
            "phase": "brief",
            "current_brief": current_brief_text,
            "revision_feedback": revision_feedback or "None",
        }

        # Reset crew to force task recreation
        self.reset()

        result = await self.execute(context, project_id, user_id)

        # Save brief to database
        if result.get("success") and result.get("pydantic"):
            brief_data = result["pydantic"]

            # Check if brief exists
            existing = self.db_session.query(ProductBrief).filter(
                ProductBrief.session_id == self.ba_session.id
            ).first()

            if existing:
                existing.product_summary = brief_data.product_summary
                existing.problem_statement = brief_data.problem_statement
                existing.target_users = brief_data.target_users
                existing.product_goals = brief_data.product_goals
                existing.scope = brief_data.scope
                existing.revision_count = brief_data.revision_count
            else:
                brief = ProductBrief(
                    session_id=self.ba_session.id,
                    project_id=self.project_id,
                    product_summary=brief_data.product_summary,
                    problem_statement=brief_data.problem_statement,
                    target_users=brief_data.target_users,
                    product_goals=brief_data.product_goals,
                    scope=brief_data.scope,
                    revision_count=brief_data.revision_count
                )
                self.db_session.add(brief)

            self.db_session.commit()

        return result

    async def execute_solution_phase(
        self,
        revision_feedback: str = None,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute solution phase - design business flows.

        Args:
            revision_feedback: Optional feedback for revision
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Result with business flows
        """
        if self.ba_session.current_phase == "brief":
            self._transition_phase("solution", "Brief approved, designing solution")

        # Get current solution if it exists (for refinement mode)
        current_solution_text = "None"
        if revision_feedback:
            existing_flows = self.db_session.query(BusinessFlow).filter(
                BusinessFlow.session_id == self.ba_session.id
            ).order_by(BusinessFlow.flow_order).all()

            if existing_flows:
                # Format current solution for agent to refine
                flow_texts = []
                for i, flow in enumerate(existing_flows, 1):
                    flow_text = f"""Flow {i}: {flow.name}
Description: {flow.description}
Steps:
{chr(10).join(f"  {j}. {step}" for j, step in enumerate(flow.steps, 1))}
Actors: {', '.join(flow.actors)}"""
                    flow_texts.append(flow_text)

                current_solution_text = "\n\n".join(flow_texts)

        context = {
            "phase": "solution",
            "current_solution": current_solution_text,
            "revision_feedback": revision_feedback or "None",
        }

        # Reset crew to force task recreation
        self.reset()

        result = await self.execute(context, project_id, user_id)

        # Save flows to database
        if result.get("success") and result.get("pydantic"):
            flows_output = result["pydantic"]

            # Clear existing flows for revision
            self.db_session.query(BusinessFlow).filter(
                BusinessFlow.session_id == self.ba_session.id
            ).delete()

            # Add new flows
            for i, flow_data in enumerate(flows_output.business_flows, 1):
                flow = BusinessFlow(
                    session_id=self.ba_session.id,
                    project_id=self.project_id,
                    name=flow_data.name,
                    description=flow_data.description,
                    steps=flow_data.steps,
                    actors=flow_data.actors,
                    flow_order=i
                )
                self.db_session.add(flow)

            self.db_session.commit()

        return result

    async def execute_backlog_phase(
        self,
        revision_feedback: str = None,
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute backlog phase - create Epics & Stories.

        Args:
            revision_feedback: Optional feedback for revision
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Result with Epics and Stories
        """
        if self.ba_session.current_phase == "solution":
            self._transition_phase("backlog", "Solution approved, creating backlog")

        # Get current backlog if it exists (for refinement mode)
        current_backlog_text = "None"
        if revision_feedback:
            existing_epics = self.db_session.query(Epic).filter(
                Epic.project_id == self.project_id
            ).all()

            existing_stories = self.db_session.query(Story).filter(
                Story.project_id == self.project_id
            ).all()

            if existing_epics or existing_stories:
                # Format current backlog for agent to refine
                backlog_parts = []

                if existing_epics:
                    backlog_parts.append("EPICS:")
                    for epic in existing_epics:
                        epic_text = f"""- {epic.title}
  Domain: {epic.domain or 'N/A'}
  Description: {epic.description or 'N/A'}"""
                        backlog_parts.append(epic_text)

                if existing_stories:
                    backlog_parts.append("\nSTORIES:")
                    for story in existing_stories:
                        epic_name = "Independent"
                        if story.epic_id:
                            epic = next((e for e in existing_epics if e.id == story.epic_id), None)
                            if epic:
                                epic_name = epic.title

                        story_text = f"""- {story.title}
  Epic: {epic_name}
  Points: {story.story_point}, Priority: {story.story_priority.value if story.story_priority else 'Medium'}
  Acceptance Criteria: {story.acceptance_criteria or 'N/A'}"""
                        backlog_parts.append(story_text)

                current_backlog_text = "\n".join(backlog_parts)

        context = {
            "phase": "backlog",
            "current_backlog": current_backlog_text,
            "revision_feedback": revision_feedback or "None",
        }

        # Reset crew to force task recreation
        self.reset()

        result = await self.execute(context, project_id, user_id)

        # Save epics and stories to database
        if result.get("success") and result.get("pydantic"):
            backlog = result["pydantic"]

            # Create epics
            epic_id_map = {}  # Map temp IDs to real IDs
            for epic_data in backlog.epics:
                epic = Epic(
                    project_id=self.project_id,
                    title=epic_data.name,
                    description=epic_data.description,
                    domain=epic_data.domain,
                    epic_status=EpicStatus.PLANNED
                )
                self.db_session.add(epic)
                self.db_session.flush()  # Get the ID
                epic_id_map[epic_data.id] = epic.id

            # Create stories
            for story_data in backlog.stories:
                # Map epic ID
                epic_uuid = epic_id_map.get(story_data.epic_id)

                # Map priority
                priority_map = {
                    "High": StoryPriority.HIGH,
                    "Medium": StoryPriority.MEDIUM,
                    "Low": StoryPriority.LOW
                }

                story = Story(
                    project_id=self.project_id,
                    epic_id=epic_uuid,
                    type=StoryType.USER_STORY,
                    title=story_data.title,
                    description=story_data.description,
                    acceptance_criteria="\n".join(story_data.acceptance_criteria),
                    story_point=story_data.story_points,
                    story_priority=priority_map.get(story_data.priority, StoryPriority.MEDIUM),
                    dependencies=story_data.dependencies
                )
                self.db_session.add(story)

            self.db_session.commit()

            # Mark session complete
            self._transition_phase("completed", "Backlog created successfully")
            self.ba_session.completed_at = datetime.now(timezone.utc)
            self.db_session.commit()

        return result

    async def execute(
        self,
        context: Dict[str, Any],
        project_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Execute BA workflow based on context phase.

        Args:
            context: Execution context with phase info
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Execution result
        """
        # Store project_id
        if project_id:
            self.project_id = project_id

        # Execute base workflow
        result = await super().execute(context, project_id, user_id)

        if result.get("success"):
            phase = context.get("phase", "analysis")

            # Publish response via Kafka
            await self.publish_response(
                content=result.get("output", ""),
                message_id=context.get("message_id", UUID(int=0)),
                project_id=project_id,
                user_id=user_id,
                structured_data={
                    "phase": phase,
                    "session_id": str(self.ba_session.id) if self.ba_session else None,
                },
            )

            logger.info(f"BA Crew completed {phase} phase")

        return result
