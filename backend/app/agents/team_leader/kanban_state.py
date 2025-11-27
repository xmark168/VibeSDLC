"""Lean Kanban state manager for Team Leader.

Provides Kanban board context to LLM agents for intelligent routing decisions.
"""

import logging
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select, func, and_
from app.models import Story, Epic, Project, StoryStatus
import httpx

logger = logging.getLogger(__name__)


class KanbanStateManager:
    """Manages Kanban board state and flow metrics for LLM context."""
    
    COLUMN_ORDER = ["Backlog", "Todo", "InProgress", "Review", "Done"]
    
    def __init__(self, project_id: UUID, session: Session):
        """Initialize Kanban state manager.
        
        Args:
            project_id: Project UUID
            session: Database session
        """
        self.project_id = project_id
        self.session = session
        self.project = session.get(Project, project_id)
    
    # === Board State ===
    
    def get_board_snapshot(self) -> dict:
        """Get current Kanban board state.
        
        Returns:
            {
                "Backlog": [stories...],
                "Todo": [stories...],
                "InProgress": [stories...],
                "Review": [stories...],
                "Done": [stories...]
            }
        """
        board = {col: [] for col in self.COLUMN_ORDER}
        
        stories = self.session.exec(
            select(Story).where(Story.project_id == self.project_id)
        ).all()
        
        for story in stories:
            status_key = self._map_status_to_column(story.status)
            board[status_key].append({
                "id": str(story.id),
                "title": story.title,
                "status": story.status.value,
                "priority": story.priority or "Medium",
                "story_points": story.story_points,
                "age_hours": story.age_in_current_status_hours,
                "epic_id": str(story.epic_id) if story.epic_id else None
            })
        
        return board
    
    def _map_status_to_column(self, status: StoryStatus) -> str:
        """Map StoryStatus enum to Kanban column."""
        mapping = {
            StoryStatus.TODO: "Todo",
            StoryStatus.IN_PROGRESS: "InProgress",
            StoryStatus.REVIEW: "Review",
            StoryStatus.DONE: "Done"
        }
        return mapping.get(status, "Backlog")
    
    # === WIP Limits ===
    
    def get_wip_status(self) -> dict:
        """Check WIP limits for all columns.
        
        Returns:
            {
                "InProgress": {
                    "current": 3, 
                    "limit": 5, 
                    "utilization": 0.6, 
                    "available": 2,
                    "limit_type": "hard"
                },
                "Review": {...}
            }
        """
        if not self.project or not self.project.wip_data:
            return {}
        
        wip_status = {}
        board = self.get_board_snapshot()
        
        for column, config in self.project.wip_data.items():
            current = len(board.get(column, []))
            limit = config.get("limit", 10)
            
            wip_status[column] = {
                "current": current,
                "limit": limit,
                "utilization": current / limit if limit > 0 else 0,
                "available": max(0, limit - current),
                "limit_type": config.get("type", "hard")
            }
        
        return wip_status
    
    def check_can_pull(self, column: str) -> tuple[bool, str]:
        """Check if can pull work into column (WIP limit check).
        
        Args:
            column: Target column name
            
        Returns:
            (can_pull, reason)
        """
        wip_status = self.get_wip_status()
        
        if column not in wip_status:
            return True, "No WIP limit configured"
        
        status = wip_status[column]
        if status["available"] > 0:
            return True, f"Capacity available: {status['available']} slots"
        else:
            limit_type = status["limit_type"]
            if limit_type == "hard":
                return False, f"WIP limit reached ({status['limit']})"
            else:
                return True, f"Soft WIP limit ({status['limit']}) - can proceed with caution"
    
    # === Flow Metrics ===
    
    async def get_flow_metrics(self) -> dict:
        """Get Lean Kanban flow metrics via API.
        
        Returns:
            Flow metrics dict with cycle_time, lead_time, throughput, etc.
        """
        try:
            # Call the existing lean_kanban API endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"http://localhost:8000/api/v1/projects/{self.project_id}/flow-metrics",
                    params={"days": 30}
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch flow metrics: {e}")
        
        return {
            "avg_cycle_time_hours": 0,
            "avg_lead_time_hours": 0,
            "throughput_per_week": 0,
            "total_completed": 0,
            "work_in_progress": 0
        }
    
    def detect_bottlenecks(self, aging_threshold_hours: float = 48) -> list[dict]:
        """Identify bottlenecks: columns with aging items.
        
        Args:
            aging_threshold_hours: Stories older than this are considered aging
            
        Returns:
            List of bottleneck info dicts
        """
        board = self.get_board_snapshot()
        bottlenecks = []
        
        for column in ["Todo", "InProgress", "Review"]:
            aging_items = [
                s for s in board.get(column, [])
                if s["age_hours"] > aging_threshold_hours
            ]
            
            if aging_items:
                bottlenecks.append({
                    "column": column,
                    "aging_count": len(aging_items),
                    "oldest_age_hours": max(s["age_hours"] for s in aging_items),
                    "stories": aging_items[:3]  # Top 3 oldest
                })
        
        return bottlenecks
    
    def suggest_next_pull(self, from_column: str = "Todo") -> dict | None:
        """Suggest which story to pull next based on priority.
        
        Args:
            from_column: Column to pull from
            
        Returns:
            Story dict or None
        """
        board = self.get_board_snapshot()
        candidates = board.get(from_column, [])
        
        if not candidates:
            return None
        
        # Priority order mapping
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        
        # Sort by priority then age
        sorted_candidates = sorted(
            candidates,
            key=lambda s: (priority_order.get(s.get("priority", "Medium"), 1), -s["age_hours"])
        )
        
        return sorted_candidates[0] if sorted_candidates else None
    
    # === Epic Progress ===
    
    def get_epic_progress(self, epic_id: UUID) -> dict:
        """Calculate epic completion.
        
        Args:
            epic_id: Epic UUID
            
        Returns:
            Epic progress dict
        """
        stories = self.session.exec(
            select(Story).where(
                and_(
                    Story.epic_id == epic_id,
                    Story.project_id == self.project_id
                )
            )
        ).all()
        
        if not stories:
            return {"total": 0, "done": 0, "percentage": 0}
        
        total = len(stories)
        done = sum(1 for s in stories if s.status == StoryStatus.DONE)
        
        return {
            "total": total,
            "done": done,
            "percentage": (done / total * 100) if total > 0 else 0,
            "in_progress": sum(1 for s in stories if s.status == StoryStatus.IN_PROGRESS),
            "in_review": sum(1 for s in stories if s.status == StoryStatus.REVIEW)
        }
    
    def get_all_epics_progress(self) -> list[dict]:
        """Get progress for all epics in project.
        
        Returns:
            List of epic progress dicts
        """
        epics = self.session.exec(
            select(Epic).where(Epic.project_id == self.project_id)
        ).all()
        
        return [
            {
                "epic_id": str(epic.id),
                "title": epic.title,
                "domain": epic.domain,
                "progress": self.get_epic_progress(epic.id)
            }
            for epic in epics
        ]
