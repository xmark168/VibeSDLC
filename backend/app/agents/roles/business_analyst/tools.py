"""Business Analyst custom tools for requirements → backlog workflow.

Tools for state management, solution design, documentation, and user interaction.
Adapted from fake/my_project to work with VibeSDLC database models.
"""

from crewai.tools import BaseTool
from typing import Type, Optional, Any, List
from pydantic import BaseModel, Field
from uuid import UUID
import json

from app.models import (
    BASession, Requirement, RequirementCategory,
    ProductBrief, BusinessFlow, Epic, Story,
    StoryPriority, StoryType, EpicStatus
)


# ==================== STATE MANAGER TOOL ====================

class StateToolInput(BaseModel):
    """Input schema for BAStateTool"""
    action: str = Field(
        ...,
        description="Action: 'add_requirement', 'add_requirements_batch', 'get_requirements', 'get_summary', 'check_complete'"
    )
    category: Optional[str] = Field(
        None,
        description="Category: 'problem_goals', 'users_stakeholders', or 'features_scope'"
    )
    content: Optional[str] = Field(None, description="Content for add_requirement")
    requirements: Optional[list] = Field(
        None,
        description="List of {category, content} dicts for batch add"
    )


class BAStateTool(BaseTool):
    """Tool to manage BA session state and requirements."""

    name: str = "State Manager Tool"
    description: str = """
    Tool to manage BA session state. Use this to:
    - Add single requirement: action='add_requirement', category='problem_goals|users_stakeholders|features_scope', content='requirement text'
    - Add multiple requirements (RECOMMENDED): action='add_requirements_batch', requirements=[{'category': 'problem_goals', 'content': 'req1'}, ...]
    - Get requirements: action='get_requirements', category='...' (or omit for all)
    - Get summary: action='get_summary'
    - Check if analysis complete: action='check_complete'
    """
    args_schema: Type[BaseModel] = StateToolInput

    # These will be set by the crew
    session: Any = Field(default=None, exclude=True)
    db_session: Any = Field(default=None, exclude=True)
    project_id: UUID = Field(default=None, exclude=True)

    def __init__(self, session: "BASession", db_session: Any, project_id: UUID, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'session', session)
        object.__setattr__(self, 'db_session', db_session)
        object.__setattr__(self, 'project_id', project_id)

    def _run(
        self,
        action: str,
        category: Optional[str] = None,
        content: Optional[str] = None,
        requirements: Optional[list] = None
    ) -> str:
        """Execute the tool action"""

        if action == "add_requirement":
            if not category or not content:
                return "Error: 'add_requirement' requires both 'category' and 'content'"

            try:
                cat_enum = RequirementCategory(category)
            except ValueError:
                return f"Error: Invalid category '{category}'. Valid: problem_goals, users_stakeholders, features_scope"

            # Create requirement in DB
            req = Requirement(
                session_id=self.session.id,
                project_id=self.project_id,
                category=cat_enum,
                content=content,
                turn_number=self.session.turn_count
            )
            self.db_session.add(req)
            self.db_session.commit()

            return f"Successfully added requirement to {category}: {content}"

        elif action == "add_requirements_batch":
            if not requirements or not isinstance(requirements, list):
                return "Error: 'add_requirements_batch' requires 'requirements' as a list"

            added_count = 0
            failed = []

            for req_dict in requirements:
                if not isinstance(req_dict, dict) or 'category' not in req_dict or 'content' not in req_dict:
                    failed.append(f"Invalid format: {req_dict}")
                    continue

                try:
                    cat_enum = RequirementCategory(req_dict['category'])
                    req = Requirement(
                        session_id=self.session.id,
                        project_id=self.project_id,
                        category=cat_enum,
                        content=req_dict['content'],
                        turn_number=self.session.turn_count
                    )
                    self.db_session.add(req)
                    added_count += 1
                except ValueError:
                    failed.append(f"Invalid category in: {req_dict}")

            self.db_session.commit()

            result = f"Batch add completed: {added_count} requirements added"
            if failed:
                result += f"\n{len(failed)} failed:\n" + "\n".join(failed)
            return result

        elif action == "get_requirements":
            # Query requirements from DB
            query = self.db_session.query(Requirement).filter(
                Requirement.session_id == self.session.id
            )

            if category:
                try:
                    cat_enum = RequirementCategory(category)
                    query = query.filter(Requirement.category == cat_enum)
                except ValueError:
                    return f"Error: Invalid category '{category}'"

            reqs = query.all()

            if not reqs:
                return f"No requirements found" + (f" in category: {category}" if category else "")

            # Format output
            if category:
                return f"Requirements in {category}:\n" + "\n".join(f"- {r.content}" for r in reqs)
            else:
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

        elif action == "get_summary":
            # Get conversation summary
            reqs = self.db_session.query(Requirement).filter(
                Requirement.session_id == self.session.id
            ).all()

            counts = {"problem_goals": 0, "users_stakeholders": 0, "features_scope": 0}
            for r in reqs:
                counts[r.category.value] += 1

            return f"""Requirements Summary:
- Problem/Goals: {counts['problem_goals']} items
- Users/Stakeholders: {counts['users_stakeholders']} items
- Features/Scope: {counts['features_scope']} items
- Total: {sum(counts.values())} requirements
- Conversation turns: {self.session.turn_count}"""

        elif action == "check_complete":
            # Check if analysis is complete
            reqs = self.db_session.query(Requirement).filter(
                Requirement.session_id == self.session.id
            ).all()

            counts = {"problem_goals": 0, "users_stakeholders": 0, "features_scope": 0}
            for r in reqs:
                counts[r.category.value] += 1

            total = sum(counts.values())

            # Completion criteria
            if (counts["problem_goals"] >= 1 and
                counts["users_stakeholders"] >= 1 and
                counts["features_scope"] >= 1 and
                total >= 5):
                status = "COMPLETE"
                reason = f"Sufficient: {counts['problem_goals']} goals, {counts['users_stakeholders']} stakeholders, {counts['features_scope']} features"
            elif (counts["problem_goals"] >= 2 and
                  counts["users_stakeholders"] >= 2 and
                  counts["features_scope"] >= 2):
                status = "COMPLETE"
                reason = f"All categories have 2+: {counts}"
            elif total >= 8:
                status = "COMPLETE"
                reason = f"Total of {total} requirements collected"
            else:
                status = "INCOMPLETE"
                missing = []
                if counts["problem_goals"] < 2:
                    missing.append(f"problem/goals ({counts['problem_goals']}/2)")
                if counts["users_stakeholders"] < 2:
                    missing.append(f"users/stakeholders ({counts['users_stakeholders']}/2)")
                if counts["features_scope"] < 2:
                    missing.append(f"features/scope ({counts['features_scope']}/2)")
                reason = f"Need more: {', '.join(missing)}"

            return f"Analysis Status: {status}\nReason: {reason}"

        else:
            return f"Error: Unknown action '{action}'"


# ==================== SOLUTION MANAGER TOOL ====================

class SolutionToolInput(BaseModel):
    """Input schema for BASolutionTool"""
    action: str = Field(
        ...,
        description="Action: 'add_flow', 'get_solution', 'get_summary', 'check_complete'"
    )
    component_data: Optional[str] = Field(
        None,
        description="JSON string of flow data"
    )


class BASolutionTool(BaseTool):
    """Tool to manage business flow solutions."""

    name: str = "Solution Manager Tool"
    description: str = """
    Tool to manage business flow solutions. Use this to:
    - Add business flow: action='add_flow', component_data='{"name": "...", "description": "...", "steps": [...], "actors": [...]}'
    - Get solution: action='get_solution'
    - Get summary: action='get_summary'
    - Check if solution complete: action='check_complete'
    """
    args_schema: Type[BaseModel] = SolutionToolInput

    session: Any = Field(default=None, exclude=True)
    db_session: Any = Field(default=None, exclude=True)
    project_id: UUID = Field(default=None, exclude=True)

    def __init__(self, session: "BASession", db_session: Any, project_id: UUID, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'session', session)
        object.__setattr__(self, 'db_session', db_session)
        object.__setattr__(self, 'project_id', project_id)

    def _run(self, action: str, component_data: Optional[str] = None) -> str:
        """Execute the tool action"""

        if action == "add_flow":
            if not component_data:
                return "Error: 'add_flow' requires 'component_data'"

            try:
                flow_data = json.loads(component_data)

                # Get current flow count for ordering
                flow_count = self.db_session.query(BusinessFlow).filter(
                    BusinessFlow.session_id == self.session.id
                ).count()

                flow = BusinessFlow(
                    session_id=self.session.id,
                    project_id=self.project_id,
                    name=flow_data.get('name', 'Unnamed Flow'),
                    description=flow_data.get('description', ''),
                    steps=flow_data.get('steps', []),
                    actors=flow_data.get('actors', []),
                    flow_order=flow_count + 1
                )
                self.db_session.add(flow)
                self.db_session.commit()

                return f"Successfully added business flow: {flow.name}"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON: {e}"

        elif action == "get_solution":
            flows = self.db_session.query(BusinessFlow).filter(
                BusinessFlow.session_id == self.session.id
            ).order_by(BusinessFlow.flow_order).all()

            if not flows:
                return "No business flows defined yet."

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

        elif action == "get_summary":
            flow_count = self.db_session.query(BusinessFlow).filter(
                BusinessFlow.session_id == self.session.id
            ).count()

            return f"Solution Components:\n- Business Flows: {flow_count} items"

        elif action == "check_complete":
            flow_count = self.db_session.query(BusinessFlow).filter(
                BusinessFlow.session_id == self.session.id
            ).count()

            if flow_count >= 2:
                status = "COMPLETE"
                reason = f"Solution has {flow_count} business flows"
            else:
                status = "INCOMPLETE"
                reason = f"Need more flows ({flow_count}, need at least 2)"

            return f"Solution Status: {status}\nReason: {reason}"

        else:
            return f"Error: Unknown action '{action}'"


# ==================== DOCUMENTATION MANAGER TOOL ====================

class DocumentationToolInput(BaseModel):
    """Input schema for BADocumentationTool"""
    action: str = Field(
        ...,
        description="Action: 'save_brief', 'get_brief', 'validate_brief', 'add_epic', 'add_story', 'get_documentation'"
    )
    data: Optional[str] = Field(None, description="JSON string of data")
    epic_id: Optional[str] = Field(None, description="Epic ID for story operations")


class BADocumentationTool(BaseTool):
    """Tool to manage Product Brief, Epics, and Stories."""

    name: str = "Documentation Manager Tool"
    description: str = """
    Tool to manage documentation. Use this to:
    - Save Product Brief: action='save_brief', data='{"product_summary": "...", "problem_statement": "...", "target_users": "...", "product_goals": "...", "scope": "..."}'
    - Get Product Brief: action='get_brief'
    - Validate Brief: action='validate_brief'
    - Add Epic: action='add_epic', data='{"id": "epic-1", "name": "...", "description": "...", "domain": "..."}'
    - Add Story: action='add_story', data='{"epic_id": "...", "title": "...", "description": "...", "acceptance_criteria": [...], "story_points": 3, "priority": "High", "dependencies": []}'
    - Get documentation: action='get_documentation'
    """
    args_schema: Type[BaseModel] = DocumentationToolInput

    session: Any = Field(default=None, exclude=True)
    db_session: Any = Field(default=None, exclude=True)
    project_id: UUID = Field(default=None, exclude=True)

    def __init__(self, session: "BASession", db_session: Any, project_id: UUID, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'session', session)
        object.__setattr__(self, 'db_session', db_session)
        object.__setattr__(self, 'project_id', project_id)

    def _run(self, action: str, data: Optional[str] = None, epic_id: Optional[str] = None) -> str:
        """Execute the tool action"""

        if action == "save_brief":
            if not data:
                return "Error: 'save_brief' requires 'data'"

            try:
                brief_data = json.loads(data)

                # Check if brief exists
                existing = self.db_session.query(ProductBrief).filter(
                    ProductBrief.session_id == self.session.id
                ).first()

                if existing:
                    # Update existing
                    existing.product_summary = brief_data.get("product_summary", "")
                    existing.problem_statement = brief_data.get("problem_statement", "")
                    existing.target_users = brief_data.get("target_users", "")
                    existing.product_goals = brief_data.get("product_goals", "")
                    existing.scope = brief_data.get("scope", "")
                    existing.revision_count = brief_data.get("revision_count", existing.revision_count + 1)
                else:
                    # Create new
                    brief = ProductBrief(
                        session_id=self.session.id,
                        project_id=self.project_id,
                        product_summary=brief_data.get("product_summary", ""),
                        problem_statement=brief_data.get("problem_statement", ""),
                        target_users=brief_data.get("target_users", ""),
                        product_goals=brief_data.get("product_goals", ""),
                        scope=brief_data.get("scope", ""),
                        revision_count=brief_data.get("revision_count", 0)
                    )
                    self.db_session.add(brief)

                self.db_session.commit()
                return "Successfully saved Product Brief"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON: {e}"

        elif action == "get_brief":
            brief = self.db_session.query(ProductBrief).filter(
                ProductBrief.session_id == self.session.id
            ).first()

            if not brief or not brief.product_summary:
                return "No Product Brief found"

            return json.dumps({
                "product_summary": brief.product_summary,
                "problem_statement": brief.problem_statement,
                "target_users": brief.target_users,
                "product_goals": brief.product_goals,
                "scope": brief.scope,
                "revision_count": brief.revision_count
            }, indent=2)

        elif action == "validate_brief":
            brief = self.db_session.query(ProductBrief).filter(
                ProductBrief.session_id == self.session.id
            ).first()

            if not brief:
                return "⚠️ No Product Brief found"

            missing = []
            if not brief.product_summary:
                missing.append("Product Summary")
            if not brief.problem_statement:
                missing.append("Problem Statement")
            if not brief.target_users:
                missing.append("Target Users")
            if not brief.product_goals:
                missing.append("Product Goals")
            if not brief.scope:
                missing.append("Scope")

            if missing:
                return f"⚠️ Product Brief INCOMPLETE. Missing:\n" + "\n".join(f"  - {m}" for m in missing)
            else:
                return "✅ Product Brief is complete"

        elif action == "add_epic":
            if not data:
                return "Error: 'add_epic' requires 'data'"

            try:
                epic_data = json.loads(data)

                epic = Epic(
                    project_id=self.project_id,
                    title=epic_data.get('name', 'Unnamed Epic'),
                    description=epic_data.get('description', ''),
                    domain=epic_data.get('domain', ''),
                    epic_status=EpicStatus.PLANNED
                )
                self.db_session.add(epic)
                self.db_session.commit()

                return f"Successfully added Epic: {epic.title} (ID: {epic.id})"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON: {e}"

        elif action == "add_story":
            if not data:
                return "Error: 'add_story' requires 'data'"

            try:
                story_data = json.loads(data)

                # Get epic if specified
                epic_uuid = None
                if story_data.get('epic_id') and story_data['epic_id'] != 'independent':
                    # Find epic by title match or UUID
                    epic = self.db_session.query(Epic).filter(
                        Epic.project_id == self.project_id,
                        Epic.title.contains(story_data['epic_id'])
                    ).first()
                    if epic:
                        epic_uuid = epic.id

                # Map priority
                priority_map = {"High": StoryPriority.HIGH, "Medium": StoryPriority.MEDIUM, "Low": StoryPriority.LOW}
                story_priority = priority_map.get(story_data.get('priority', 'Medium'), StoryPriority.MEDIUM)

                story = Story(
                    project_id=self.project_id,
                    epic_id=epic_uuid,
                    type=StoryType.USER_STORY,
                    title=story_data.get('title', 'Untitled Story'),
                    description=story_data.get('description', ''),
                    acceptance_criteria="\n".join(story_data.get('acceptance_criteria', [])),
                    story_point=story_data.get('story_points', 3),
                    story_priority=story_priority,
                    dependencies=story_data.get('dependencies', [])
                )
                self.db_session.add(story)
                self.db_session.commit()

                return f"Successfully added Story: {story.title}"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON: {e}"

        elif action == "get_documentation":
            # Get brief
            brief = self.db_session.query(ProductBrief).filter(
                ProductBrief.session_id == self.session.id
            ).first()

            # Get epics and stories
            epics = self.db_session.query(Epic).filter(
                Epic.project_id == self.project_id
            ).all()

            stories = self.db_session.query(Story).filter(
                Story.project_id == self.project_id
            ).all()

            text = []

            # Brief section
            if brief and brief.product_summary:
                text.append("# PRODUCT BRIEF\n")
                text.append(f"## Product Summary\n{brief.product_summary}\n")
                text.append(f"## Problem Statement\n{brief.problem_statement}\n")
                text.append(f"## Target Users\n{brief.target_users}\n")
                text.append(f"## Product Goals\n{brief.product_goals}\n")
                text.append(f"## Scope\n{brief.scope}\n")

            # Backlog section
            if epics or stories:
                text.append("\n# PRODUCT BACKLOG\n")

                if epics:
                    text.append("## Epics\n")
                    for epic in epics:
                        text.append(f"### {epic.title}")
                        text.append(f"**Domain:** {epic.domain or 'N/A'}")
                        text.append(f"**Description:** {epic.description or 'N/A'}")

                        # Stories for this epic
                        epic_stories = [s for s in stories if s.epic_id == epic.id]
                        if epic_stories:
                            text.append(f"\n**Stories ({len(epic_stories)}):**")
                            for story in epic_stories:
                                text.append(f"- {story.title} [{story.story_point}pts, {story.story_priority.value if story.story_priority else 'Medium'}]")
                        text.append("")

            return "\n".join(text) if text else "No documentation created yet."

        else:
            return f"Error: Unknown action '{action}'"


# ==================== USER INTERACTION TOOL ====================

class UserInteractionInput(BaseModel):
    """Input schema for BAUserInteractionTool"""
    action: str = Field(
        ...,
        description="Action: 'present_options', 'get_last_choice', 'check_pending'"
    )
    question: Optional[str] = Field(None, description="Question to ask")
    options: Optional[str] = Field(None, description="JSON list of options")
    context: Optional[str] = Field(None, description="Context for the question")


class BAUserInteractionTool(BaseTool):
    """Tool for interactive user questions (choices/options)."""

    name: str = "User Interaction Tool"
    description: str = """
    Tool for user interaction. Use this to:
    - Present options: action='present_options', question='Which framework?', options='[{"label": "React", "value": "react", "description": "..."}]', context='frontend'
    - Get last choice: action='get_last_choice', context='frontend'
    - Check pending: action='check_pending'
    """
    args_schema: Type[BaseModel] = UserInteractionInput

    session: Any = Field(default=None, exclude=True)
    db_session: Any = Field(default=None, exclude=True)

    def __init__(self, session: "BASession", db_session: Any, **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, 'session', session)
        object.__setattr__(self, 'db_session', db_session)

    def _run(
        self,
        action: str,
        question: Optional[str] = None,
        options: Optional[str] = None,
        context: Optional[str] = None
    ) -> str:
        """Execute the tool action"""

        # Get or initialize session metadata
        metadata = self.session.session_metadata or {}

        if action == "present_options":
            if not question or not options:
                return "Error: 'present_options' requires 'question' and 'options'"

            try:
                options_list = json.loads(options)

                if not isinstance(options_list, list) or len(options_list) < 2:
                    return "Error: 'options' must have at least 2 items"

                # Store pending question in metadata
                metadata['pending_question'] = {
                    "question": question,
                    "options": options_list,
                    "context": context or "general"
                }
                self.session.session_metadata = metadata
                self.db_session.commit()

                return f"SUCCESS: Question prepared.\nQuestion: {question}\nOptions: {len(options_list)} choices"
            except json.JSONDecodeError as e:
                return f"Error: Invalid JSON: {e}"

        elif action == "get_last_choice":
            choices = metadata.get('user_choices', [])

            if not choices:
                return "No user choices recorded yet."

            if context:
                matching = [c for c in reversed(choices) if c.get('context') == context]
                if matching:
                    choice = matching[0]
                    return f"Last choice for '{context}': {choice.get('selected_label')} (value: {choice.get('selected_value')})"
                else:
                    return f"No choices found for context: {context}"
            else:
                choice = choices[-1]
                return f"Most recent choice: {choice.get('selected_label')} (context: {choice.get('context')})"

        elif action == "check_pending":
            pending = metadata.get('pending_question')
            if pending:
                return f"PENDING: {pending.get('question')}\nContext: {pending.get('context')}\nOptions: {len(pending.get('options', []))} choices"
            else:
                return "No pending questions."

        else:
            return f"Error: Unknown action '{action}'"


# ==================== TOOL FACTORY ====================

def get_ba_tools(session: "BASession", db_session: Any, project_id: UUID) -> list:
    """Get list of tools for Business Analyst workflow.

    Args:
        session: Current BA session
        db_session: Database session
        project_id: Project UUID

    Returns:
        List of CrewAI Tool instances
    """
    return [
        BAStateTool(session=session, db_session=db_session, project_id=project_id),
        BASolutionTool(session=session, db_session=db_session, project_id=project_id),
        BADocumentationTool(session=session, db_session=db_session, project_id=project_id),
        BAUserInteractionTool(session=session, db_session=db_session),
    ]
