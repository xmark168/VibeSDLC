"""
Initialize Node

Setup initial state, validate input và chuẩn bị cho planning workflow.
"""

from typing import Dict, Any
from langchain_core.messages import HumanMessage
from ..state import PlannerState


def initialize(state: PlannerState) -> PlannerState:
    """
    Initialize node - Setup initial state và validate input.
    
    Tasks:
    1. Validate task_description input
    2. Setup initial state values
    3. Create initial message for workflow
    4. Set current_phase to parse_task
    
    Args:
        state: PlannerState với task_description
        
    Returns:
        Updated PlannerState ready for task parsing
    """
    print("\n" + "="*80)
    print("🚀 INITIALIZE NODE - Setup Planning Workflow")
    print("="*80)
    
    # Validate input
    if not state.task_description.strip():
        print("❌ Error: Empty task description")
        state.status = "error_empty_task"
        state.error_message = "Task description cannot be empty"
        return state
    
    print(f"📝 Task Description: {state.task_description[:200]}...")
    
    # Reset state for fresh planning
    state.current_iteration = 0
    state.validation_score = 0.0
    state.validation_issues = []
    state.can_proceed = False
    state.ready_for_implementation = False
    state.status = "initialized"
    state.error_message = ""
    
    # Clear previous outputs
    state.tools_output = {}
    state.final_plan = {}
    
    # Create initial message for workflow
    initial_message = HumanMessage(
        content=f"""Planning Request:

Task Description: {state.task_description}

Codebase Context: {state.codebase_context if state.codebase_context else 'No additional context provided'}

Please analyze this task and create a detailed implementation plan following the 4-phase planning process:
1. Task Parsing - Extract requirements and constraints
2. Codebase Analysis - Analyze existing code and dependencies  
3. Dependency Mapping - Map execution order and dependencies
4. Implementation Planning - Create detailed implementation plan

Begin with Phase 1: Task Parsing."""
    )
    
    # Add to messages if not already present
    if not state.messages or state.messages[-1].content != initial_message.content:
        state.messages.append(initial_message)
    
    # Set next phase
    state.current_phase = "parse_task"
    
    print("✅ Initialization complete")
    print(f"🔄 Next Phase: {state.current_phase}")
    print("="*80 + "\n")
    
    return state
