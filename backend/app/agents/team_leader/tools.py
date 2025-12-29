"""Team Leader Tools - LangChain tools for on-demand context loading."""

import logging
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_kanban_service():
    """Get KanbanService instance with session."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.services import KanbanService
    
    session = Session(engine)
    return KanbanService(session), session


@tool
def get_board_status(project_id: str) -> str:
    """Get Kanban board status: WIP counts, limits, available slots.
    
    Call this when you need to:
    - Check capacity before delegating work to developer/tester
    - Answer questions about board status or progress
    - Determine if WIP limits allow new work
    
    Args:
        project_id: The project UUID
        
    Returns:
        Board status with WIP counts and availability
    """
    try:
        kanban_service, session = _get_kanban_service()
        
        with session:
            wip_data = kanban_service.get_dynamic_wip_with_usage(UUID(project_id))
            
            lines = []
            for col in ["InProgress", "Review", "Done"]:
                if col in wip_data:
                    data = wip_data[col]
                    current = data.get("current_stories", 0)
                    limit = data.get("limit", "N/A")
                    available = data.get("available", 0)
                    
                    if col == "Done":
                        lines.append(f"- {col}: {current} stories completed")
                    else:
                        status = "FULL" if available <= 0 else f"{available} slots available"
                        lines.append(f"- {col}: {current}/{limit} ({status})")
            
            return "Board Status:\n" + "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_board_status] Error: {e}")
        return f"Error fetching board status: {str(e)}"


@tool
def get_active_stories(project_id: str) -> str:
    """Get stories currently in progress with assignees.
    
    Call this when you need to:
    - See what work is being done
    - Check who is working on what
    - Get context about current tasks
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of active stories with title, assignee, and status
    """
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Story, StoryStatus, User
        
        with Session(engine) as session:
            stories = session.exec(
                select(Story)
                .where(Story.project_id == UUID(project_id))
                .where(Story.status.in_([StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]))
                .order_by(Story.updated_at.desc())
                .limit(10)
            ).all()
            
            if not stories:
                return "No active stories in progress."
            
            lines = ["Active Stories:"]
            for s in stories:
                assignee_name = "Unassigned"
                if s.assignee_id:
                    assignee = session.get(User, s.assignee_id)
                    if assignee:
                        assignee_name = assignee.full_name or assignee.email
                
                lines.append(f"- [{s.status.value}] {s.title} (Assignee: {assignee_name})")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_active_stories] Error: {e}")
        return f"Error fetching active stories: {str(e)}"


@tool
def search_stories(project_id: str, query: str) -> str:
    """Search stories by title, ID, or keyword.
    
    Call this when:
    - User mentions a specific story by name or ID
    - Need to find stories related to a feature
    - Looking for specific work items
    
    Args:
        project_id: The project UUID
        query: Search query (story title, ID like "#123", or keyword)
        
    Returns:
        Matching stories with details
    """
    try:
        from sqlmodel import Session, select, or_
        from app.core.db import engine
        from app.models import Story
        
        with Session(engine) as session:
            # Handle ID search (e.g., "#123" or "123")
            story_id = query.replace("#", "").strip()
            
            stmt = select(Story).where(Story.project_id == UUID(project_id))
            
            # Try UUID search first
            try:
                uuid_query = UUID(story_id)
                stmt = stmt.where(Story.id == uuid_query)
            except (ValueError, AttributeError):
                # Fall back to title search
                stmt = stmt.where(Story.title.ilike(f"%{query}%"))
            
            stories = session.exec(stmt.limit(5)).all()
            
            if not stories:
                return f"No stories found matching '{query}'"
            
            lines = [f"Stories matching '{query}':"]
            for s in stories:
                lines.append(f"- [{s.status.value}] {s.title}")
                if s.description:
                    lines.append(f"  Description: {s.description[:100]}...")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[search_stories] Error: {e}")
        return f"Error searching stories: {str(e)}"


@tool
def get_blocked_items(project_id: str) -> str:
    """Get stories that are blocked and need attention.
    
    Call this when:
    - Need to identify bottlenecks
    - Checking for impediments
    - Prioritizing unblocking work
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of blocked stories with reasons
    """
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Story
        
        with Session(engine) as session:
            # Stories with is_blocked flag or stuck too long
            stories = session.exec(
                select(Story)
                .where(Story.project_id == UUID(project_id))
                .where(Story.is_blocked == True)
                .limit(10)
            ).all()
            
            if not stories:
                return "No blocked items found."
            
            lines = ["Blocked Items:"]
            for s in stories:
                blocker = s.blocker_reason or "No reason specified"
                lines.append(f"- {s.title}: {blocker}")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_blocked_items] Error: {e}")
        return f"Error fetching blocked items: {str(e)}"


@tool
def get_project_info(project_id: str) -> str:
    """Get project metadata: name, description, tech stack.
    
    Call this when:
    - Need project context for decision making
    - User asks about the project
    - Providing context to specialists
    
    Args:
        project_id: The project UUID
        
    Returns:
        Project information
    """
    try:
        from sqlmodel import Session
        from app.core.db import engine
        from app.models import Project
        
        with Session(engine) as session:
            project = session.get(Project, UUID(project_id))
            
            if not project:
                return "Project not found."
            
            lines = [
                f"Project: {project.name}",
                f"Description: {project.description or 'No description'}",
            ]
            
            if project.tech_stack:
                lines.append(f"Tech Stack: {', '.join(project.tech_stack)}")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_project_info] Error: {e}")
        return f"Error fetching project info: {str(e)}"


@tool
def get_flow_metrics(project_id: str) -> str:
    """Get flow metrics: cycle time, lead time, throughput.
    
    Call this when:
    - User asks about team performance
    - Need to report on progress/velocity
    - Analyzing flow efficiency
    
    Args:
        project_id: The project UUID
        
    Returns:
        Flow metrics summary
    """
    try:
        kanban_service, session = _get_kanban_service()
        
        with session:
            # TODO: Re-implement get_project_flow_metrics
            # metrics = kanban_service.get_project_flow_metrics(UUID(project_id))
            metrics = {}  # Temporary: method not implemented
            
            lines = ["Flow Metrics:"]
            
            if metrics.get("avg_cycle_time_hours"):
                lines.append(f"- Avg Cycle Time: {metrics['avg_cycle_time_hours']:.1f}h")
            elif not metrics:
                lines.append("- Flow metrics not available (feature in development)")
            
            if metrics.get("avg_lead_time_hours"):
                lines.append(f"- Avg Lead Time: {metrics['avg_lead_time_hours']:.1f}h")
            
            if metrics:
                lines.append(f"- Throughput: {metrics.get('throughput_per_week', 0)} stories/week")
            lines.append(f"- Current WIP: {metrics.get('work_in_progress', 0)}")
            lines.append(f"- Total Completed: {metrics.get('total_completed', 0)}")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_flow_metrics] Error: {e}")
        return f"Error fetching flow metrics: {str(e)}"


# Tool registry
TEAM_LEADER_TOOLS = [
    get_board_status,
    get_active_stories,
    search_stories,
    get_blocked_items,
    get_project_info,
    get_flow_metrics,
]


def get_team_leader_tools():
    """Get list of tools available to Team Leader."""
    return TEAM_LEADER_TOOLS
