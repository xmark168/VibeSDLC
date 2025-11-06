"""Scrum Master Orchestrator - Điều phối flow từ PO Agent → Sprint Planner → Database.

Workflow:
1. Nhận sprint plan + backlog items từ PO Agent
2. Trigger Sprint Planner để enrich & verify data (Sprint Planner tự lưu vào database)
3. Broadcast kanban items qua WebSocket
"""

import json
import asyncio
from typing import Optional, Callable, Any
from uuid import UUID
from datetime import datetime

from app.agents.scrum_master.sprint_planner.agent import SprintPlannerAgent
from app.core.response_queue import response_manager


class ScrumMasterOrchestrator:
    """Orchestrator để điều phối flow từ PO Agent → Sprint Planner → Database."""

    def __init__(
        self,
        project_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        websocket_broadcast_fn: Optional[Callable] = None,
    ):
        """Initialize Scrum Master Orchestrator.

        Args:
            project_id: Project ID
            user_id: User ID
            session_id: Session ID for tracing
            websocket_broadcast_fn: Function để broadcast qua WebSocket
        """
        self.project_id = project_id
        self.user_id = user_id
        self.session_id = session_id or f"sm_orchestrator_{project_id}_{user_id}"
        self.websocket_broadcast_fn = websocket_broadcast_fn

    async def process_po_output(
        self,
        sprint_plan: dict,
        backlog_items: list[dict],
    ) -> dict:
        """Process PO Agent output: trigger Sprint Planner & save to database.

        Args:
            sprint_plan: Sprint plan từ PO Agent
            backlog_items: Backlog items từ PO Agent

        Returns:
            dict: Result với sprint + backlog items đã được enrich
        """
        print("\n" + "=" * 80)
        print("🎯 SCRUM MASTER ORCHESTRATOR - Processing PO Output")
        print("=" * 80)
        print(f"   Project ID: {self.project_id}")
        print(f"   User ID: {self.user_id}")
        print(f"   Session ID: {self.session_id}")
        print(f"   Sprints: {len(sprint_plan.get('sprints', []))}")
        print(f"   Backlog Items: {len(backlog_items)}")
        print(f"   Sprint Plan Keys: {list(sprint_plan.keys())}")
        print("=" * 80 + "\n")

        try:
            # Step 1: Broadcast to WebSocket - Starting Sprint Planner
            await self._broadcast({
                "type": "scrum_master_step",
                "step": "starting",
                "message": "🚀 Scrum Master đang xử lý Sprint Plan từ PO Agent...",
                "agent": "Scrum Master"
            })

            # Auto-switch to Kanban tab
            await self._broadcast({
                "type": "switch_tab",
                "tab": "kanban",
                "message": "Đang chuyển sang tab Kanban để xem cập nhật..."
            })

            # Step 2: Trigger Sprint Planner (Sprint Planner sẽ tự lưu vào database)
            print("\n[1/2] Triggering Sprint Planner Agent...")
            sprint_planner = SprintPlannerAgent(
                session_id=self.session_id,
                user_id=self.user_id,
                websocket_broadcast_fn=self.websocket_broadcast_fn,
                project_id=self.project_id
            )

            # Prepare input for Sprint Planner
            sprint_planner_input = {
                "sprint_plan": sprint_plan,
                "backlog_items": backlog_items
            }

            # Run Sprint Planner (sẽ enrich, verify, assign, và LƯU VÀO DATABASE)
            enriched_result = await self._run_sprint_planner(
                sprint_planner,
                sprint_planner_input
            )

            # Step 3: Broadcast kanban items
            print("\n[2/2] Broadcasting Kanban Items...")

            # Get saved data from enriched_result
            saved_sprints = enriched_result.get("saved_sprint_ids", [])
            saved_items = enriched_result.get("saved_item_ids", [])

            # Prepare data for broadcast
            sprints_for_broadcast = []
            items_for_broadcast = []

            # Use assigned_items (with assignment data) instead of backlog_items
            # assigned_items have: assigned_to_dev, assigned_to_tester, and status="Todo"
            assigned_items = enriched_result.get("assigned_items", [])

            if assigned_items:
                print(f"   Broadcasting {len(assigned_items)} assigned items...")
                for item in assigned_items:
                    items_for_broadcast.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "status": "Todo",  # All assigned items go to Todo column
                        "type": item.get("type"),
                        "story_point": item.get("story_point"),
                        "estimate_value": item.get("estimate_value"),
                        "sprint_id": item.get("sprint_id"),
                        "item_id": item.get("item_id"),
                        "assigned_to_dev": item.get("assigned_to_dev"),
                        "assigned_to_tester": item.get("assigned_to_tester")
                    })
            else:
                # Fallback to backlog_items if no assigned_items (shouldn't happen)
                print("   [!] No assigned_items found, using backlog_items as fallback")
                for item in enriched_result.get("backlog_items", []):
                    items_for_broadcast.append({
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "status": item.get("status", "Backlog"),
                        "type": item.get("type"),
                        "story_point": item.get("story_point"),
                        "estimate_value": item.get("estimate_value"),
                        "sprint_id": item.get("sprint_id"),
                        "item_id": item.get("item_id")
                    })

            await self._broadcast_kanban_items(
                sprints_for_broadcast,
                items_for_broadcast
            )

            # Broadcast task assignment summary
            total_assigned = len(assigned_items) if assigned_items else 0
            await self._broadcast({
                "type": "agent_step",
                "step": "task_assignment",
                "agent": "Scrum Master",
                "message": f"✅ Đã giao việc cho team: {total_assigned} tasks đã được assign cho Developer và Tester."
            })

            # Broadcast kanban update notification
            await self._broadcast({
                "type": "agent_step",
                "step": "kanban_updated",
                "agent": "Scrum Master",
                "message": f"📋 Kanban Board đã được cập nhật! Bạn có thể chuyển sang tab Kanban để xem chi tiết."
            })

            # Final broadcast
            await self._broadcast({
                "type": "scrum_master_step",
                "step": "completed",
                "message": "✅ Scrum Master hoàn thành! Sprint Plan đã được lưu vào database.",
                "agent": "Scrum Master"
            })

            # Turn off typing indicators
            await self._broadcast({
                "type": "typing",
                "agent_name": "PO Agent",
                "is_typing": False
            })

            await self._broadcast({
                "type": "typing",
                "agent_name": "Scrum Master",
                "is_typing": False
            })

            print("\n✅ Scrum Master Orchestrator completed successfully!")
            print(f"   Saved Sprints: {len(saved_sprints)}")
            print(f"   Saved Items: {len(saved_items)}")
            print("=" * 80 + "\n")

            return enriched_result

        except Exception as e:
            print(f"\n❌ Error in Scrum Master Orchestrator: {e}")
            import traceback
            traceback.print_exc()

            await self._broadcast({
                "type": "scrum_master_step",
                "step": "error",
                "message": f"❌ Lỗi: {str(e)}",
                "agent": "Scrum Master"
            })

            # Turn off typing indicators on error
            await self._broadcast({
                "type": "typing",
                "agent_name": "PO Agent",
                "is_typing": False
            })

            await self._broadcast({
                "type": "typing",
                "agent_name": "Scrum Master",
                "is_typing": False
            })

            raise

    async def _run_sprint_planner(
        self,
        sprint_planner: SprintPlannerAgent,
        input_data: dict
    ) -> dict:
        """Run Sprint Planner Agent.

        Args:
            sprint_planner: Sprint Planner Agent instance
            input_data: Input data for Sprint Planner

        Returns:
            dict: Enriched result từ Sprint Planner
        """
        print("   - Running Sprint Planner Agent...")

        # Extract sprint_plan and backlog_items
        sprint_plan = input_data.get("sprint_plan", {})
        backlog_items = input_data.get("backlog_items", [])

        # Run Sprint Planner with WebSocket streaming
        result = await sprint_planner.run_with_streaming(
            sprint_plan=sprint_plan,
            backlog_items=backlog_items
        )

        return result

    async def _broadcast_kanban_items(
        self,
        sprints: list[dict],
        backlog_items: list[dict]
    ) -> None:
        """Broadcast kanban items qua WebSocket.

        Args:
            sprints: List of sprints (with database IDs)
            backlog_items: List of backlog items (with database IDs)
        """
        if not self.websocket_broadcast_fn:
            return

        # Group backlog items by status for Kanban board
        kanban_columns = {
            "Backlog": [],
            "Todo": [],
            "Doing": [],
            "Done": []
        }

        for item in backlog_items:
            status = item.get("status", "Backlog")
            kanban_columns[status].append({
                "id": item.get("id"),
                "title": item.get("title"),
                "description": item.get("description"),
                "type": item.get("type"),
                "status": status,
                "story_point": item.get("story_point"),
                "estimate_value": item.get("estimate_value"),
                "rank": item.get("rank"),
                "assignee_id": item.get("assigned_to_dev") or item.get("assignee_id"),
                "reviewer_id": item.get("assigned_to_tester") or item.get("reviewer_id"),
                "sprint_id": item.get("sprint_id"),  # May be None for unassigned items
                "item_id": item.get("item_id")  # Original ID from PO Agent
            })

        await self._broadcast({
            "type": "kanban_update",
            "data": {
                "sprints": sprints,
                "kanban_board": kanban_columns,
                "total_items": len(backlog_items),
                "timestamp": datetime.now().isoformat()
            }
        })

    async def _broadcast(self, message: dict) -> None:
        """Broadcast message qua WebSocket.

        Args:
            message: Message to broadcast
        """
        if not self.websocket_broadcast_fn:
            return

        try:
            await self.websocket_broadcast_fn(message, self.project_id)
        except Exception as e:
            print(f"[Warning] Failed to broadcast: {e}")

