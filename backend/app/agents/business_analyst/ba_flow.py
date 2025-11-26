"""Business Analyst Flow - Event-driven workflow using CrewAI Flows."""

import logging
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

from crewai.flow.flow import Flow, start, listen, router, or_

from .ba_flow_state import BAFlowState
from .crew import BusinessAnalystCrew

if TYPE_CHECKING:
    from .business_analyst import BusinessAnalyst


logger = logging.getLogger(__name__)


class BAFlow(Flow[BAFlowState]):
    """BA workflow orchestrated via CrewAI Flows.
    
    This flow uses a declarative, event-driven architecture to handle
    business analysis tasks including:
    - User requirements gathering through interviews
    - Domain analysis
    - PRD generation and updates
    - User story extraction
    
    The flow automatically manages state and provides visualization capabilities.
    """
    
    def __init__(self, agent: "BusinessAnalyst", user_message: str):
        """Initialize the BA Flow.
        
        Args:
            agent: BusinessAnalyst instance for communication and persistence
            user_message: User's message to process
        """
        super().__init__()
        self.agent = agent
        self.crew = agent.crew
        self.project_files = agent.project_files
        
        # Initialize state
        self.state.user_id = UUID(int=0)  # Will be set properly in entry point
        self.state.user_message = user_message
    
    # ==================== Entry Point ====================
    
    @start()
    async def receive_user_message(self):
        """Entry point - receives user message and loads context."""
        logger.info(f"[BAFlow] Starting flow for message: {self.state.user_message[:50]}...")
        
        # Store original request if not already present
        if not self.state.collected_info.get("original_request"):
            self.state.collected_info["original_request"] = self.state.user_message
        
        # Load existing artifacts
        if self.project_files:
            try:
                self.state.existing_prd = await self.project_files.load_prd()
                logger.info(f"[BAFlow] Loaded existing PRD: {bool(self.state.existing_prd)}")
            except Exception as e:
                logger.warning(f"[BAFlow] Could not load PRD: {e}")
                self.state.existing_prd = None
        
        # TODO: Check if stories exist in DB
        self.state.has_stories = False
        
        return self.state
    
    # ==================== Orchestration ====================
    
    @listen(receive_user_message)
    async def orchestrate_routing(self, state):
        """Orchestrator analyzes message and decides routing."""
        logger.info("[BAFlow] Orchestrator analyzing message...")
        
        routing = await self.crew.analyze_and_route(
            user_message=state.user_message,
            current_phase=state.phase,
            collected_info=state.collected_info,
            questions_asked=state.questions_asked,
            has_existing_prd=state.existing_prd is not None,
            has_stories=state.has_stories
        )
        
        # Update state with routing decision
        self.state.intent = routing["intent"]
        self.state.action = routing["action"]
        self.state.agent_to_use = routing["agent_to_use"]
        
        logger.info(
            f"[BAFlow] Orchestrator decision: intent={routing['intent']}, "
            f"action={routing['action']}, agent={routing['agent_to_use']}"
        )
        
        return routing
    
    # ==================== Router ====================
    
    @router(orchestrate_routing)
    def route_action(self, routing):
        """Route to appropriate action handler based on orchestrator decision."""
        action = routing["action"]
        logger.info(f"[BAFlow] Routing to action: {action}")
        return action  # Returns label for @listen decorators
    
    # ==================== Action Handlers ====================
    
    @listen("ASK_CLARIFICATION")
    async def handle_interview(self):
        """Start interview flow to gather requirements."""
        logger.info("[BAFlow] Starting interview flow")
        
        missing_info = self.state.collected_info.get("missing_info", [])
        
        # Generate first question using crew
        question_data = await self.crew.generate_first_clarification_question(
            user_message=self.state.user_message,
            missing_info=missing_info
        )
        
        # Ask via agent's communication method
        await self.agent.ask_clarification_question(
            question=question_data["question_text"],
            question_type=question_data.get("question_type", "multichoice"),
            options=question_data.get("options", []),
            allow_multiple=question_data.get("allow_multiple", False)
        )
        
        # Update state
        self.state.phase = "interview"
        self.state.questions_asked.append({
            "question": question_data["question_text"],
            "context": question_data.get("context"),
            "type": question_data.get("question_type")
        })
        
        logger.info("[BAFlow] Interview question sent")
        return "interview_started"
    
    @listen("ANALYZE_DOMAIN")
    async def handle_domain_analysis(self):
        """Perform domain expert analysis."""
        logger.info("[BAFlow] Running domain analysis")
        
        # Use domain_expert crew member for analysis
        analysis = await self.crew.analyze_requirements(self.state.user_message)
        
        # Store in state
        self.state.collected_info["domain_analysis"] = analysis
        self.state.phase = "analysis_complete"
        
        # Send to user
        await self.agent.message_user("response", 
            f"📊 **Domain Analysis Complete**\n\n{analysis}\n\n"
            "Bạn muốn tiếp tục tạo PRD không?",
            {"message_type": "domain_analysis", "analysis": analysis}
        )
        
        logger.info("[BAFlow] Domain analysis complete")
        return analysis
    
    @listen("GENERATE_PRD")
    async def handle_prd_generation(self):
        """Generate PRD from collected information."""
        logger.info("[BAFlow] Generating PRD")
        
        if not self.project_files:
            logger.warning("[BAFlow] No project files, cannot generate PRD")
            await self.agent.message_user("error", "❌ Project files not initialized")
            return None
        
        # Use prd_specialist to generate PRD
        prd_data = await self.crew.generate_prd_from_interview(
            original_request=self.state.collected_info.get("original_request", ""),
            interview_data=self.state.collected_info
        )
        
        # Save PRD to files
        prd_path = await self.project_files.save_prd(prd_data)
        logger.info(f"[BAFlow] PRD saved to: {prd_path}")
        
        # Create artifact in DB
        artifact_id = await self.agent.create_artifact(
            artifact_type="prd",
            title=f"PRD: {prd_data.get('project_name', 'Untitled')}",
            content=prd_data,
            description=prd_data.get('overview', '')[:200],
            tags=["prd", "generated"]
        )
        
        # Notify user
        await self.agent.message_user("response",
            f"✅ Đã tạo PRD: {prd_data.get('project_name', 'Untitled')}\n\n"
            f"**File**: `{prd_path.name}`",
            {
                "message_type": "artifact_created",
                "artifact_id": str(artifact_id),
                "artifact_type": "prd"
            }
        )
        
        # Update state
        self.state.phase = "prd_complete"
        self.state.existing_prd = prd_data
        
        logger.info("[BAFlow] PRD generation complete")
        return prd_data
    
    @listen("UPDATE_PRD")
    async def handle_prd_update(self):
        """Update existing PRD based on user's edit request."""
        logger.info("[BAFlow] Updating existing PRD")
        
        if not self.state.existing_prd:
            error_msg = "❌ Không tìm thấy PRD. Bạn muốn tạo PRD mới?"
            await self.agent.message_user("error", error_msg)
            self.state.error_message = "No existing PRD"
            return None
        
        if not self.project_files:
            logger.warning("[BAFlow] No project files, cannot update PRD")
            await self.agent.message_user("error", "❌ Project files not initialized")
            return None
        
        # Use prd_specialist to update
        updated_prd = await self.crew.update_existing_prd(
            edit_request=self.state.user_message,
            existing_prd=self.state.existing_prd
        )
        
        # Save updated PRD
        prd_path = await self.project_files.save_prd(updated_prd)
        logger.info(f"[BAFlow] Updated PRD saved to: {prd_path}")
        
        # Create new artifact version
        artifact_id = await self.agent.create_artifact(
            artifact_type="prd",
            title=f"PRD: {updated_prd['project_name']} v{updated_prd.get('version', '1.0')}",
            content=updated_prd,
            description=updated_prd.get('change_summary', 'PRD updated'),
            tags=["prd", "updated"]
        )
        
        # Notify user
        await self.agent.message_user("response",
            f"✅ Đã cập nhật PRD!\n\n"
            f"**Changes**: {updated_prd.get('change_summary', 'See artifact')}\n"
            f"**Version**: {updated_prd.get('version', 'N/A')}",
            {
                "message_type": "artifact_updated",
                "artifact_id": str(artifact_id)
            }
        )
        
        # Update state
        self.state.existing_prd = updated_prd
        
        logger.info("[BAFlow] PRD update complete")
        return updated_prd
    
    @listen("EXTRACT_STORIES")
    async def handle_story_extraction(self):
        """Extract user stories from existing PRD."""
        logger.info("[BAFlow] Extracting user stories from PRD")
        
        if not self.state.existing_prd:
            error_msg = "❌ Cần có PRD trước khi tạo stories. Tạo PRD trước nhé!"
            await self.agent.message_user("error", error_msg)
            self.state.error_message = "No PRD to extract from"
            return None
        
        # Use the agent's existing method to extract stories
        # Note: Need a placeholder artifact_id
        created_story_ids = await self.agent._extract_stories_from_prd(
            self.state.existing_prd,
            uuid4()  # Placeholder UUID
        )
        
        logger.info(f"[BAFlow] Extracted {len(created_story_ids)} stories")
        return created_story_ids
    
    @listen("UPDATE_STORY")
    async def handle_story_update(self):
        """Update existing user story (stub for future implementation)."""
        logger.info("[BAFlow] Story update requested")
        
        await self.agent.message_user("info", 
            "📝 Story editing feature đang được phát triển.\n"
            "Hiện tại bạn có thể edit trực tiếp trong backlog."
        )
        
        return "story_update_pending"
    
    @listen("ERROR")
    async def handle_error(self):
        """Handle orchestrator errors."""
        error_msg = self.state.error_message or "Unable to process request"
        logger.error(f"[BAFlow] Error: {error_msg}")
        
        await self.agent.message_user("error", error_msg)
        
        self.state.is_complete = True
        return error_msg
    
    # ==================== Completion ====================
    
    @listen(or_(
        handle_prd_generation,
        handle_prd_update,
        handle_story_extraction,
        handle_domain_analysis,
        handle_error
    ))
    async def complete_flow(self, result):
        """Mark flow as complete after any terminal action."""
        logger.info(f"[BAFlow] Flow completing with result type: {type(result).__name__}")
        
        # Don't mark as complete if we're waiting for interview response
        if self.state.phase == "interview":
            logger.info("[BAFlow] Interview in progress, not completing")
            return "waiting_for_answer"
        
        self.state.is_complete = True
        logger.info("[BAFlow] Flow complete")
        
        return "complete"
