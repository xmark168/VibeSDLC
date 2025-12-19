import json
import logging

from sqlmodel import Session

from ..state import BAState
from app.core.db import engine
from app.models import Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

async def _save_prd_artifact(state: BAState, agent, project_files) -> dict:
    """Save PRD to database and file system.
    
    Returns:
        dict with prd_artifact_id, prd_saved, summary, next_steps, error
    """
    result = {"prd_artifact_id": None, "prd_saved": False, "summary": "", "next_steps": [], "error": None}
    prd_data = state.get("prd_draft")
    
    if not prd_data or not agent:
        return result
    
    try:
        project_name = prd_data.get("project_name", "Project")
        
        # Save to Artifact table
        with Session(engine) as session:
            service = ArtifactService(session)
            artifact = service.create_artifact(
                project_id=agent.project_id,
                agent_id=agent.agent_id,
                agent_name=agent.name,
                artifact_type=ArtifactType.PRD,
                title=project_name,
                content=prd_data,
                description=f"PRD for {project_name}",
                save_to_file=False
            )
            result["prd_artifact_id"] = str(artifact.id)
        
        # Save markdown for human reading
        if project_files:
            await project_files.save_prd(prd_data)
        
        result["prd_saved"] = True
        result["summary"] = f"PRD '{project_name}' saved successfully"
        result["next_steps"] = ["Review PRD document", "Approve to create user stories", "Or request edits"]
        
        # Send message to user - use message from LLM response instead of separate call
        is_update = bool(state.get("change_summary"))
        prd_message = state.get("prd_message", "")
        
        # Fallback message if LLM didn't generate one
        if not prd_message:
            prd_message = f"Mình đã cập nhật PRD theo yêu cầu của bạn rồi nhé!" if is_update else f"Tuyệt vời! 🎉 Mình đã hoàn thành PRD cho dự án '{project_name}' rồi!"
        
        await agent.message_user(
            event_type="response",
            content=prd_message,
            details={"message_type": "prd_created", "file_path": "docs/prd.md", "title": project_name, "artifact_id": result["prd_artifact_id"]}
        )
        
        logger.info(f"[BA] PRD saved: {project_name} (artifact_id={result['prd_artifact_id']})")
        
    except Exception as e:
        logger.error(f"[BA] Failed to save PRD: {e}", exc_info=True)
        result["error"] = f"Failed to save PRD: {str(e)}"
    
    return result




async def _save_stories_artifact(state: BAState, agent, project_files) -> dict:
    """Save stories to database and file system.
    
    Returns:
        dict with stories_artifact_id, stories_saved, summary, next_steps, error
    """
    result = {"stories_artifact_id": None, "stories_saved": False, "summary": "", "next_steps": [], "error": None}
    
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    is_stories_approved = state.get("stories_approved", False) or bool(state.get("created_epics"))
    intent = state.get("intent", "")
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories", "story_edit_single"]
    
    if not (epics_data or stories_data) or not project_files or is_stories_approved or not is_story_intent:
        return result
    
    try:
        await project_files.save_user_stories(epics_data, stories_data)
        result["stories_saved"] = True
        
        epics_count = len(epics_data)
        stories_count = len(stories_data)
        
        # Save to Artifact table
        if agent:
            with Session(engine) as session:
                service = ArtifactService(session)
                # Include approval_message so it can be loaded when user approves later
                approval_message = state.get("stories_approval_message", "")
                artifact_content = {
                    "epics": epics_data, 
                    "stories": stories_data, 
                    "epics_count": epics_count, 
                    "stories_count": stories_count,
                    "approval_message": approval_message  # Save for later use in approve_stories
                }
                artifact = service.create_artifact(
                    project_id=agent.project_id,
                    agent_id=agent.agent_id,
                    agent_name=agent.name,
                    artifact_type=ArtifactType.USER_STORIES,
                    title="User Stories",
                    content=artifact_content,
                    description=f"{epics_count} epics with {stories_count} stories",
                    save_to_file=False
                )
                result["stories_artifact_id"] = str(artifact.id)
        
        result["summary"] = f"Extracted {epics_count} epics with {stories_count} INVEST-compliant stories"
        result["next_steps"] = ["Review epics and prioritize stories", "Approve to add to backlog"]
        
        # Send message to user - use message from state (already filled from LLM template)
        if agent:
            stories_message = state.get("stories_message", "")
            logger.info(f"[BA] _save_stories_artifact: stories_message from state = '{stories_message[:50] if stories_message else 'EMPTY'}...'")
            
            # Fallback only if state somehow doesn't have message (shouldn't happen normally)
            if not stories_message:
                stories_message = f"Xong rồi! 🚀 Mình đã tạo {stories_count} User Stories từ {epics_count} Epics. Bạn xem qua và phê duyệt nhé!"
                logger.warning(f"[BA] _save_stories_artifact: stories_message was empty, using fallback")
            
            await agent.message_user(
                event_type="response",
                content=stories_message,
                details={"message_type": "stories_created", "file_path": "docs/user-stories.md", "epics_count": epics_count, "stories_count": stories_count, "status": "pending"}
            )
        
        logger.info(f"[BA] Saved {epics_count} epics with {stories_count} user stories (pending approval)")
        
    except Exception as e:
        logger.error(f"[BA] Failed to save stories: {e}", exc_info=True)
        result["error"] = f"Failed to save stories: {str(e)}"
    
    return result




async def save_artifacts(state: BAState, agent=None) -> dict:
    """Node: Save PRD/stories to database and file system."""
    logger.info(f"[BA] Saving artifacts...")
    
    result = {
        "action_taken": state.get("intent", "unknown"),
        "summary": "",
        "next_steps": [],
        "prd_artifact_id": None
    }
    
    project_files = agent.project_files if agent else None
    
    # Save PRD using helper
    prd_result = await _save_prd_artifact(state, agent, project_files)
    if prd_result.get("prd_saved"):
        result.update({
            "prd_artifact_id": prd_result["prd_artifact_id"],
            "prd_saved": True,
            "summary": prd_result["summary"],
        })
        result["next_steps"].extend(prd_result["next_steps"])
    if prd_result.get("error"):
        result["error"] = prd_result["error"]
    
    # Save stories using helper
    stories_result = await _save_stories_artifact(state, agent, project_files)
    if stories_result.get("stories_saved"):
        result.update({
            "stories_artifact_id": stories_result["stories_artifact_id"],
            "stories_saved": True,
            "summary": stories_result["summary"],
        })
        result["next_steps"].extend(stories_result["next_steps"])
    if stories_result.get("error"):
        result["error"] = stories_result["error"]
    
    # Handle case where story extraction failed (no stories returned)
    intent = state.get("intent", "")
    is_story_intent = intent in ["extract_stories", "stories_update", "update_stories"]
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    if is_story_intent and not epics_data and not stories_data and agent and not stories_result.get("stories_saved"):
        error_msg = state.get("error", "Không thể tạo stories từ PRD.")
        logger.warning(f"[BA] Story extraction failed: {error_msg}")
        result["error"] = error_msg
        await agent.message_user(
            event_type="response",
            content=f"Hmm, mình gặp chút vấn đề khi tạo stories nè. Bạn thử kiểm tra lại PRD hoặc nhờ mình thử lại nhé!",
            details={
                "message_type": "error",
                "error": error_msg
            }
        )
    
    # Interview questions sent
    if state.get("questions_sent"):
        questions_count = len(state.get("questions", []))
        result["summary"] = f"Sent {questions_count} clarification questions to user"
        result["next_steps"].append("Wait for user answers to continue")
    
    # Domain analysis - internal process, don't send message to user
    # The analysis helps generate better PRD/stories, but users don't need to see it
    if state.get("analysis_text") and not state.get("error"):
        result["summary"] = "Domain analysis completed"
        result["analysis"] = state["analysis_text"]
        # Don't send "Mình đã phân tích xong domain" message - it's confusing for users
    
    # PRD update - show updated PRD card (same as create, no extra text message)
    if state.get("change_summary"):
        result["change_summary"] = state["change_summary"]
        # Card is already shown in the PRD save section above
    
    # Stories approved - only save to DB, notify Kanban to refresh (no card)
    stories_approved_flag = state.get("stories_approved", False)
    created_epics_list = state.get("created_epics", [])
    logger.info(f"[BA] Checking stories_approved: flag={stories_approved_flag}, created_epics={len(created_epics_list)}")
    
    if stories_approved_flag or created_epics_list:
        approval_message = state.get("approval_message", "Epics & Stories đã được phê duyệt")
        
        result["summary"] = approval_message
        result["stories_approved"] = True
        result["created_epics"] = created_epics_list
        result["created_stories"] = state.get("created_stories", [])
        
        # Send simple notification to trigger Kanban refresh (no card displayed)
        # Use approval_message from LLM response (generated during story extraction/update)
        if agent:
            logger.info(f"[BA] Sending stories_approved message to frontend")
            stories_count = len(state.get("created_stories", []))
            epics_count = len(created_epics_list)
            
            # Get approval message from state (already filled from LLM template)
            approved_message = state.get("stories_approval_message", "")
            logger.info(f"[BA] save_artifacts: stories_approval_message from state = '{approved_message[:50] if approved_message else 'EMPTY'}...'")
            
            # Fallback only if state somehow doesn't have message (shouldn't happen normally)
            if not approved_message:
                approved_message = f"Tuyệt vời! 🎊 Đã thêm {epics_count} Epics và {stories_count} Stories vào backlog rồi!"
                logger.warning(f"[BA] save_artifacts: stories_approval_message was empty, using fallback")
            
            await agent.message_user(
                event_type="response",
                content=approved_message,
                details={
                    "message_type": "stories_approved",  # Frontend will refresh Kanban, no card
                    "task_completed": True  # Signal to release ownership
                }
            )
    
    logger.info(f"[BA] Artifacts saved: {result['summary']}")
    
    # Determine if task is truly complete (should release ownership)
    # ONLY release ownership when stories are APPROVED (final step in BA workflow)
    # Keep ownership for: PRD create/update, stories pending approval, waiting for answer
    is_stories_approved = result.get("stories_approved", False)
    
    if is_stories_approved:
        result["task_completed"] = True
        logger.info(f"[BA] Stories approved - task completed, will release ownership")
    else:
        logger.info(f"[BA] Task not complete yet, keeping ownership (stories_approved={is_stories_approved})")
    
    return {
        "result": result,
        "is_complete": True
    }


# =============================================================================
# STORY VERIFY NODE - Simple 1-Phase LLM
# =============================================================================



