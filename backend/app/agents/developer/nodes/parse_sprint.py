"""
Parse Sprint Node

Load and validate sprint.json and backlog.json files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

from ..state import DeveloperState


def _validate_backlog_item(item: Dict[str, Any]) -> bool:
    """
    Validate a single backlog item has required fields.
    
    Args:
        item: Backlog item to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["id", "type", "title", "description"]
    
    for field in required_fields:
        if field not in item or not item[field]:
            print(f"⚠️ Invalid backlog item {item.get('id', 'UNKNOWN')}: missing {field}")
            return False
    
    return True


def _validate_sprint_data(sprint_data: Dict[str, Any]) -> bool:
    """
    Validate sprint data has required fields.
    
    Args:
        sprint_data: Sprint data to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["sprint_id", "assigned_items"]
    
    for field in required_fields:
        if field not in sprint_data:
            print(f"⚠️ Invalid sprint data: missing {field}")
            return False
    
    if not isinstance(sprint_data["assigned_items"], list):
        print("⚠️ Invalid sprint data: assigned_items must be a list")
        return False
    
    return True


def parse_sprint(state: DeveloperState) -> DeveloperState:
    """
    Parse sprint and backlog data from JSON files.
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with parsed data
    """
    print("📖 Parsing sprint and backlog data...")
    
    try:
        # Load backlog data
        print(f"📄 Loading backlog from: {state.backlog_path}")
        with open(state.backlog_path, 'r', encoding='utf-8') as f:
            backlog_data = json.load(f)
        
        if not isinstance(backlog_data, list):
            raise ValueError("Backlog data must be a list of items")
        
        # Validate backlog items
        valid_backlog_items = []
        for item in backlog_data:
            if _validate_backlog_item(item):
                valid_backlog_items.append(item)
        
        state.backlog_data = valid_backlog_items
        print(f"✅ Loaded {len(valid_backlog_items)} valid backlog items")
        
        # Load sprint data
        print(f"📄 Loading sprint from: {state.sprint_path}")
        with open(state.sprint_path, 'r', encoding='utf-8') as f:
            sprint_list = json.load(f)
        
        if not isinstance(sprint_list, list) or len(sprint_list) == 0:
            raise ValueError("Sprint data must be a non-empty list")
        
        # Use first sprint (assuming single sprint execution)
        sprint_data = sprint_list[0]
        
        if not _validate_sprint_data(sprint_data):
            raise ValueError("Invalid sprint data structure")
        
        state.sprint_data = sprint_data
        
        # Update execution summary
        state.execution_summary.sprint_id = sprint_data["sprint_id"]
        state.execution_summary.sprint_goal = sprint_data.get("sprint_goal", "")
        state.execution_summary.total_assigned_items = len(sprint_data["assigned_items"])
        
        print(f"✅ Loaded sprint: {sprint_data['sprint_id']}")
        print(f"📋 Sprint goal: {sprint_data.get('sprint_goal', 'N/A')}")
        print(f"📝 Assigned items: {len(sprint_data['assigned_items'])}")
        
        # Move to next phase
        state.current_phase = "filter_tasks"
        
    except FileNotFoundError as e:
        error_msg = f"File not found: {e}"
        print(f"❌ {error_msg}")
        raise
        
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON format: {e}"
        print(f"❌ {error_msg}")
        raise
        
    except Exception as e:
        error_msg = f"Error parsing sprint/backlog data: {e}"
        print(f"❌ {error_msg}")
        raise
    
    print("✅ Sprint and backlog parsing complete")
    return state
