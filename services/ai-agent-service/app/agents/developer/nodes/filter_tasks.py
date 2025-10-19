"""
Filter Tasks Node

Filter tasks by task_type and resolve parent context.
"""

from typing import Dict, List, Any, Optional

from ..state import DeveloperState


def _find_backlog_item_by_id(backlog_data: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """
    Find backlog item by ID.
    
    Args:
        backlog_data: List of backlog items
        item_id: ID to search for
        
    Returns:
        Backlog item if found, None otherwise
    """
    for item in backlog_data:
        if item.get("id") == item_id:
            return item
    return None


def _resolve_parent_context(item: Dict[str, Any], backlog_data: List[Dict[str, Any]]) -> str:
    """
    Resolve parent context for a task.
    
    Args:
        item: Task item
        backlog_data: List of all backlog items
        
    Returns:
        Parent context string
    """
    parent_id = item.get("parent_id")
    if not parent_id:
        return ""
    
    parent_item = _find_backlog_item_by_id(backlog_data, parent_id)
    if not parent_item:
        return f"Parent ID {parent_id} not found"
    
    # Build parent context
    context_parts = []
    
    # Add parent type and title
    parent_type = parent_item.get("type", "Unknown")
    parent_title = parent_item.get("title", "")
    if parent_title:
        context_parts.append(f"{parent_type}: {parent_title}")
    
    # Add parent description
    parent_description = parent_item.get("description", "")
    if parent_description:
        context_parts.append(f"Description: {parent_description}")
    
    # Add business value if available
    business_value = parent_item.get("business_value", "")
    if business_value:
        context_parts.append(f"Business Value: {business_value}")
    
    # Add acceptance criteria if available
    acceptance_criteria = parent_item.get("acceptance_criteria", [])
    if acceptance_criteria:
        criteria_text = "; ".join(acceptance_criteria)
        context_parts.append(f"Acceptance Criteria: {criteria_text}")
    
    return "\n".join(context_parts)


def _enrich_task_description(item: Dict[str, Any], parent_context: str) -> str:
    """
    Create enriched task description combining task and parent context.
    
    Args:
        item: Task item
        parent_context: Parent context string
        
    Returns:
        Enriched description
    """
    task_title = item.get("title", "")
    task_description = item.get("description", "")
    
    enriched_parts = []
    
    # Add task information
    if task_title:
        enriched_parts.append(f"Task: {task_title}")
    
    if task_description:
        enriched_parts.append(f"Task Description: {task_description}")
    
    # Add parent context if available
    if parent_context:
        enriched_parts.append(f"\nParent Context:\n{parent_context}")
    
    # Add acceptance criteria if available
    acceptance_criteria = item.get("acceptance_criteria", [])
    if acceptance_criteria:
        criteria_text = "; ".join(acceptance_criteria)
        enriched_parts.append(f"\nTask Acceptance Criteria: {criteria_text}")
    
    return "\n".join(enriched_parts)


def filter_tasks(state: DeveloperState) -> DeveloperState:
    """
    Filter tasks by task_type and resolve parent context.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with filtered tasks
    """
    print("🔍 Filtering tasks and resolving context...")
    
    assigned_items = state.sprint_data.get("assigned_items", [])
    eligible_tasks = []
    
    print(f"📋 Processing {len(assigned_items)} assigned items...")
    
    for item_id in assigned_items:
        # Find item in backlog
        item = _find_backlog_item_by_id(state.backlog_data, item_id)
        
        if not item:
            print(f"⚠️ Item {item_id} not found in backlog, skipping")
            continue
        
        # Check task_type filter
        task_type = item.get("task_type")
        
        if task_type not in ["Development", "Infrastructure"]:
            print(f"⏭️ Skipping {item_id} ({item.get('type', 'Unknown')}): task_type='{task_type}'")
            continue
        
        # Resolve parent context
        parent_context = _resolve_parent_context(item, state.backlog_data)
        
        # Create enriched description
        enriched_description = _enrich_task_description(item, parent_context)
        
        # Create enriched task item
        enriched_task = {
            "id": item["id"],
            "type": item.get("type", ""),
            "task_type": task_type,
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "parent_id": item.get("parent_id"),
            "parent_context": parent_context,
            "enriched_description": enriched_description,
            "original_item": item
        }
        
        eligible_tasks.append(enriched_task)
        
        print(f"✅ Eligible: {item_id} ({task_type}) - {item.get('title', '')[:50]}...")
        if parent_context:
            parent_title = parent_context.split('\n')[0] if parent_context else "No parent"
            print(f"   📎 Parent: {parent_title[:60]}...")
    
    state.eligible_tasks = eligible_tasks
    state.execution_summary.eligible_tasks_count = len(eligible_tasks)
    
    print(f"🎯 Found {len(eligible_tasks)} eligible tasks for processing")
    
    # Move to next phase
    state.current_phase = "process_tasks"
    
    print("✅ Task filtering and context resolution complete")
    return state
