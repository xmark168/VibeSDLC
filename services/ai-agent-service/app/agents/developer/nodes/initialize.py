"""
Initialize Node

Setup and validation for Developer Agent workflow.
"""

import os
from datetime import datetime
from pathlib import Path

from ..state import DeveloperState


def initialize(state: DeveloperState) -> DeveloperState:
    """
    Initialize Developer Agent workflow.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with initialization complete
    """
    print("🚀 Initializing Developer Agent workflow...")
    
    # Set default file paths if not provided
    if not state.backlog_path:
        state.backlog_path = str(
            Path(__file__).parent.parent / "backlog.json"
        )
    
    if not state.sprint_path:
        state.sprint_path = str(
            Path(__file__).parent.parent / "sprint.json"
        )
    
    # Validate file paths exist
    backlog_file = Path(state.backlog_path)
    sprint_file = Path(state.sprint_path)
    
    if not backlog_file.exists():
        raise FileNotFoundError(f"Backlog file not found: {state.backlog_path}")
    
    if not sprint_file.exists():
        raise FileNotFoundError(f"Sprint file not found: {state.sprint_path}")
    
    # Set working directory
    if not state.working_directory or state.working_directory == ".":
        state.working_directory = os.getcwd()
    
    # Generate session ID if not provided
    if not state.session_id:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        state.session_id = f"dev_agent_{timestamp}"
    
    # Initialize execution summary
    state.execution_summary.start_time = datetime.now().isoformat()
    
    print(f"📁 Backlog file: {state.backlog_path}")
    print(f"📁 Sprint file: {state.sprint_path}")
    print(f"📂 Working directory: {state.working_directory}")
    print(f"🆔 Session ID: {state.session_id}")
    print(f"🤖 Model: {state.model_name}")
    
    # Move to next phase
    state.current_phase = "parse_sprint"
    
    print("✅ Initialization complete")
    return state
