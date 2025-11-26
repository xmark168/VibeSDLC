"""Business Analyst Tools for File Operations.

Tools for BA sub-agents to interact with PRD and User Stories files.
Provides synchronous interface to async ProjectFiles operations.
"""

from crewai.tools import tool
from pathlib import Path
import json
from typing import Optional


# ==================== PRD Tools ====================

@tool
def load_prd_from_file(project_path: str) -> dict:
    """
    Load existing PRD from project files.
    
    Use this when you need to read the current PRD to update it or extract information.
    
    Args:
        project_path: Path to project directory (e.g., "projects/proj_123")
    
    Returns:
        PRD data as dictionary, or empty dict if not exists
    
    Example:
        prd = load_prd_from_file("projects/proj_123")
        print(f"Project: {prd['project_name']}")
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    pf = ProjectFiles(Path(project_path))
    try:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        prd = loop.run_until_complete(pf.load_prd())
        return prd or {}
    except Exception as e:
        return {"error": f"Failed to load PRD: {str(e)}"}


@tool
def save_prd_to_file(project_path: str, prd_data: str) -> dict:
    """
    Save PRD to project files (both JSON and Markdown).
    
    Use this after generating or updating a PRD to persist it to disk.
    
    Args:
        project_path: Path to project directory
        prd_data: PRD data as JSON string (must be valid JSON)
    
    Returns:
        Success status and file paths
    
    Example:
        prd = {
            "project_name": "Login System",
            "version": "1.0",
            "overview": "User authentication system",
            "features": [...]
        }
        result = save_prd_to_file("projects/proj_123", json.dumps(prd))
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    try:
        prd_dict = json.loads(prd_data)
        pf = ProjectFiles(Path(project_path))
        
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        path = loop.run_until_complete(pf.save_prd(prd_dict))
        
        return {
            "success": True,
            "prd_json_path": str(path.parent / "prd.json"),
            "prd_md_path": str(path),
            "message": "PRD saved successfully"
        }
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def update_prd_section(project_path: str, section_name: str, new_content: str) -> dict:
    """
    Update a specific section in existing PRD.
    
    Use this for targeted PRD updates without regenerating the entire document.
    
    Args:
        project_path: Path to project directory
        section_name: Section to update (e.g., "features", "goals", "constraints")
        new_content: New content as JSON string
    
    Returns:
        Success status and updated PRD
    
    Example:
        # Add 2FA to features
        new_features = json.dumps([
            {"name": "Login", "description": "..."},
            {"name": "2FA", "description": "Two-factor authentication"}
        ])
        result = update_prd_section("projects/proj_123", "features", new_features)
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    try:
        # Load existing PRD
        pf = ProjectFiles(Path(project_path))
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        prd = loop.run_until_complete(pf.load_prd())
        
        if not prd:
            return {"success": False, "error": "PRD not found"}
        
        # Update section
        prd[section_name] = json.loads(new_content)
        prd["change_summary"] = f"Updated {section_name}"
        
        # Save updated PRD
        path = loop.run_until_complete(pf.save_prd(prd))
        
        return {
            "success": True,
            "section_updated": section_name,
            "prd_path": str(path),
            "message": f"Section '{section_name}' updated successfully"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== User Stories Tools ====================

@tool
def load_user_stories_from_file(project_path: str) -> list:
    """
    Load existing user stories from project files.
    
    Use this to read current user stories for updates or analysis.
    
    Args:
        project_path: Path to project directory
    
    Returns:
        List of user story dictionaries
    
    Example:
        stories = load_user_stories_from_file("projects/proj_123")
        print(f"Found {len(stories)} stories")
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    pf = ProjectFiles(Path(project_path))
    try:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        stories = loop.run_until_complete(pf.load_user_stories())
        return stories or []
    except Exception as e:
        return [{"error": f"Failed to load stories: {str(e)}"}]


@tool
def save_user_stories_to_file(project_path: str, stories_data: str) -> dict:
    """
    Save user stories to project files (both JSON and Markdown).
    
    Use this after generating user stories to persist them.
    
    Args:
        project_path: Path to project directory
        stories_data: Stories as JSON string (array of story objects)
    
    Returns:
        Success status and file paths
    
    Example:
        stories = [
            {
                "title": "User Login",
                "description": "As a user, I want to login...",
                "acceptance_criteria": ["Can login with email", ...],
                "story_points": 3,
                "priority": "High"
            }
        ]
        result = save_user_stories_to_file("projects/proj_123", json.dumps(stories))
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    try:
        stories_list = json.loads(stories_data)
        if not isinstance(stories_list, list):
            return {"success": False, "error": "stories_data must be an array"}
        
        pf = ProjectFiles(Path(project_path))
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        path = loop.run_until_complete(pf.save_user_stories(stories_list))
        
        return {
            "success": True,
            "stories_count": len(stories_list),
            "stories_md_path": str(path),
            "message": f"Saved {len(stories_list)} user stories"
        }
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def add_user_story(project_path: str, story_data: str) -> dict:
    """
    Add a single user story to existing stories.
    
    Use this to append a new story without rewriting all stories.
    
    Args:
        project_path: Path to project directory
        story_data: Single story as JSON string
    
    Returns:
        Success status and updated stories list
    
    Example:
        story = {
            "title": "Password Reset",
            "description": "As a user, I want to reset password...",
            "acceptance_criteria": ["Receive reset email", ...],
            "story_points": 2
        }
        result = add_user_story("projects/proj_123", json.dumps(story))
    """
    from app.utils.project_files import ProjectFiles
    import asyncio
    import nest_asyncio
    
    try:
        # Load existing stories
        pf = ProjectFiles(Path(project_path))
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        stories = loop.run_until_complete(pf.load_user_stories()) or []
        
        # Add new story
        new_story = json.loads(story_data)
        stories.append(new_story)
        
        # Save updated stories
        path = loop.run_until_complete(pf.save_user_stories(stories))
        
        return {
            "success": True,
            "story_added": new_story.get("title", "Untitled"),
            "total_stories": len(stories),
            "stories_path": str(path)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== Validation Tools ====================

@tool
def validate_prd_completeness(prd_data: str) -> dict:
    """
    Validate that PRD has all required sections.
    
    Use this before saving PRD to ensure quality.
    
    Args:
        prd_data: PRD as JSON string
    
    Returns:
        Validation results with missing sections
    
    Example:
        prd = {...}
        validation = validate_prd_completeness(json.dumps(prd))
        if not validation["is_complete"]:
            print(f"Missing: {validation['missing_sections']}")
    """
    try:
        prd = json.loads(prd_data)
        
        required_sections = [
            "project_name", "version", "overview", "goals",
            "target_users", "features", "acceptance_criteria"
        ]
        
        missing = [s for s in required_sections if s not in prd or not prd[s]]
        
        return {
            "is_complete": len(missing) == 0,
            "missing_sections": missing,
            "present_sections": [s for s in required_sections if s in prd and prd[s]],
            "completeness_score": (len(required_sections) - len(missing)) / len(required_sections),
            "recommendation": "All sections present" if len(missing) == 0 else f"Add missing sections: {', '.join(missing)}"
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def validate_user_story(story_data: str) -> dict:
    """
    Validate user story follows INVEST principles.
    
    Use this to ensure story quality before saving.
    
    Args:
        story_data: User story as JSON string
    
    Returns:
        Validation results with quality score
    
    Example:
        story = {"title": "Login", "description": "...", ...}
        validation = validate_user_story(json.dumps(story))
        print(f"Quality score: {validation['quality_score']}/5")
    """
    try:
        story = json.loads(story_data)
        
        invest_checks = {
            "has_title": "title" in story and len(story["title"]) > 0,
            "has_description": "description" in story and len(story["description"]) > 10,
            "has_acceptance_criteria": "acceptance_criteria" in story and len(story.get("acceptance_criteria", [])) > 0,
            "has_story_points": "story_points" in story,
            "has_priority": "priority" in story
        }
        
        quality_score = sum(invest_checks.values())
        missing_fields = [k.replace("has_", "") for k, v in invest_checks.items() if not v]
        
        return {
            "is_valid": quality_score >= 3,
            "quality_score": quality_score,
            "max_score": 5,
            "checks_passed": invest_checks,
            "missing_fields": missing_fields,
            "recommendation": "Story meets minimum quality" if quality_score >= 3 else f"Add: {', '.join(missing_fields)}"
        }
    except Exception as e:
        return {"error": str(e)}
