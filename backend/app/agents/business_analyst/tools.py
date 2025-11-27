"""Business Analyst Tools for File Operations.

Tools for BA sub-agents to interact with PRD and User Stories files.
Provides synchronous interface to async ProjectFiles operations.
"""

from crewai.tools import tool
from pathlib import Path
import json
from typing import Optional, Any


# ==================== Helper Functions ====================

def _run_async(coro):
    """Run async coroutine in sync context.
    
    Bridges async ProjectFiles methods to sync CrewAI tools.
    Uses nest_asyncio to allow nested event loops.
    """
    import asyncio
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


def _get_project_files(project_path: str):
    """Get ProjectFiles instance for project path.
    
    Args:
        project_path: Path to project directory
        
    Returns:
        ProjectFiles instance
    """
    from app.utils.project_files import ProjectFiles
    from pathlib import Path
    return ProjectFiles(Path(project_path))


def _parse_json(json_str: str, field_name: str = "data"):
    """Parse JSON string with error handling.
    
    Args:
        json_str: JSON string to parse
        field_name: Field name for error message
        
    Returns:
        tuple: (parsed_data, error_dict)
        - On success: (data, None)
        - On error: (None, error_dict)
    """
    try:
        return json.loads(json_str), None
    except json.JSONDecodeError as e:
        return None, {"success": False, "error": f"Invalid {field_name} JSON: {str(e)}"}


def _error_response(message: str, **kwargs) -> dict:
    """Create standardized error response."""
    return {"success": False, "error": message, **kwargs}


def _success_response(message: str, **kwargs) -> dict:
    """Create standardized success response."""
    return {"success": True, "message": message, **kwargs}


# ==================== User Interaction Tools ====================

@tool
def ask_user_question(question: str, question_type: str = "open", options: str = "", agent_id: str = "") -> dict:
    """
    Ask the user a clarification question and wait for their answer.
    
    Use this when you need more information from the user to proceed with analysis.
    The question will be sent to the user immediately, and their answer will be
    available when the task resumes.
    
    Args:
        question: The question to ask the user (clear and specific)
        question_type: Type of question:
                      - "open": Free text response
                      - "multichoice": Pick one option from a list
                      - "multiselect": Pick multiple options from a list
                      - "yesno": Simple yes/no question
        options: For multichoice/multiselect only - comma-separated options
                Example: "OAuth,JWT,Session-based"
        agent_id: BA agent ID (auto-provided by crew)
    
    Returns:
        Dictionary with status:
        - On success: {"status": "question_sent", "question_id": "...", "message": "..."}
        - On error: {"error": "error message"}
    
    Examples:
        # Open question for free text
        result = ask_user_question(
            "What authentication methods do you need for this feature?",
            question_type="open"
        )
        
        # Multiple choice - user picks one
        result = ask_user_question(
            "Which authentication method would you prefer?",
            question_type="multichoice",
            options="OAuth 2.0,JWT tokens,Session-based,API keys"
        )
        
        # Multiple select - user picks several
        result = ask_user_question(
            "Which features are required? (select all that apply)",
            question_type="multiselect",
            options="Login,Registration,Password Reset,2FA,Social Login"
        )
        
        # Yes/No question
        result = ask_user_question(
            "Do you need two-factor authentication (2FA)?",
            question_type="yesno"
        )
    
    Note:
        After sending the question, the current analysis will pause. When the user
        answers, the task will resume with the answer included in the context.
    """
    if not agent_id:
        return {
            "error": "agent_id required to send question",
            "note": "Make sure to pass agent_id parameter"
        }
    
    # Get BA agent from pool manager
    try:
        from uuid import UUID
        from app.api.routes.agent_management import _manager_registry
        
        # Convert agent_id string to UUID
        try:
            agent_uuid = UUID(agent_id)
        except (ValueError, AttributeError):
            return {"error": f"Invalid agent_id format: {agent_id}"}
        
        # Get pool manager (should only be one for universal pool)
        if not _manager_registry:
            return {"error": "Agent pool manager not initialized"}
        
        # Get agent from pool manager
        pool_manager = next(iter(_manager_registry.values()), None)
        if not pool_manager:
            return {"error": "No pool manager found"}
        
        agent = pool_manager.get_agent(agent_uuid)
        if not agent:
            return {"error": f"No agent found with ID {agent_id}"}
        
    except Exception as e:
        return {"error": f"Failed to get agent: {str(e)}"}
    
    # Now use the agent to send question
    try:
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        
        # Prepare question configuration
        question_config = {
            "question_type": question_type,
            "allow_multiple": question_type == "multiselect"
        }
        
        # Parse options if provided for multichoice/multiselect
        if options and question_type in ["multichoice", "multiselect"]:
            parsed_options = [opt.strip() for opt in options.split(",") if opt.strip()]
            if parsed_options:
                question_config["options"] = parsed_options
            else:
                return {
                    "error": f"Invalid options format. Provide comma-separated values.",
                    "example": "OAuth,JWT,Session"
                }
        elif question_type in ["multichoice", "multiselect"] and not options:
            return {
                "error": f"Options required for question_type '{question_type}'",
                "example": "ask_user_question('Pick one:', 'multichoice', 'Option1,Option2,Option3')"
            }
        
        # Send question via BaseAgent's message_user method
        question_id = loop.run_until_complete(
            agent.message_user(
                event_type="question",
                content=question,
                question_config=question_config
            )
        )
        
        if not question_id:
            return {"error": "Failed to send question to user. Check agent logs."}
        
        return {
            "status": "question_sent",
            "question_id": str(question_id),
            "message": f"Question sent to user successfully.",
            "note": "The user's answer will be available when the task resumes. Continue with available information or indicate you need the answer."
        }
        
    except Exception as e:
        return {
            "error": f"Failed to ask question: {str(e)}",
            "question": question,
            "question_type": question_type
        }


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
    try:
        pf = _get_project_files(project_path)
        prd = _run_async(pf.load_prd())
        return prd or {}
    except Exception as e:
        return _error_response(f"Failed to load PRD: {str(e)}")


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
    prd_dict, error = _parse_json(prd_data, "PRD")
    if error:
        return error
    
    try:
        pf = _get_project_files(project_path)
        path = _run_async(pf.save_prd(prd_dict))
        return _success_response(
            "PRD saved successfully",
            prd_json_path=str(path.parent / "prd.json"),
            prd_md_path=str(path)
        )
    except Exception as e:
        return _error_response(f"Failed to save PRD: {str(e)}")


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
    section_data, error = _parse_json(new_content, "section")
    if error:
        return error
    
    try:
        pf = _get_project_files(project_path)
        prd = _run_async(pf.load_prd())
        
        if not prd:
            return _error_response("PRD not found")
        
        prd[section_name] = section_data
        prd["change_summary"] = f"Updated {section_name}"
        
        path = _run_async(pf.save_prd(prd))
        return _success_response(
            f"Section '{section_name}' updated",
            section_updated=section_name,
            prd_path=str(path)
        )
    except Exception as e:
        return _error_response(f"Failed to update section: {str(e)}")


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
    try:
        pf = _get_project_files(project_path)
        stories = _run_async(pf.load_user_stories())
        return stories or []
    except Exception as e:
        return [_error_response(f"Failed to load stories: {str(e)}")]


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
    stories_list, error = _parse_json(stories_data, "stories")
    if error:
        return error
    
    if not isinstance(stories_list, list):
        return _error_response("stories_data must be an array")
    
    try:
        pf = _get_project_files(project_path)
        path = _run_async(pf.save_user_stories(stories_list))
        return _success_response(
            f"Saved {len(stories_list)} user stories",
            stories_count=len(stories_list),
            stories_md_path=str(path)
        )
    except Exception as e:
        return _error_response(f"Failed to save stories: {str(e)}")


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
    new_story, error = _parse_json(story_data, "story")
    if error:
        return error
    
    try:
        pf = _get_project_files(project_path)
        stories = _run_async(pf.load_user_stories()) or []
        
        stories.append(new_story)
        path = _run_async(pf.save_user_stories(stories))
        
        return _success_response(
            f"Story '{new_story.get('title', 'Untitled')}' added",
            story_added=new_story.get("title", "Untitled"),
            total_stories=len(stories),
            stories_path=str(path)
        )
    except Exception as e:
        return _error_response(f"Failed to add story: {str(e)}")


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
    prd, error = _parse_json(prd_data, "PRD")
    if error:
        return error
    
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
    story, error = _parse_json(story_data, "story")
    if error:
        return error
    
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
