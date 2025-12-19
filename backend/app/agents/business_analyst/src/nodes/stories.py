import json
import logging
import os
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from sqlmodel import Session, func, select
from sqlalchemy.orm.attributes import flag_modified

from app.core.agent.llm_factory import get_llm, create_llm, MODELS

from ..state import BAState
from ..schemas import (
    IntentOutput,
    QuestionsOutput,
    PRDOutput,
    PRDUpdateOutput,
    DocumentAnalysisOutput,
    EpicsOnlyOutput,
    StoriesForEpicOutput,
    FullStoriesOutput,
    VerifyStoryOutput,
    DocumentFeedbackOutput,
    SingleStoryEditOutput,
    FeatureClarityOutput,
)
from app.core.agent.prompt_utils import (
    load_prompts_yaml,
    extract_agent_personality,
)

# Load prompts from YAML (same pattern as Developer V2)
PROMPTS = load_prompts_yaml(Path(__file__).parent.parent / "prompts.yaml")

# Default values for BA agent persona
BA_DEFAULTS = {
    "name": "Business Analyst",
    "role": "Business Analyst / Requirements Specialist",
    "goal": "Phân tích requirements, tạo PRD và user stories",
    "description": "Chuyên gia phân tích yêu cầu phần mềm",
    "personality": "Thân thiện, kiên nhẫn, giỏi lắng nghe",
    "communication_style": "Đơn giản, dễ hiểu, tránh thuật ngữ kỹ thuật",
}
from app.core.db import engine
from app.core.config import settings
from app.models import AgentQuestion, Epic, Story, StoryStatus, StoryType, EpicStatus, ArtifactType
from app.services.artifact_service import ArtifactService
from app.kafka import KafkaTopics, get_kafka_producer
from app.kafka.event_schemas import AgentEvent

logger = logging.getLogger(__name__)

from .utils import _get_llm, _invoke_structured, _cfg, _sys_prompt, _user_prompt, _save_interview_state_to_question, _default_llm, _fast_llm, _story_llm

async def _generate_stories_for_epic(
    epic: dict, 
    prd: dict, 
    all_epic_ids: list, 
    state: BAState, 
    agent=None
) -> dict:
    """Generate stories for a single Epic (used in parallel batch processing).
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    epic_id = epic.get("id", "EPIC-???")
    epic_title = epic.get("title", "Unknown")
    
    logger.info(f"[BA] Generating stories for Epic: {epic_title}")
    
    # Find related features from PRD
    feature_refs = epic.get("feature_refs", [])
    prd_features = []
    for feature in prd.get("features", []):
        feature_name = feature.get("name") if isinstance(feature, dict) else str(feature)
        if feature_name in feature_refs:
            prd_features.append(feature)
    
    # If no feature_refs matched, include all features for this epic
    if not prd_features:
        prd_features = prd.get("features", [])
    
    system_prompt = _sys_prompt(agent, "generate_stories_for_epic")
    user_prompt = _user_prompt(
        "generate_stories_for_epic",
        epic_id=epic_id,
        epic_title=epic_title,
        epic_domain=epic.get("domain", "General"),
        epic_description=epic.get("description", ""),
        prd_features=json.dumps(prd_features, ensure_ascii=False, indent=2),
        all_epic_ids=", ".join(all_epic_ids)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    logger.info(f"[BA] Calling LLM for Epic '{epic_title}' with {len(prd_features)} features")
    
    result = await _invoke_structured(
        llm=_story_llm,
        schema=StoriesForEpicOutput,
        messages=messages,
        config=_cfg(state, f"generate_stories_{epic_id}"),
        fallback_data={"stories": []}
    )
    
    # Convert Pydantic UserStory objects to dicts
    stories = []
    for s in result.get("stories", []):
        if hasattr(s, "model_dump"):
            story_dict = s.model_dump()
        elif isinstance(s, dict):
            story_dict = s
        else:
            continue
        # Add epic info to each story
        story_dict["epic_id"] = epic_id
        story_dict["epic_title"] = epic_title
        stories.append(story_dict)
    
    logger.info(f"[BA] Generated {len(stories)} stories for Epic '{epic_title}'")
    return {"epic_id": epic_id, "stories": stories}




async def extract_stories(state: BAState, agent=None) -> dict:
    """Node: Extract epics with INVEST-compliant user stories from PRD.
    
    Uses BATCH PROCESSING for better performance:
    - Phase 1: Extract Epics only (fast, ~5s)
    - Phase 2: Generate stories for each Epic in PARALLEL (~15s total instead of ~60s)
    """
    import asyncio
    
    logger.info(f"[BA] Extracting epics and user stories (batch mode)...")
    
    prd = state.get("prd_draft") or state.get("existing_prd", {})
    
    if not prd:
        logger.error("[BA] No PRD available to extract stories from")
        return {
            "epics": [],
            "stories": [],
            "error": "No PRD available. Please create a PRD first."
        }
    
    # Check if PRD is simple (few features) - use single call instead of batch
    features_count = len(prd.get("features", []))
    use_batch = features_count >= 3  # Use batch for 3+ features
    
    if not use_batch:
        # Simple PRD - use single call (original method)
        logger.info(f"[BA] Using single-call mode for simple PRD ({features_count} features)")
        return await _extract_stories_single_call(state, agent, prd)
    
    logger.info(f"[BA] Using batch mode for complex PRD ({features_count} features)")
    
    try:
        # =============================================
        # PHASE 1: Extract Epics only (fast call ~5s)
        # Uses structured output for reliable parsing
        # =============================================
        logger.info("[BA] Phase 1: Extracting Epics structure...")
        
        system_prompt = _sys_prompt(agent, "extract_epics_only")
        user_prompt = _user_prompt(
            "extract_epics_only",
            prd=json.dumps(prd, ensure_ascii=False, indent=2)
        )
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        epics_result = await _invoke_structured(
            llm=_fast_llm,
            schema=EpicsOnlyOutput,
            messages=messages,
            config=_cfg(state, "extract_epics_only"),
            fallback_data={"epics": [], "message_template": "", "approval_template": ""}
        )
        
        # Convert Pydantic Epic objects to dicts
        epics = []
        for e in epics_result.get("epics", []):
            if hasattr(e, "model_dump"):
                epics.append(e.model_dump())
            elif isinstance(e, dict):
                epics.append(e)
        
        message_template = epics_result.get("message_template", "")
        approval_template = epics_result.get("approval_template", "")
        
        if not epics:
            logger.warning("[BA] No epics extracted, falling back to single call")
            return await _extract_stories_single_call(state, agent, prd)
        
        logger.info(f"[BA] Phase 1 complete: {len(epics)} Epics extracted, message_template: {message_template[:50] if message_template else 'none'}...")
        
        # =============================================
        # PHASE 2: Generate stories for each Epic IN PARALLEL
        # =============================================
        logger.info(f"[BA] Phase 2: Generating stories for {len(epics)} Epics in parallel...")
        
        all_epic_ids = [epic.get("id", "") for epic in epics]
        
        # Use semaphore to limit concurrent LLM calls (avoid rate limiting)
        # Increased from 5 to 7 to process all epics in one batch
        MAX_CONCURRENT_LLM_CALLS = 7
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
        
        async def _generate_with_semaphore(epic):
            async with semaphore:
                return await _generate_stories_for_epic(epic, prd, all_epic_ids, state, agent)
        
        # Create tasks with rate limiting
        tasks = [_generate_with_semaphore(epic) for epic in epics]
        
        # Run all epics in parallel (limited by semaphore)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all stories and update epics
        all_stories = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"[BA] Error generating stories for Epic {i}: {result}")
                continue
            
            epic_id = result.get("epic_id")
            stories = result.get("stories", [])
            
            # Find and update the epic with its stories
            for epic in epics:
                if epic.get("id") == epic_id:
                    epic["stories"] = stories
                    break
            
            # Add to flat list
            all_stories.extend(stories)
        
        total_epics = len(epics)
        total_stories = len(all_stories)
        logger.info(f"[BA] Batch extraction complete: {total_epics} epics with {total_stories} stories")
        
        # If batch mode generated no stories, fall back to single call
        if total_stories == 0 and total_epics > 0:
            logger.warning(f"[BA] Batch mode generated 0 stories for {total_epics} epics, falling back to single call")
            return await _extract_stories_single_call(state, agent, prd)
        
        # Use hardcoded messages (LLM-generated templates were unreliable - often mentioned "Phase 2" incorrectly)
        message = f"Đã tạo xong {total_stories} User Stories từ {total_epics} Epics! Bạn xem qua và bấm 'Phê duyệt Stories' để thêm vào backlog nhé!"
        approval_message = f"Đã phê duyệt và thêm {total_epics} Epics, {total_stories} Stories vào backlog!"
        
        logger.info(f"[BA] Stories message: {message[:50]}...")
        
        return {
            "epics": epics,
            "stories": all_stories,
            "stories_message": message,
            "stories_approval_message": approval_message
        }
        
    except Exception as e:
        logger.error(f"[BA] Batch extraction failed: {e}, falling back to single call")
        return await _extract_stories_single_call(state, agent, prd)




async def _extract_stories_single_call(state: BAState, agent, prd: dict) -> dict:
    """Original single-call story extraction (fallback for simple PRDs).
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    """
    system_prompt = _sys_prompt(agent, "extract_stories")
    user_prompt = _user_prompt(
        "extract_stories",
        prd=json.dumps(prd, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_story_llm,
        schema=FullStoriesOutput,
        messages=messages,
        config=_cfg(state, "extract_stories"),
        fallback_data={"epics": [], "message_template": "", "approval_template": "", "change_summary": ""}
    )
    
    # Convert Pydantic Epic objects to dicts
    epics = []
    for e in result.get("epics", []):
        if hasattr(e, "model_dump"):
            epics.append(e.model_dump())
        elif isinstance(e, dict):
            epics.append(e)
    
    message_template = result.get("message_template", "")
    approval_template = result.get("approval_template", "")
    
    # Flatten stories for backward compatibility
    all_stories = []
    for epic in epics:
        stories_in_epic = epic.get("stories", [])
        epic_title = epic.get("title", epic.get("name", "Unknown"))
        for story in stories_in_epic:
            if hasattr(story, "model_dump"):
                story = story.model_dump()
            story["epic_id"] = epic.get("id")
            story["epic_title"] = epic_title
            all_stories.append(story)
    
    total_epics = len(epics)
    total_stories = len(all_stories)
    logger.info(f"[BA] Single-call extraction: {total_epics} epics, {total_stories} stories")
    
    # Use hardcoded messages (LLM templates unreliable)
    message = f"Đã tạo xong {total_stories} User Stories từ {total_epics} Epics! Bạn xem qua và bấm 'Phê duyệt Stories' để thêm vào backlog nhé!"
    approval_message = f"Đã phê duyệt và thêm {total_epics} Epics, {total_stories} Stories vào backlog!"
    
    return {
        "epics": epics,
        "stories": all_stories,
        "stories_message": message,
        "stories_approval_message": approval_message
    }




async def update_stories(state: BAState, agent=None) -> dict:
    """Node: Update existing Epics and Stories based on user feedback.
    
    Uses structured output for reliable parsing (Developer V2 pattern).
    
    FLOW:
    1. Check request clarity → ask clarification if vague
    2. Send to LLM for update
    3. Validate no duplicates created
    
    OPTIMIZATION: If user mentions specific page/domain (e.g., "thêm menu ở homepage"),
    only send RELEVANT epics to LLM instead of all epics (avoids timeout on large projects).
    """
    logger.info(f"[BA] Updating stories based on user feedback...")
    
    all_epics = state.get("epics", [])
    if not all_epics:
        return {"error": "No existing stories to update"}
    
    user_message = state.get("user_message", "")
    existing_prd = state.get("existing_prd")
    skip_clarity_check = state.get("skip_clarity_check", False)
    
    # ====================================================================================
    # STEP 0: CLASSIFY CRUD OPERATION - Determine what user wants to do
    # This simplifies routing and reduces unnecessary checks
    # ====================================================================================
    crud_operation, crud_confidence = _classify_crud_operation(user_message)
    logger.info(f"[BA] CRUD classification: {crud_operation} (confidence: {crud_confidence:.2f})")
    
    # ====================================================================================
    # STEP 1: UNIFIED DUPLICATE DETECTION - Check if feature/story already exists
    # This combines story-level and epic-level checks into one unified flow
    # ====================================================================================
    # SKIP this check for DELETE/UPDATE operations (they are explicit, no need to check duplicates)
    user_msg_lower = user_message.lower()
    is_deletion_request = crud_operation == "DELETE"
    is_update_request = crud_operation == "UPDATE"
    
    # For CREATE operations, check if similar functionality already exists
    # This prevents duplicate stories and helps user refine existing ones
    if not skip_clarity_check and crud_operation == "CREATE":
        user_keywords = _extract_intent_keywords(user_message)
        
        # LEVEL 1: Check for existing STORIES (most specific)
        matching_stories = []
        for epic in all_epics:
            for story in epic.get("stories", []):
                story_text = (
                    f"{story.get('title', '')} {story.get('description', '')} "
                    f"{' '.join(story.get('requirements', []))}"
                ).lower()
                
                # Check if user keywords appear in story
                matches = sum(1 for kw in user_keywords if kw in story_text)
                if matches >= 2:  # At least 2 keywords match
                    matching_stories.append({
                        "story": story,
                        "epic_id": epic.get("id"),
                        "epic_title": epic.get("title"),
                        "epic_domain": epic.get("domain"),
                        "match_score": matches / len(user_keywords) if user_keywords else 0
                    })
        
        # LEVEL 2: Check for existing EPICS (broader scope)
        matching_epics = []
        for epic in all_epics:
            epic_text = f"{epic.get('title', '')} {epic.get('domain', '')} {epic.get('description', '')}".lower()
            matches = sum(1 for kw in user_keywords if kw in epic_text)
            if matches >= 1:  # At least 1 keyword match for epic
                matching_epics.append({
                    "epic": epic,
                    "match_score": matches / len(user_keywords) if user_keywords else 0
                })
        
        # DECISION LOGIC: What to do with matches?
        if matching_stories and agent:
            # CASE A: Found specific story → Ask user to refine it (most specific)
            matching_stories.sort(key=lambda x: x["match_score"], reverse=True)
            best_match = matching_stories[0]
            story = best_match["story"]
            
            logger.info(f"[BA] Found existing story: {story.get('id')} - {story.get('title')} (score: {best_match['match_score']:.2f})")
            
            # SMART MESSAGE: Tell user story exists, ask what to add
            existing_story_msg = (
                f"🔍 Mình tìm thấy story \"{story.get('title', '')}\" (ID: {story.get('id')}) "
                f"trong epic \"{best_match['epic_title']}\" có vẻ đã cover chức năng này rồi.\n\n"
                f"Bạn muốn bổ sung gì vào story này? (Ví dụ: thêm requirement, acceptance criteria, ...)"
            )
            
            await agent.message_user("response", existing_story_msg)
            
            # Return early - STOP the flow (waiting for user to clarify what to add)
            return {
                "found_existing_story": True,
                "existing_story_id": story.get("id"),
                "existing_story_title": story.get("title"),
                "existing_epic_id": best_match["epic_id"],
                "awaiting_user_decision": True,
                "is_complete": True,
                "result": {
                    "summary": f"Found existing story '{story.get('title')}' - awaiting user clarification",
                    "task_completed": False
                }
            }
        
        elif matching_epics and agent:
            # CASE B: Found epic but no specific story → This is REFINEMENT (add to existing epic)
            matching_epics.sort(key=lambda x: x["match_score"], reverse=True)
            best_epic = matching_epics[0]["epic"]
            
            logger.info(f"[BA] Found existing epic: {best_epic.get('title')} (score: {matching_epics[0]['match_score']:.2f}) - will refine it")
            
            # NO NEED TO ASK - This is clearly a refinement of existing epic
            # Just proceed to add story to this epic (skip clarity check)
            logger.info(f"[BA] Refinement detected - will add new story to epic '{best_epic.get('title')}'")
            # Continue to STEP 3 (skip STEP 2 clarity check)
    
    # ====================================================================================
    # STEP 2: CHECK CLARITY - Ask clarification ONLY for CREATE operations on NEW features
    # DELETE/UPDATE operations are always clear (user explicitly states what to modify/remove)
    # ====================================================================================
    # SKIP clarity check for:
    # 1. DELETE operations (always explicit: "xóa epic X")
    # 2. UPDATE operations (always explicit: "sửa story Y")
    # 3. Resuming from previous clarification (skip_clarity_check=True)
    # 4. Found matching epic in STEP 1 (this is REFINEMENT, not NEW feature)
    
    # Check if we found matching epic in STEP 1 (CASE B)
    found_matching_epic = False
    if crud_operation == "CREATE" and not skip_clarity_check:
        user_keywords = _extract_intent_keywords(user_message)
        for epic in all_epics:
            epic_text = f"{epic.get('title', '')} {epic.get('domain', '')}".lower()
            matches = sum(1 for kw in user_keywords if kw in epic_text)
            if matches >= 1:
                found_matching_epic = True
                logger.info(f"[BA] Found matching epic '{epic.get('title')}' - treating as REFINEMENT")
                break
    
    should_skip_clarity = (
        skip_clarity_check or 
        crud_operation == "DELETE" or 
        crud_operation == "UPDATE" or
        found_matching_epic  # NEW: Skip if found matching epic (REFINEMENT)
    )
    
    if should_skip_clarity:
        if crud_operation == "DELETE":
            logger.info(f"[BA] Skipping clarity check (DELETE operation - always clear)")
        elif crud_operation == "UPDATE":
            logger.info(f"[BA] Skipping clarity check (UPDATE operation - always clear)")
        elif found_matching_epic:
            logger.info(f"[BA] Skipping clarity check (found matching epic - this is REFINEMENT)")
        else:
            logger.info(f"[BA] Skipping clarity check (resuming from clarification)")
        is_clear = True
        missing_details = []
        related_feature = None
    else:
        # Only CREATE operations on COMPLETELY NEW features need clarity check
        logger.info(f"[BA] CREATE operation on NEW feature - checking for clarification needs")
        is_clear, missing_details, related_feature = await _check_request_clarity(
            user_message, all_epics, existing_prd, agent
        )
    
    if not is_clear and agent:
        # Request needs clarification - either NEW feature or EXISTING without specific change
        logger.info(f"[BA] Clarification needed (related_feature={related_feature}): {missing_details}")
        
        # Build context message
        if related_feature:
            # EXISTING feature → use simple open question (missing_details is list of strings)
            context_msg = f"Tính năng \"{related_feature}\" đã có trong hệ thống. Mình cần biết thêm chi tiết để cập nhật."
            batch_questions = [
                {
                    "question_text": detail,
                    "question_type": "open",
                    "options": None,
                    "allow_multiple": False,
                    "context": context_msg if i == 0 else None,
                }
                for i, detail in enumerate(missing_details)
            ]
        else:
            # NEW feature → generate multichoice questions specific to this feature
            logger.info(f"[BA] NEW feature detected, generating feature-specific multichoice questions...")
            context_msg = f"Để mình hiểu rõ hơn về \"{user_message}\", bạn cho mình biết thêm nhé!"
            
            # Generate multichoice questions using LLM (specific to the new feature, not general interview)
            try:
                system_prompt = _sys_prompt(agent, "generate_feature_questions")
                user_prompt = _user_prompt(
                    "generate_feature_questions",
                    user_message=user_message
                )
                
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt)
                ]
                
                result = await _invoke_structured(
                    llm=_default_llm,
                    schema=QuestionsOutput,
                    messages=messages,
                    config=_cfg(state, "generate_feature_questions"),
                    fallback_data={"questions": []}
                )
                
                generated_questions = []
                for q in result.get("questions", []):
                    if hasattr(q, "model_dump"):
                        q_dict = q.model_dump()
                    elif isinstance(q, dict):
                        q_dict = q
                    else:
                        continue
                    
                    # Ensure multichoice type
                    if q_dict.get("type") != "multichoice":
                        q_dict["type"] = "multichoice"
                    if not q_dict.get("options"):
                        q_dict["options"] = ["Có", "Không", "Khác (vui lòng mô tả)"]
                    
                    generated_questions.append(q_dict)
                
                if generated_questions:
                    batch_questions = [
                        {
                            "question_text": q["text"],
                            "question_type": q.get("type", "multichoice"),
                            "options": q.get("options"),
                            "allow_multiple": q.get("allow_multiple", False),
                            "context": context_msg if i == 0 else None,
                        }
                        for i, q in enumerate(generated_questions)
                    ]
                else:
                    raise ValueError("No questions generated")
                    
            except Exception as e:
                logger.warning(f"[BA] Failed to generate feature-specific questions: {e}, using fallback")
                # Fallback: use simple open questions
                batch_questions = [
                    {
                        "question_text": detail,
                        "question_type": "open",
                        "options": None,
                        "allow_multiple": False,
                        "context": context_msg if i == 0 else None,
                    }
                    for i, detail in enumerate(missing_details)
                ]
        
        logger.info(f"[BA] Sending {len(batch_questions)} clarification questions via question cards...")
        
        # Send questions using question cards
        question_ids = await agent.ask_multiple_clarification_questions(batch_questions)
        
        # Save interview state with original_intent so RESUME knows to continue stories_update
        with Session(engine) as session:
            interview_state = {
                "original_intent": "stories_update",
                "user_message": user_message,
                "existing_prd": existing_prd,
                "epics": all_epics,
                "questions": batch_questions,
                "question_ids": [str(qid) for qid in question_ids],
                "related_feature": related_feature,
            }
            _save_interview_state_to_question(session, question_ids[0], interview_state)
            logger.info(f"[BA] Saved stories_update state for RESUME flow")
        
        # Return early - STOP the flow (waiting for user answers)
        return {
            "needs_clarification": True,
            "waiting_for_answer": True,
            "question_ids": [str(qid) for qid in question_ids],
            "is_complete": True,
            "result": {
                "summary": f"Feature '{related_feature}' already exists - asked for specific changes" if related_feature else "New feature request - asked for clarification",
                "task_completed": False
            }
        }
    
    # ====================================================================================
    # STEP 3: PROCEED WITH UPDATE - Either resuming from clarification or request is clear
    # ====================================================================================
    user_message_lower = state["user_message"].lower()
    
    # SMART FILTERING: Detect if user mentions specific domain/page
    # If yes, only update that epic (much faster, avoids timeout)
    # SPECIAL HANDLING FOR DELETION: Find the epic to delete by matching keywords
    if is_deletion_request:
        # Extract keywords from user message to find target epic
        user_keywords = _extract_intent_keywords(user_message)
        
        # Find epic(s) that match the deletion request
        matching_epics_for_deletion = []
        for epic in all_epics:
            epic_text = f"{epic.get('title', '')} {epic.get('domain', '')} {epic.get('description', '')}".lower()
            matches = sum(1 for kw in user_keywords if kw in epic_text)
            if matches >= 1:  # At least 1 keyword match
                matching_epics_for_deletion.append({
                    "epic": epic,
                    "match_score": matches / len(user_keywords) if user_keywords else 0
                })
        
        if matching_epics_for_deletion:
            # Sort by match score and take top matches
            matching_epics_for_deletion.sort(key=lambda x: x["match_score"], reverse=True)
            # Only send matched epics to LLM (much smaller payload)
            epics_to_update = [m["epic"] for m in matching_epics_for_deletion[:3]]  # Max 3 epics
            logger.info(f"[BA] Deletion request - found {len(epics_to_update)} matching epic(s) to delete: {[e.get('title') for e in epics_to_update]}")
        else:
            # No match found, send all epics (fallback)
            logger.warning(f"[BA] Deletion request - no matching epic found, sending all {len(all_epics)} epics")
            epics_to_update = all_epics
    else:
        relevant_epics = []
        mentioned_domains = []
        
        for epic in all_epics:
            epic_domain = (epic.get("domain") or "").lower()
            epic_title = (epic.get("title") or "").lower()
            
            # Check if user message mentions this epic's domain or title
            if epic_domain and epic_domain in user_message_lower:
                relevant_epics.append(epic)
                mentioned_domains.append(epic_domain)
            elif any(keyword in epic_title for keyword in user_message_lower.split() if len(keyword) > 3):
                # Match significant words (>3 chars) from user message to epic title
                relevant_epics.append(epic)
                mentioned_domains.append(epic_domain or "unknown")
        
        # If no specific domain mentioned, or too many epics (>5), use ALL epics (general update)
        # But warn about performance
        if not relevant_epics or len(relevant_epics) > 5:
            logger.info(f"[BA] No specific domain detected or too many matches, using ALL {len(all_epics)} epics (may be slow)")
            epics_to_update = all_epics
        else:
            logger.info(f"[BA] Detected specific domains: {mentioned_domains}. Updating only {len(relevant_epics)} relevant epics (optimization)")
            epics_to_update = relevant_epics
    
    # Get conversation context for memory
    conversation_context = state.get("conversation_context", "")
    if conversation_context:
        logger.info(f"[BA] Using conversation context: {len(conversation_context)} chars")
    
    system_prompt = _sys_prompt(agent, "update_stories")
    user_prompt = _user_prompt(
        "update_stories",
        epics=json.dumps(epics_to_update, ensure_ascii=False, indent=2),
        user_message=state["user_message"],
        conversation_context=conversation_context
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Log payload size for debugging
    total_chars = len(system_prompt) + len(user_prompt)
    logger.info(f"[BA] Calling LLM for update_stories: {len(epics_to_update)} epics, payload size: {total_chars} chars")
    
    # Add timeout wrapper for LLM call
    import asyncio
    try:
        # Set timeout to 120 seconds (2 minutes) for large payloads
        result = await asyncio.wait_for(
            _invoke_structured(
                llm=_story_llm,
                schema=FullStoriesOutput,
                messages=messages,
                config=_cfg(state, "update_stories"),
                fallback_data={"epics": epics_to_update, "message_template": "", "approval_template": "", "change_summary": "Không thể cập nhật"}
            ),
            timeout=120.0  # 2 minutes timeout
        )
        logger.info(f"[BA] LLM call completed successfully")
    except asyncio.TimeoutError:
        logger.error(f"[BA] LLM call TIMEOUT after 120s! Payload: {len(epics_to_update)} epics, {total_chars} chars")
        # Use fallback data
        result = {"epics": epics_to_update, "message_template": "", "approval_template": "", "change_summary": "⚠️ Timeout - không thể cập nhật (payload quá lớn)"}
    except Exception as e:
        logger.error(f"[BA] LLM call FAILED: {e}")
        result = {"epics": epics_to_update, "message_template": "", "approval_template": "", "change_summary": f"⚠️ Lỗi: {str(e)[:100]}"}
    
    # Convert Pydantic Epic objects to dicts
    updated_epics_from_llm = []
    for e in result.get("epics", []):
        if hasattr(e, "model_dump"):
            updated_epics_from_llm.append(e.model_dump())
        elif isinstance(e, dict):
            updated_epics_from_llm.append(e)
    
    # MERGE: If we only updated SOME epics (optimization), merge them back into all_epics
    # Otherwise, use the updated epics directly
    if len(epics_to_update) < len(all_epics):
        logger.info(f"[BA] Merging {len(updated_epics_from_llm)} updated epics back into {len(all_epics)} total epics")
        
        # Build map of updated epics by ID
        updated_map = {epic.get("id"): epic for epic in updated_epics_from_llm}
        
        # Build set of IDs that were sent to LLM (for deletion detection)
        sent_epic_ids = {epic.get("id") for epic in epics_to_update}
        
        # Merge: replace updated epics, keep others unchanged
        # SPECIAL: If an epic was sent to LLM but NOT in result → it was DELETED
        final_epics = []
        for epic in all_epics:
            epic_id = epic.get("id")
            if epic_id in sent_epic_ids:
                # This epic was sent to LLM
                if epic_id in updated_map:
                    # Epic still exists in result → keep it (might be modified)
                    final_epics.append(updated_map[epic_id])
                else:
                    # Epic was sent but NOT in result → it was DELETED by LLM
                    logger.info(f"[BA] Epic '{epic.get('title')}' was DELETED by LLM")
                    # Don't add to final_epics (effectively deleted)
            else:
                # Epic was NOT sent to LLM → keep original
                final_epics.append(epic)
    else:
        # All epics were updated, use result directly
        final_epics = updated_epics_from_llm
    
    change_summary = result.get("change_summary", "Đã cập nhật stories")
    message_template = result.get("message_template", "")
    approval_template = result.get("approval_template", "")
    
    # Flatten stories for backward compatibility (use get, NOT pop - to keep stories in epics)
    all_stories = []
    for epic in final_epics:
        stories_in_epic = epic.get("stories", [])
        epic_title = epic.get("title", epic.get("name", "Unknown"))
        for story in stories_in_epic:
            if hasattr(story, "model_dump"):
                story = story.model_dump()
            story["epic_id"] = epic.get("id")
            story["epic_title"] = epic_title
            all_stories.append(story)
    
    total_epics = len(final_epics)
    total_stories = len(all_stories)
    logger.info(f"[BA] Updated {len(updated_epics_from_llm)} epics, final result: {total_epics} epics with {total_stories} stories")
    
    # No more validation needed here - STEP 2 already checked for existing functionality
    # If we reach here, user has confirmed they want to proceed
    # Use hardcoded messages (LLM templates unreliable)
    message = f"Đã cập nhật xong! Hiện có {total_stories} Stories trong {total_epics} Epics. Bạn xem qua và bấm 'Phê duyệt Stories' nhé!"
    approval_message = f"Đã cập nhật và lưu {total_epics} Epics, {total_stories} Stories vào backlog!"
    
    return {
        "epics": final_epics,
        "stories": all_stories,
        "change_summary": change_summary,
        "stories_message": message,
        "stories_approval_message": approval_message
    }




async def edit_single_story(state: BAState, agent=None) -> dict:
    """Node: Edit a SINGLE specific story based on user request.
    
    This is a FAST targeted update - finds the story by ID and applies only the requested change.
    Much faster than update_stories which regenerates everything.
    """
    logger.info(f"[BA] Editing single story (targeted mode)...")
    
    import re
    
    user_message = state.get("user_message", "")
    user_msg_lower = user_message.lower()
    
    # ====================================================================================
    # STEP 1: Extract story ID or title from user message
    # ====================================================================================
    # Try 1: Extract story ID with regex (most reliable)
    # Pattern: EPIC-XXX-US-YYY or epic-xxx-us-yyy
    story_id_pattern = r'epic-\d+-us-\d+'
    id_match = re.search(story_id_pattern, user_msg_lower)
    
    target_story_id = None
    search_by_title = False
    
    if id_match:
        target_story_id = id_match.group(0).upper()  # Normalize to uppercase
        logger.info(f"[BA] Extracted story ID: {target_story_id}")
    else:
        # Try 2: Check if user mentioned story title (quoted or after keywords)
        # Patterns: "sửa story 'title here'" or "xóa story title here"
        title_patterns = [
            r"['\"](.+?)['\"]",  # Quoted: "story title" or 'story title'
            r"(?:story|stories)\s+(.{10,100}?)(?:\s+(?:bỏ|xóa|thêm|sửa|add|remove|delete|change)|$)",  # After "story": "sửa story ABC"
        ]
        
        title_match = None
        for pattern in title_patterns:
            title_match = re.search(pattern, user_message, re.IGNORECASE)
            if title_match:
                break
        
        if title_match:
            search_by_title = True
            title_query = title_match.group(1).strip()
            logger.info(f"[BA] No ID found, will search by title: '{title_query[:50]}...'")
        else:
            # No ID, no clear title → vague request
            logger.warning(f"[BA] No story ID or title found in message: {user_message[:100]}")
            logger.info("[BA] Falling back to update_stories for vague request")
            return await update_stories(state, agent)
    
    # ====================================================================================
    # STEP 2: Load epics from state or artifact
    # ====================================================================================
    epics = state.get("epics", [])
    
    # If no epics in state, try to load from artifact (same pattern as approve_stories)
    if not epics and agent:
        logger.info("[BA] No epics in state, loading from artifact...")
        try:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.get_latest_version(
                    project_id=agent.project_id,
                    artifact_type=ArtifactType.USER_STORIES
                )
                if artifact and artifact.content:
                    epics = artifact.content.get("epics", [])
                    logger.info(f"[BA] Loaded {len(epics)} epics from artifact")
        except Exception as e:
            logger.warning(f"[BA] Failed to load from artifact: {e}")
    
    if not epics:
        logger.warning("[BA] No existing epics/stories to edit")
        return {"error": "No existing stories to edit"}
    
    # ====================================================================================
    # STEP 3: Find target story (by ID or title)
    # ====================================================================================
    target_story = None
    target_story_idx = None
    
    # Build a flat list of all stories
    stories = []
    for epic in epics:
        for story in epic.get("stories", []):
            story["epic_id"] = epic.get("id")
            story["epic_title"] = epic.get("title")
            stories.append(story)
    
    if target_story_id:
        # Search by ID (exact match)
        for i, story in enumerate(stories):
            if story.get("id", "").upper() == target_story_id:
                target_story = story
                target_story_idx = i
                logger.info(f"[BA] Found story by ID: {target_story_id} - {story.get('title')[:50]}...")
                break
        
        if not target_story:
            logger.warning(f"[BA] Story {target_story_id} not found in {len(stories)} existing stories")
            # Fallback: Let LLM try to find it
            return await _edit_story_with_llm_search(state, agent, epics, stories)
    
    elif search_by_title:
        # Search by title (fuzzy match with scoring)
        title_query_lower = title_query.lower()
        best_match = None
        best_score = 0
        
        for i, story in enumerate(stories):
            story_title = story.get("title", "").lower()
            
            # Calculate similarity score
            # Method 1: Exact substring match (highest priority)
            if title_query_lower in story_title or story_title in title_query_lower:
                score = 1.0
            else:
                # Method 2: Word overlap (count matching words)
                query_words = set(title_query_lower.split())
                title_words = set(story_title.split())
                common_words = query_words & title_words
                
                if len(query_words) > 0:
                    score = len(common_words) / len(query_words)
                else:
                    score = 0
            
            if score > best_score:
                best_score = score
                best_match = (story, i)
            
            # Log top matches for debugging
            if score >= 0.3:
                logger.debug(f"[BA] Story '{story_title[:50]}...' similarity: {score:.2f}")
        
        # Use best match if score is good enough (>= 50% similarity)
        if best_match and best_score >= 0.5:
            target_story, target_story_idx = best_match
            logger.info(f"[BA] Found story by title (score={best_score:.2f}): {target_story.get('title')[:50]}...")
        else:
            logger.warning(f"[BA] No good title match found (best score: {best_score:.2f})")
            # Fallback: Let LLM try to find it
            return await _edit_story_with_llm_search(state, agent, epics, stories)
    
    # Step 2: Use LLM to apply the specific change
    logger.info(f"[BA] Applying changes to story: {target_story.get('id')} - {target_story.get('title')[:50]}...")
    
    system_prompt = _sys_prompt(agent, "edit_single_story")
    user_prompt = _user_prompt(
        "edit_single_story",
        user_message=user_message,
        target_story=json.dumps(target_story, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_fast_llm,  # Use fast LLM since it's a simple edit
        schema=SingleStoryEditOutput,
        messages=messages,
        config=_cfg(state, "edit_single_story"),
        fallback_data={
            "story_id": target_story.get("id", ""),
            "found": True,
            "updated_story": target_story,
            "change_summary": "Không thể áp dụng thay đổi",
            "message": "⚠️ Không thể xử lý yêu cầu. Bạn thử lại nhé!"
        }
    )
    
    # Check if edit was successful
    updated_story = result.get("updated_story")
    if not updated_story:
        logger.warning("[BA] LLM could not process the edit - no updated_story returned")
        error_message = result.get("message", "⚠️ Không thể áp dụng thay đổi. Bạn thử lại nhé!")
        # Send error message to user directly
        if agent:
            await agent.message_user("response", error_message)
        return {
            "error": error_message,
            "is_complete": True  # Mark complete so graph ends
        }
    
    # Step 3: Check if user wants to DELETE the story
    # Story is considered "deleted" if:
    # - User explicitly says "xóa", "delete", "remove"
    # - LLM returns empty requirements AND empty acceptance_criteria
    if hasattr(updated_story, "model_dump"):
        updated_story = updated_story.model_dump()
    
    user_wants_delete = any(kw in user_msg_lower for kw in ["xóa", "delete", "remove", "loại bỏ", "bỏ story"])
    story_is_empty = (
        not updated_story.get("requirements") and 
        not updated_story.get("acceptance_criteria")
    )
    
    should_delete_story = user_wants_delete or story_is_empty
    
    if should_delete_story:
        # DELETE story completely from epics and stories
        story_id = target_story.get("id")
        logger.info(f"[BA] DELETING story {story_id} (user requested or story is empty)")
        
        # Remove from flat stories list
        stories = [s for s in stories if s.get("id") != story_id]
        
        # Remove from epics structure
        for epic in epics:
            epic_stories = epic.get("stories", [])
            epic["stories"] = [s for s in epic_stories if s.get("id") != story_id]
        
        change_summary = f"Đã xóa story {story_id}"
        message = result.get("message", f"🗑️ Đã xóa thành công story \"{target_story.get('title', '')[:50]}...\"")
        
        logger.info(f"[BA] Story deleted: {story_id}")
        
        return {
            "epics": epics,
            "stories": stories,
            "change_summary": change_summary,
            "stories_message": message,
            "stories_approval_message": f"Đã xóa story khỏi backlog!"
        }
    else:
        # UPDATE story (keep it, just modify)
        # Update in stories list
        stories[target_story_idx] = updated_story
        
        # Update in epics structure
        for epic in epics:
            epic_stories = epic.get("stories", [])
            for j, s in enumerate(epic_stories):
                if s.get("id") == updated_story.get("id"):
                    epic_stories[j] = updated_story
                    break
        
        change_summary = result.get("change_summary", "Đã cập nhật story")
        message = result.get("message", f"Đã cập nhật story '{updated_story.get('title', '')[:50]}...'")
        
        logger.info(f"[BA] Single story edit complete: {change_summary}")
        
        return {
            "epics": epics,
            "stories": stories,
            "change_summary": change_summary,
            "stories_message": message,
            "stories_approval_message": f"Đã lưu thay đổi cho story!"
        }




async def _edit_story_with_llm_search(state: BAState, agent, epics: list, stories: list) -> dict:
    """Fallback: Let LLM search for the story when we can't find it by keyword matching."""
    logger.info("[BA] Using LLM to search for target story...")
    
    # Create a summary of all stories for LLM to search
    stories_summary = []
    for story in stories:
        stories_summary.append({
            "id": story.get("id"),
            "title": story.get("title"),
            "epic_id": story.get("epic_id")
        })
    
    # Ask LLM to identify which story and what change
    system_prompt = """You identify which story the user wants to edit.
Return JSON: {"story_id": "EPIC-XXX-US-XXX", "found": true/false}
If you can't identify, set found=false."""
    
    user_prompt = f"""User request: "{state.get('user_message', '')}"

Available stories:
{json.dumps(stories_summary, ensure_ascii=False, indent=2)}

Which story does the user want to edit?"""
    
    try:
        response = await _fast_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Parse response
        import re
        match = re.search(r'"story_id"\s*:\s*"([^"]+)"', response.content)
        if match:
            story_id = match.group(1)
            # Find the story
            for i, story in enumerate(stories):
                if story.get("id") == story_id:
                    # Now edit this story
                    state_copy = dict(state)
                    state_copy["target_story_idx"] = i
                    # Recursively call with found story
                    return await _apply_edit_to_story(state_copy, agent, epics, stories, i)
    except Exception as e:
        logger.warning(f"[BA] LLM search failed: {e}")
    
    # Could not find - fall back to full update
    logger.warning("[BA] Could not find specific story, falling back to full update_stories")
    return await update_stories(state, agent)




async def _apply_edit_to_story(state: BAState, agent, epics: list, stories: list, story_idx: int) -> dict:
    """Apply edit to a specific story after it's been found."""
    target_story = stories[story_idx]
    user_message = state.get("user_message", "")
    
    system_prompt = _sys_prompt(agent, "edit_single_story")
    user_prompt = _user_prompt(
        "edit_single_story",
        user_message=user_message,
        target_story=json.dumps(target_story, ensure_ascii=False, indent=2)
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    result = await _invoke_structured(
        llm=_fast_llm,
        schema=SingleStoryEditOutput,
        messages=messages,
        config=_cfg(state, "edit_single_story"),
        fallback_data={
            "story_id": target_story.get("id", ""),
            "found": True,
            "updated_story": target_story,
            "change_summary": "Không thể áp dụng thay đổi",
            "message": "⚠️ Không thể xử lý yêu cầu."
        }
    )
    
    updated_story = result.get("updated_story")
    if not updated_story:
        logger.warning("[BA] _apply_edit_to_story: LLM could not process the edit")
        error_message = result.get("message", "⚠️ Không thể áp dụng thay đổi. Bạn thử lại nhé!")
        if agent:
            await agent.message_user("response", error_message)
        return {"error": error_message, "is_complete": True}
    if hasattr(updated_story, "model_dump"):
        updated_story = updated_story.model_dump()
    
    stories[story_idx] = updated_story
    
    for epic in epics:
        epic_stories = epic.get("stories", [])
        for j, s in enumerate(epic_stories):
            if s.get("id") == updated_story.get("id"):
                epic_stories[j] = updated_story
                break
    
    return {
        "epics": epics,
        "stories": stories,
        "change_summary": result.get("change_summary", "Đã cập nhật"),
        "stories_message": result.get("message", "Đã cập nhật story!"),
        "stories_approval_message": "Đã lưu thay đổi!"
    }




async def approve_stories(state: BAState, agent=None) -> dict:
    """Node: Approve stories and save them to database using UPSERT logic.
    
    UPSERT Strategy (preserves existing stories):
    - Epics/Stories with matching code: UPDATE (preserve status, progress)
    - New Epics/Stories: INSERT
    - Epics/Stories not in new data: KEEP (don't delete - user may have other epics)
    
    This allows incremental updates when user adds/modifies features without
    losing existing stories that are in progress.
    """
    logger.info(f"[BA] Approving stories with UPSERT logic...")
    
    epics_data = state.get("epics", [])
    stories_data = state.get("stories", [])
    
    # If no epics in state, try to load from artifact (fix for approval flow)
    if not epics_data and agent:
        logger.info("[BA] No epics in state, trying to load from artifact...")
        try:
            with Session(engine) as session:
                service = ArtifactService(session)
                artifact = service.get_latest_version(
                    project_id=agent.project_id,
                    artifact_type=ArtifactType.USER_STORIES
                )
                if artifact and artifact.content:
                    epics_data = artifact.content.get("epics", [])
                    stories_data = artifact.content.get("stories", [])
                    logger.info(f"[BA] Loaded from artifact: {len(epics_data)} epics, {len(stories_data)} stories")
        except Exception as e:
            logger.warning(f"[BA] Failed to load from artifact: {e}")
    
    if not epics_data and not stories_data:
        return {"error": "No stories to approve"}
    
    if not agent:
        return {"error": "No agent context for saving to database"}
    
    try:
        created_epics = []
        updated_epics = []
        created_stories = []
        updated_stories = []
        epic_id_map = {}  # Map string ID (EPIC-001) to UUID
        story_id_map = {}  # Map string ID (EPIC-001-US-001) to actual UUID
        
        with Session(engine) as session:
            # 0. Load existing epics and stories (for UPSERT comparison)
            existing_epics_db = session.exec(
                select(Epic).where(Epic.project_id == agent.project_id)
            ).all()
            existing_stories_db = session.exec(
                select(Story).where(Story.project_id == agent.project_id)
            ).all()
            
            # Build lookup maps by epic_code and story_code
            existing_epics_map = {e.epic_code: e for e in existing_epics_db if e.epic_code}
            existing_stories_map = {s.story_code: s for s in existing_stories_db if s.story_code}
            
            logger.info(
                f"[BA] UPSERT: Found {len(existing_epics_map)} existing epics, "
                f"{len(existing_stories_map)} existing stories in DB"
            )
            
            # 1. UPSERT Epics
            for epic_data in epics_data:
                epic_string_id = epic_data.get("id", "")  # e.g., "EPIC-001"
                existing_epic = existing_epics_map.get(epic_string_id)
                
                if existing_epic:
                    # UPDATE existing epic (preserve UUID, update content)
                    existing_epic.title = epic_data.get("title", epic_data.get("name", existing_epic.title))
                    existing_epic.description = epic_data.get("description", existing_epic.description)
                    existing_epic.domain = epic_data.get("domain", existing_epic.domain)
                    # Note: preserve epic_status - don't reset to PLANNED
                    
                    epic_id_map[epic_string_id] = existing_epic.id
                    updated_epics.append({
                        "id": str(existing_epic.id),
                        "title": existing_epic.title,
                        "domain": existing_epic.domain,
                        "action": "updated"
                    })
                    logger.debug(f"[BA] Updated epic: {epic_string_id} -> {existing_epic.id}")
                else:
                    # INSERT new epic
                    new_epic = Epic(
                        epic_code=epic_string_id if epic_string_id else None,
                        title=epic_data.get("title", epic_data.get("name", "Unknown Epic")),
                        description=epic_data.get("description"),
                        domain=epic_data.get("domain"),
                        project_id=agent.project_id,
                        epic_status=EpicStatus.PLANNED
                    )
                    session.add(new_epic)
                    session.flush()  # Get UUID immediately
                    
                    epic_id_map[epic_string_id] = new_epic.id
                    created_epics.append({
                        "id": str(new_epic.id),
                        "title": new_epic.title,
                        "domain": new_epic.domain,
                        "action": "created"
                    })
                    logger.debug(f"[BA] Created epic: {epic_string_id} -> {new_epic.id}")
            
            logger.info(f"[BA] Epics: {len(created_epics)} created, {len(updated_epics)} updated")
            
            # 2. UPSERT Stories
            # Get max rank for new stories
            max_rank_result = session.exec(
                select(func.max(Story.rank)).where(
                    Story.project_id == agent.project_id,
                    Story.status == StoryStatus.TODO
                )
            ).one()
            current_rank = (max_rank_result or 0)
            
            story_objects_for_deps = []  # (story, string_id, original_deps) for dependency resolution
            
            for story_data in stories_data:
                story_string_id = story_data.get("id", "")  # e.g., "EPIC-001-US-001"
                epic_string_id = story_data.get("epic_id", "")
                epic_uuid = epic_id_map.get(epic_string_id)
                original_dependencies = story_data.get("dependencies", [])
                
                existing_story = existing_stories_map.get(story_string_id)
                
                if existing_story:
                    # UPDATE existing story (preserve status, UUID, rank)
                    existing_story.title = story_data.get("title", existing_story.title)
                    existing_story.description = story_data.get("description", existing_story.description)
                    existing_story.acceptance_criteria = story_data.get("acceptance_criteria", existing_story.acceptance_criteria)
                    existing_story.requirements = story_data.get("requirements", existing_story.requirements)
                    existing_story.priority = story_data.get("priority", existing_story.priority)
                    existing_story.story_point = story_data.get("story_point", existing_story.story_point)
                    # Update epic_id in case story moved to different epic
                    if epic_uuid:
                        existing_story.epic_id = epic_uuid
                    # Note: preserve status, rank - don't reset to TODO
                    
                    story_id_map[story_string_id] = str(existing_story.id)
                    story_objects_for_deps.append((existing_story, story_string_id, original_dependencies))
                    updated_stories.append({
                        "id": str(existing_story.id),
                        "string_id": story_string_id,
                        "title": existing_story.title,
                        "epic_id": str(existing_story.epic_id) if existing_story.epic_id else None,
                        "status": existing_story.status.value if existing_story.status else "TODO",
                        "action": "updated"
                    })
                    logger.debug(f"[BA] Updated story: {story_string_id} (status preserved: {existing_story.status})")
                else:
                    # INSERT new story
                    current_rank += 1
                    new_story = Story(
                        story_code=story_string_id if story_string_id else None,
                        title=story_data.get("title", "Unknown Story"),
                        description=story_data.get("description"),
                        acceptance_criteria=story_data.get("acceptance_criteria", []),
                        requirements=story_data.get("requirements", []),
                        project_id=agent.project_id,
                        epic_id=epic_uuid,
                        status=StoryStatus.TODO,
                        type=StoryType.USER_STORY,
                        priority=story_data.get("priority"),
                        story_point=story_data.get("story_point"),
                        rank=current_rank,
                        dependencies=[],
                    )
                    session.add(new_story)
                    session.flush()  # Get UUID immediately
                    
                    story_id_map[story_string_id] = str(new_story.id)
                    story_objects_for_deps.append((new_story, story_string_id, original_dependencies))
                    created_stories.append({
                        "id": str(new_story.id),
                        "string_id": story_string_id,
                        "title": new_story.title,
                        "epic_id": str(new_story.epic_id) if new_story.epic_id else None,
                        "action": "created"
                    })
                    logger.debug(f"[BA] Created story: {story_string_id} -> {new_story.id}")
            
            logger.info(f"[BA] Stories: {len(created_stories)} created, {len(updated_stories)} updated")
            
            # 3. DELETE epics that are NOT in the new artifact (user deleted them)
            deleted_epics = []
            epics_in_artifact = {e.get("epic_code") for e in epics_data if e.get("epic_code")}
            
            for existing_epic in existing_epics_db:
                epic_code = existing_epic.epic_code
                if epic_code and epic_code not in epics_in_artifact:
                    # Epic was in DB but NOT in artifact → User deleted it
                    logger.info(f"[BA] DELETING epic from DB: {epic_code} (not in artifact)")
                    # Delete all stories in this epic first
                    epic_stories = [s for s in existing_stories_db if s.epic_id == existing_epic.id]
                    for story in epic_stories:
                        session.delete(story)
                        logger.debug(f"[BA]   Deleting story {story.story_code} (part of deleted epic)")
                    # Then delete the epic
                    session.delete(existing_epic)
                    deleted_epics.append({
                        "id": str(existing_epic.id),
                        "epic_code": epic_code,
                        "title": existing_epic.title,
                        "stories_deleted": len(epic_stories),
                        "action": "deleted"
                    })
            
            if deleted_epics:
                logger.info(f"[BA] Deleted {len(deleted_epics)} epics from DB (including their stories)")
            
            # 4. DELETE stories that are NOT in the new artifact (user deleted them)
            # This handles the case where user says "xóa story X"
            deleted_stories = []
            stories_in_artifact = {s.get("id") for s in stories_data if s.get("id")}
            
            for existing_story in existing_stories_db:
                story_code = existing_story.story_code
                if story_code and story_code not in stories_in_artifact:
                    # Story was in DB but NOT in artifact → User deleted it
                    logger.info(f"[BA] DELETING story from DB: {story_code} (not in artifact)")
                    session.delete(existing_story)
                    deleted_stories.append({
                        "id": str(existing_story.id),
                        "string_id": story_code,
                        "title": existing_story.title,
                        "action": "deleted"
                    })
            
            if deleted_stories:
                logger.info(f"[BA] Deleted {len(deleted_stories)} stories from DB")
            
            # 4. Resolve dependencies for all stories (both new and updated)
            deps_resolved = 0
            for story, string_id, original_deps in story_objects_for_deps:
                if original_deps:
                    resolved_deps = [
                        story_id_map[dep_id]
                        for dep_id in original_deps
                        if dep_id in story_id_map
                    ]
                    if resolved_deps:
                        story.dependencies = resolved_deps
                        deps_resolved += 1
            
            if deps_resolved:
                logger.info(f"[BA] Resolved dependencies for {deps_resolved} stories")
            
            # Commit all changes (including deletions)
            session.commit()
        
        total_epics = len(created_epics) + len(updated_epics)
        total_stories = len(created_stories) + len(updated_stories)
        
        logger.info(
            f"[BA] UPSERT complete: {total_epics} epics ({len(created_epics)} new, {len(updated_epics)} updated), "
            f"{total_stories} stories ({len(created_stories)} new, {len(updated_stories)} updated, {len(deleted_stories)} deleted)"
        )
        
        # Build approval message - ONLY show actions that actually happened
        actions = []
        
        # Only mention what actually changed
        if len(created_epics) > 0:
            actions.append(f"{len(created_epics)} epic thêm mới")
        if len(updated_epics) > 0:
            actions.append(f"{len(updated_epics)} epic cập nhật")
        if len(deleted_epics) > 0:
            total_stories_in_deleted_epics = sum(e.get("stories_deleted", 0) for e in deleted_epics)
            actions.append(f"{len(deleted_epics)} epic xóa ({total_stories_in_deleted_epics} stories)")
        if len(created_stories) > 0:
            actions.append(f"{len(created_stories)} story thêm mới")
        if len(updated_stories) > 0:
            actions.append(f"{len(updated_stories)} story cập nhật")
        if len(deleted_stories) > 0:
            actions.append(f"{len(deleted_stories)} story xóa")
        
        if actions:
            # Show only what changed
            approval_msg = f"Đã cập nhật backlog! {', '.join(actions)}. 🎉"
        else:
            # Nothing changed
            approval_msg = "Backlog đã được đồng bộ! 🎉"
        
        return {
            "stories_approved": True,
            "created_epics": created_epics,
            "updated_epics": updated_epics,
            "created_stories": created_stories,
            "updated_stories": updated_stories,
            "approval_message": approval_msg,
            "stories_approval_message": approval_msg
        }
        
    except Exception as e:
        logger.error(f"[BA] Failed to save stories to database: {e}", exc_info=True)
        return {"error": f"Failed to save stories: {str(e)}"}




