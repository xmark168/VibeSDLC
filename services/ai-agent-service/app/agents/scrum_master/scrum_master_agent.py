"""Scrum Master Agent - Simple orchestrator.

This is the main Scrum Master agent that coordinates sprint activities.
Architecture: Simple orchestrator that delegates to Sprint Planner (LangGraph).

DRAFT VERSION - No database connection, uses hardcoded test data.
Output format matches database schema for future integration.
"""

import os
import json
from typing import Optional
from datetime import datetime
from langfuse.langchain import CallbackHandler

from .sprint_planner.agent import SprintPlannerAgent
from .models import ScrumMasterOutput
from .test_data import MOCK_TEAM


class ScrumMasterAgent:
    """Scrum Master Agent - Simple orchestrator for sprint planning."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2
    ):
        """Initialize Scrum Master Agent.

        Args:
            session_id: Session ID for Langfuse tracing
            user_id: User ID for tracking
            model_name: OpenAI model name (default: gpt-4o-mini)
            temperature: LLM temperature (default: 0.2 for balanced reasoning)
        """
        self.session_id = session_id
        self.user_id = user_id
        self.model_name = model_name
        self.temperature = temperature

        # Initialize Langfuse callback handler
        try:
            self.langfuse_handler = CallbackHandler(
                flush_at=5,  # Flush every 5 events to avoid 413 errors
                flush_interval=1.0
            )
        except Exception:
            # Fallback for older versions without flush_at parameter
            self.langfuse_handler = CallbackHandler()

        # Initialize Sprint Planner
        self.sprint_planner = SprintPlannerAgent(
            session_id=f"{session_id}_sprint_planner",
            user_id=user_id,
            model_name=model_name,
            temperature=temperature
        )

    def process_po_output(
        self,
        po_output: dict,
        team: Optional[dict] = None
    ) -> dict:
        """Process Product Owner output through Sprint Planner.

        This is the main orchestration method that delegates to Sprint Planner.

        Args:
            po_output: PO output with metadata, prioritized_backlog, sprints
            team: Team members dict (optional, uses MOCK_TEAM by default)

        Returns:
            dict: Complete processed output with sprints, items, assignments
        """
        print("\n" + "="*80)
        print("🎯 SCRUM MASTER: Processing PO Output")
        print("="*80)

        try:
            # Delegate to Sprint Planner
            result = self.sprint_planner.process_po_output(
                po_output=po_output,
                team=team or MOCK_TEAM
            )

            print("\n✅ SCRUM MASTER: Processing complete")
            return result

        except Exception as e:
            print(f"\n❌ SCRUM MASTER: Error processing PO output: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Flush Langfuse traces
            try:
                self.langfuse_handler.langfuse.flush()
            except Exception:
                pass






# ==================== CONVENIENCE FUNCTION ====================

def create_scrum_master_agent(
    session_id: str,
    user_id: str,
    model_name: str = "gpt-4o-mini"
) -> ScrumMasterAgent:
    """Create Scrum Master Agent instance.

    Args:
        session_id: Session ID for Langfuse tracing
        user_id: User ID for tracking
        model_name: OpenAI model name (default: gpt-4o-mini)

    Returns:
        ScrumMasterAgent instance
    """
    return ScrumMasterAgent(
        session_id=session_id,
        user_id=user_id,
        model_name=model_name
    )
