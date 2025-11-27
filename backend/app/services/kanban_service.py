"""Kanban Service - Business logic for Lean Kanban (WIP limits, flow metrics, policies)."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func, and_

from app.models import Project, Story, StoryStatus, WorkflowPolicy, Agent, AgentStatus

logger = logging.getLogger(__name__)


class KanbanService:
    """Service for Lean Kanban management."""

    def __init__(self, session: Session):
        self.session = session

    def get_dynamic_wip_limits(self, project_id: UUID) -> dict:
        """Calculate WIP limits from active agent count (InProgress=devs, Review=testers)."""
        active_agents = [AgentStatus.running, AgentStatus.idle]
        
        dev_count = self.session.exec(
            select(func.count())
            .select_from(Agent)
            .where(Agent.project_id == project_id)
            .where(Agent.role_type == "developer")
            .where(Agent.status.in_(active_agents))
        ).one()
        
        tester_count = self.session.exec(
            select(func.count())
            .select_from(Agent)
            .where(Agent.project_id == project_id)
            .where(Agent.role_type == "tester")
            .where(Agent.status.in_(active_agents))
        ).one()
        
        return {
            "InProgress": {
                "limit": max(dev_count, 1),
                "type": "hard",
                "source": "dynamic",
                "agent_count": dev_count
            },
            "Review": {
                "limit": max(tester_count, 1),
                "type": "hard",
                "source": "dynamic",
                "agent_count": tester_count
            },
            "Done": {
                "limit": 20,
                "type": "soft",
                "source": "default",
                "agent_count": None
            }
        }

    def get_all_wip_limits(self, project_id: UUID) -> list[dict]:
        """Get all WIP limits (dynamic InProgress/Review + manual other columns)."""
        project = self.session.get(Project, project_id)
        if not project:
            return []
        
        dynamic_limits = self.get_dynamic_wip_limits(project_id)
        limits = []
        
        for column_name, config in dynamic_limits.items():
            limits.append({
                "id": str(project_id),
                "project_id": str(project_id),
                "column_name": column_name,
                "wip_limit": config["limit"],
                "limit_type": config["type"],
                "created_at": project.created_at,
                "updated_at": project.updated_at
            })
        
        if project.wip_data:
            for column_name, config in project.wip_data.items():
                if column_name not in ["InProgress", "Review", "Done"]:
                    limits.append({
                        "id": str(project_id),
                        "project_id": str(project_id),
                        "column_name": column_name,
                        "wip_limit": config.get("limit", 10),
                        "limit_type": config.get("type", "hard"),
                        "created_at": project.created_at,
                        "updated_at": project.updated_at
                    })
        
        return limits

    def get_dynamic_wip_with_usage(self, project_id: UUID) -> dict:
        """Get dynamic WIP limits with current story counts and available capacity."""
        dynamic_limits = self.get_dynamic_wip_limits(project_id)
        
        inprogress_count = self.session.exec(
            select(func.count())
            .select_from(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == StoryStatus.IN_PROGRESS)
        ).one()
        
        review_count = self.session.exec(
            select(func.count())
            .select_from(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == StoryStatus.REVIEW)
        ).one()
        
        done_count = self.session.exec(
            select(func.count())
            .select_from(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == StoryStatus.DONE)
        ).one()
        
        return {
            "InProgress": {
                **dynamic_limits["InProgress"],
                "current_stories": inprogress_count,
                "available": max(dynamic_limits["InProgress"]["limit"] - inprogress_count, 0)
            },
            "Review": {
                **dynamic_limits["Review"],
                "current_stories": review_count,
                "available": max(dynamic_limits["Review"]["limit"] - review_count, 0)
            },
            "Done": {
                **dynamic_limits["Done"],
                "current_stories": done_count,
                "available": max(dynamic_limits["Done"]["limit"] - done_count, 0)
            }
        }

    def validate_wip_move(
        self, 
        project_id: UUID, 
        story_id: UUID, 
        target_status: str
    ) -> tuple[bool, Optional[dict]]:
        """Validate if moving story would violate WIP limits (dynamic for InProgress/Review)."""
        project = self.session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if target_status in ["InProgress", "Review", "Done"]:
            dynamic_limits = self.get_dynamic_wip_limits(project_id)
            wip_config = dynamic_limits[target_status]
            wip_limit_value = wip_config["limit"]
            limit_type = wip_config["type"]
        else:
            if not project.wip_data or target_status not in project.wip_data:
                return (True, None)
            
            wip_config = project.wip_data[target_status]
            wip_limit_value = wip_config.get("limit", 10)
            limit_type = wip_config.get("type", "hard")
        
        status_enum = self._get_status_enum(target_status)
        if not status_enum:
            return (True, None)
        
        current_count = self.session.exec(
            select(func.count())
            .select_from(Story)
            .where(
                and_(
                    Story.project_id == project_id,
                    Story.status == status_enum,
                    Story.id != story_id
                )
            )
        ).one()
        
        new_count = current_count + 1
        
        if new_count > wip_limit_value:
            violation = {
                "column_name": target_status,
                "current_count": current_count,
                "wip_limit": wip_limit_value,
                "new_count": new_count,
                "limit_type": limit_type,
                "message": f"Cannot move to {target_status}: WIP limit {wip_limit_value} exceeded (current: {current_count})"
            }
            
            return (False, violation) if limit_type == "hard" else (True, violation)
        
        return (True, None)

    def _get_status_enum(self, status_str: str) -> Optional[StoryStatus]:
        """Convert status string to enum."""
        status_map = {
            "Todo": StoryStatus.TODO,
            "InProgress": StoryStatus.IN_PROGRESS,
            "Review": StoryStatus.REVIEW,
            "Done": StoryStatus.DONE
        }
        return status_map.get(status_str)

    def update_wip_limit(
        self, 
        project_id: UUID, 
        column_name: str, 
        wip_limit: int, 
        limit_type: str = "hard"
    ) -> dict:
        """Update or create manual WIP limit for a column."""
        project = self.session.get(Project, project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        if project.wip_data is None:
            project.wip_data = {}
        
        project.wip_data[column_name] = {
            "limit": wip_limit,
            "type": limit_type
        }
        
        project.updated_at = datetime.now(timezone.utc)
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        
        logger.info(f"Updated WIP limit for {column_name} in project {project_id}: {wip_limit}")
        
        return {
            "id": str(project_id),
            "project_id": str(project_id),
            "column_name": column_name,
            "wip_limit": wip_limit,
            "limit_type": limit_type,
            "created_at": project.created_at,
            "updated_at": project.updated_at
        }

    def get_workflow_policies(self, project_id: UUID) -> list[WorkflowPolicy]:
        """Get all active workflow policies for a project."""
        statement = (
            select(WorkflowPolicy)
            .where(WorkflowPolicy.project_id == project_id)
            .where(WorkflowPolicy.is_active == True)
        )
        return list(self.session.exec(statement).all())

    def create_workflow_policy(
        self,
        project_id: UUID,
        from_status: str,
        to_status: str,
        criteria: Optional[dict] = None,
        is_active: bool = True
    ) -> WorkflowPolicy:
        """Create a new workflow policy."""
        policy = WorkflowPolicy(
            project_id=project_id,
            from_status=from_status,
            to_status=to_status,
            criteria=criteria,
            is_active=is_active
        )
        
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        
        logger.info(f"Created workflow policy: {from_status} → {to_status} for project {project_id}")
        return policy

    def update_workflow_policy(
        self,
        policy_id: UUID,
        criteria: Optional[dict] = None,
        is_active: Optional[bool] = None
    ) -> Optional[WorkflowPolicy]:
        """Update existing workflow policy."""
        policy = self.session.get(WorkflowPolicy, policy_id)
        if not policy:
            return None
        
        if criteria is not None:
            policy.criteria = criteria
        if is_active is not None:
            policy.is_active = is_active
        
        policy.updated_at = datetime.now(timezone.utc)
        self.session.add(policy)
        self.session.commit()
        self.session.refresh(policy)
        
        logger.info(f"Updated workflow policy {policy_id}")
        return policy

    def delete_workflow_policy(self, policy_id: UUID) -> bool:
        """Delete workflow policy."""
        policy = self.session.get(WorkflowPolicy, policy_id)
        if not policy:
            return False
        
        self.session.delete(policy)
        self.session.commit()
        
        logger.info(f"Deleted workflow policy {policy_id}")
        return True

    def get_project_flow_metrics(self, project_id: UUID) -> dict:
        """Calculate flow metrics (cycle/lead time, throughput, WIP)."""
        completed_stories = self.session.exec(
            select(Story)
            .where(Story.project_id == project_id)
            .where(Story.status == StoryStatus.DONE)
            .where(Story.completed_at.isnot(None))
        ).all()
        
        cycle_times = [
            (s.completed_at - s.started_at).total_seconds() / 3600
            for s in completed_stories
            if s.started_at and s.completed_at
        ]
        
        lead_times = [
            (s.completed_at - s.created_at).total_seconds() / 3600
            for s in completed_stories
            if s.completed_at
        ]
        
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_completed = sum(
            1 for s in completed_stories 
            if s.completed_at and s.completed_at >= seven_days_ago
        )
        
        wip_count = self.session.exec(
            select(func.count())
            .select_from(Story)
            .where(Story.project_id == project_id)
            .where(Story.status.in_([StoryStatus.IN_PROGRESS, StoryStatus.REVIEW]))
        ).one()
        
        return {
            "avg_cycle_time_hours": sum(cycle_times) / len(cycle_times) if cycle_times else None,
            "avg_lead_time_hours": sum(lead_times) / len(lead_times) if lead_times else None,
            "throughput_per_week": recent_completed,
            "total_completed": len(completed_stories),
            "work_in_progress": wip_count,
            "aging_items": [],
            "bottlenecks": {}
        }
