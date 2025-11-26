"""Business Analyst Crew - Requirements analysis and PRD generation."""

import json
import logging

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task


logger = logging.getLogger(__name__)


@CrewBase
class BusinessAnalystCrew:
    """Multi-agent BA crew with specialized sub-agents."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    def __init__(
        self,
        agent_name: str = "BA",
        personality_traits: list[str] = None,
        communication_style: str = None
    ):
        self.agent_name = agent_name
        self.personality_traits = personality_traits or []
        self.communication_style = communication_style or "professional and clear"
        
        self.persona_description = self._build_persona_description()
    
    def _build_persona_description(self) -> str:
        traits_str = ", ".join(self.personality_traits) if self.personality_traits else "professional"
        
        return f"""You are {self.agent_name}, a Business Analyst.

Personality Traits: {traits_str}
Communication Style: {self.communication_style}

Embody this personality in all responses while maintaining professionalism."""
    
    @agent
    def requirements_engineer(self) -> Agent:
        base_config = self.agents_config['requirements_engineer'].copy()
        
        base_config['backstory'] = f"""{self.persona_description}

As a Requirements Engineer, you excel at asking targeted clarification questions and detecting missing information."""
        
        return Agent(
            config=base_config,
            verbose=True
        )
    
    @agent
    def domain_expert(self) -> Agent:
        base_config = self.agents_config['domain_expert'].copy()
        
        base_config['backstory'] = f"""{self.persona_description}

As a Domain Expert, you analyze business context and explain complex domain concepts clearly."""
        
        return Agent(
            config=base_config,
            verbose=True
        )
    
    @agent
    def prd_specialist(self) -> Agent:
        base_config = self.agents_config['prd_specialist'].copy()
        
        base_config['backstory'] = f"""{self.persona_description}

As a PRD Specialist, you create clear and comprehensive documentation."""
        
        return Agent(
            config=base_config,
            verbose=True
        )
    
    @agent
    def story_writer(self) -> Agent:
        base_config = self.agents_config['story_writer'].copy()
        
        base_config['backstory'] = f"""{self.persona_description}

As a Story Writer, you craft clear, actionable user stories."""
        
        return Agent(
            config=base_config,
            verbose=True
        )
    
    @agent
    def workflow_orchestrator(self) -> Agent:
        base_config = self.agents_config['workflow_orchestrator'].copy()
        
        base_config['backstory'] = f"""{self.persona_description}

As the Workflow Orchestrator, you coordinate your team of specialists and make intelligent routing decisions."""
        
        return Agent(
            config=base_config,
            verbose=True
        )
    
    @task
    def analyze_requirements_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_requirements']
        )
    
    @task
    def check_clarification_task(self) -> Task:
        return Task(
            config=self.tasks_config['check_clarification_needed']
        )
    
    @task
    def analyze_with_context_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_with_context']
        )
    
    @task
    def detect_intent_task(self) -> Task:
        return Task(
            config=self.tasks_config['detect_intent']
        )
    
    @task
    def generate_interview_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_interview_question']
        )
    
    @task
    def generate_prd_from_interview_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_prd_from_interview']
        )
    
    @task
    def extract_user_stories_task(self) -> Task:
        return Task(
            config=self.tasks_config['extract_user_stories_from_prd']
        )
    
    @task
    def update_existing_prd_task(self) -> Task:
        return Task(
            config=self.tasks_config['update_existing_prd']
        )
    
    @task
    def generate_first_clarification_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_first_clarification_question']
        )
    
    @task
    def generate_next_interview_question_task(self) -> Task:
        return Task(
            config=self.tasks_config['generate_next_interview_question']
        )
    
    @task
    def decide_next_action_task(self) -> Task:
        return Task(
            config=self.tasks_config['decide_next_action']
        )
    
    @task
    def analyze_and_route_task(self) -> Task:
        return Task(
            config=self.tasks_config['analyze_and_route']
        )
    
    @crew
    def crew(self) -> Crew:
        """Creates the Business Analyst crew."""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
    
    async def analyze_requirements(self, user_message: str) -> str:
        """Analyze requirements for a user message - uses domain_expert."""
        crew_instance = Crew(
            agents=[self.domain_expert()],
            tasks=[self.analyze_requirements_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={"user_message": user_message})
        return str(result)
    
    async def check_needs_clarification(self, message: str) -> bool:
        """Check if message needs clarification - uses requirements_engineer."""
        crew_instance = Crew(
            agents=[self.requirements_engineer()],
            tasks=[self.check_clarification_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={"message": message})
        result_str = str(result).upper()
        
        needs_clarification = "DECISION: YES" in result_str or (
            "YES" in result_str[:100] and "NO" not in result_str[:50]
        )
        
        return needs_clarification
    
    async def analyze_with_context(
        self,
        original_message: str,
        selected_aspects: str,
        aspects_list: str
    ) -> str:
        """Analyze with user-selected context - uses domain_expert."""
        crew_instance = Crew(
            agents=[self.domain_expert()],
            tasks=[self.analyze_with_context_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "original_message": original_message,
            "selected_aspects": selected_aspects,
            "aspects_list": aspects_list
        })
        return str(result)
    
    async def detect_intent(self, user_message: str) -> str:
        """Detect user intent from message - uses requirements_engineer.
        
        Returns:
            Intent name: create_feature, edit_prd, edit_story, or general_discussion
        """
        crew_instance = Crew(
            agents=[self.requirements_engineer()],
            tasks=[self.detect_intent_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={"user_message": user_message})
        result_str = str(result).strip().lower()
        
        # Extract intent from result
        if "create_feature" in result_str:
            return "create_feature"
        elif "edit_prd" in result_str:
            return "edit_prd"
        elif "edit_story" in result_str:
            return "edit_story"
        else:
            return "general_discussion"
    
    async def generate_interview_question(
        self,
        user_message: str,
        collected_info: dict,
        previous_questions: list
    ) -> dict:
        """Generate next interview question - uses requirements_engineer.
        
        Returns:
            Question dict with text, type, options, allow_multiple
        """
        crew_instance = Crew(
            agents=[self.requirements_engineer()],
            tasks=[self.generate_interview_question_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "user_message": user_message,
            "collected_info": json.dumps(collected_info, ensure_ascii=False),
            "previous_questions": json.dumps(previous_questions, ensure_ascii=False)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            # Extract JSON from markdown code blocks if present
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            question_data = json.loads(result_str)
            return question_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse interview question JSON: {e}, result: {result}")
            # Fallback question
            return {
                "text": "Bạn có thể mô tả chi tiết hơn về feature này không?",
                "type": "open",
                "options": [],
                "allow_multiple": False
            }
    
    async def generate_prd_from_interview(
        self,
        original_request: str,
        interview_data: dict
    ) -> dict:
        """Generate PRD from interview data - uses prd_specialist.
        
        Returns:
            PRD dict with project_name, version, overview, features, etc.
        """
        crew_instance = Crew(
            agents=[self.prd_specialist()],
            tasks=[self.generate_prd_from_interview_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "original_request": original_request,
            "interview_data": json.dumps(interview_data, ensure_ascii=False, indent=2)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            # Extract JSON from markdown code blocks
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            prd_data = json.loads(result_str)
            return prd_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse PRD JSON: {e}, result: {result}")
            # Return fallback PRD
            return {
                "project_name": original_request[:50],
                "version": "1.0",
                "overview": str(result)[:500],
                "goals": ["Implement feature"],
                "target_users": ["End users"],
                "features": [{"name": original_request, "description": "Feature implementation"}],
                "acceptance_criteria": ["Feature works as expected"],
                "constraints": [],
                "success_metrics": [],
                "next_steps": ["Review and implement"]
            }
    
    async def extract_user_stories_from_prd(self, prd_data: dict) -> list[dict]:
        """Extract user stories from PRD - uses story_writer.
        
        Returns:
            List of story dicts with title, description, acceptance_criteria, etc.
        """
        crew_instance = Crew(
            agents=[self.story_writer()],
            tasks=[self.extract_user_stories_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "prd_data": json.dumps(prd_data, ensure_ascii=False, indent=2)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            # Extract JSON from markdown code blocks
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            stories = json.loads(result_str)
            if isinstance(stories, list):
                return stories
            else:
                logger.error(f"Expected list of stories, got: {type(stories)}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse stories JSON: {e}, result: {result}")
            return []
    
    async def update_existing_prd(
        self,
        edit_request: str,
        existing_prd: dict
    ) -> dict:
        """Update existing PRD based on edit request - uses prd_specialist.
        
        Returns:
            Updated PRD dict with change_summary field
        """
        crew_instance = Crew(
            agents=[self.prd_specialist()],
            tasks=[self.update_existing_prd_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "edit_request": edit_request,
            "existing_prd": json.dumps(existing_prd, ensure_ascii=False, indent=2)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            # Extract JSON from markdown code blocks
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            updated_prd = json.loads(result_str)
            return updated_prd
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse updated PRD JSON: {e}, result: {result}")
            # Return original with change note
            existing_prd["change_summary"] = f"Failed to update: {edit_request}"
            return existing_prd
    
    async def generate_first_clarification_question(
        self,
        user_message: str,
        missing_info: list
    ) -> dict:
        """Generate first clarification question with multichoice - uses requirements_engineer.
        
        Returns:
            Question dict with text, type, options (including "Other"), context
        """
        crew_instance = Crew(
            agents=[self.requirements_engineer()],
            tasks=[self.generate_first_clarification_question_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "user_message": user_message,
            "missing_info": json.dumps(missing_info, ensure_ascii=False)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            question_data = json.loads(result_str)
            
            # Ensure "Other" option exists
            if "options" in question_data:
                if "Other (Khác - vui lòng mô tả)" not in question_data["options"]:
                    question_data["options"].append("Other (Khác - vui lòng mô tả)")
            
            return question_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse clarification question JSON: {e}, result: {result}")
            # Fallback question
            return {
                "question_text": "Bạn có thể mô tả chi tiết hơn về yêu cầu của mình không?",
                "question_type": "open",
                "options": [],
                "allow_multiple": False,
                "context": "general"
            }
    
    async def generate_next_interview_question(
        self,
        user_message: str,
        collected_info: dict,
        previous_questions: list
    ) -> dict:
        """Generate next interview question based on collected info - uses requirements_engineer.
        
        Returns:
            Question dict with text, type, options (including "Other"), context
        """
        crew_instance = Crew(
            agents=[self.requirements_engineer()],
            tasks=[self.generate_next_interview_question_task()],
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "user_message": user_message,
            "collected_info": json.dumps(collected_info, ensure_ascii=False, indent=2),
            "previous_questions": json.dumps(previous_questions, ensure_ascii=False, indent=2)
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            question_data = json.loads(result_str)
            
            # Ensure "Other" option exists
            if "options" in question_data:
                if "Other (Khác - vui lòng mô tả)" not in question_data["options"]:
                    question_data["options"].append("Other (Khác - vui lòng mô tả)")
            
            return question_data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse next question JSON: {e}, result: {result}")
            # Fallback question
            return {
                "question_text": "Còn thông tin nào khác bạn muốn bổ sung?",
                "question_type": "open",
                "options": [],
                "allow_multiple": False,
                "context": "general"
            }
    
    async def decide_next_action(
        self,
        current_phase: str,
        collected_info: dict,
        last_message: str,
        questions_asked: list,
        prd_status: dict | None
    ) -> dict:
        """Use orchestrator to decide next action - LLM-based intelligent routing.
        
        Returns:
            {
                "action": str,  # ASK_CLARIFICATION, ANALYZE_DOMAIN, GENERATE_PRD, UPDATE_PRD, EXTRACT_STORIES, COMPLETE
                "agent_to_use": str,  # requirements_engineer, domain_expert, prd_specialist, story_writer, none
                "reason": str,  # Brief explanation
                "estimated_missing_info": list  # Optional, only for ASK_CLARIFICATION
            }
        """
        crew_instance = Crew(
            agents=[self.workflow_orchestrator()],
            tasks=[self.decide_next_action_task()],
            process=Process.sequential,
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "current_phase": current_phase,
            "collected_info": json.dumps(collected_info, ensure_ascii=False, indent=2),
            "last_message": last_message,
            "questions_asked": json.dumps(questions_asked, ensure_ascii=False),
            "prd_status": json.dumps(prd_status, ensure_ascii=False, indent=2) if prd_status else "None"
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            # Extract JSON from markdown code blocks
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            action_data = json.loads(result_str)
            
            # Validate required fields
            if "action" not in action_data or "agent_to_use" not in action_data:
                raise ValueError("Missing required fields in orchestrator response")
            
            logger.info(f"[Orchestrator] Decision: {action_data['action']} "
                       f"(agent: {action_data['agent_to_use']}, reason: {action_data.get('reason', 'N/A')})")
            
            return action_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse orchestrator decision: {e}, result: {result}")
            # Fallback: continue with interview if we don't have much info
            if len(questions_asked) < 2:
                return {
                    "action": "ASK_CLARIFICATION",
                    "agent_to_use": "requirements_engineer",
                    "reason": "Fallback to interview mode (orchestrator parse failed)",
                    "estimated_missing_info": []
                }
            else:
                # If we already asked questions, proceed to PRD
                return {
                    "action": "GENERATE_PRD",
                    "agent_to_use": "prd_specialist",
                    "reason": "Fallback to PRD generation (orchestrator parse failed, have some info)",
                    "estimated_missing_info": []
                }
    
    async def analyze_and_route(
        self,
        user_message: str,
        current_phase: str,
        collected_info: dict,
        questions_asked: list,
        has_existing_prd: bool,
        has_stories: bool
    ) -> dict:
        """Orchestrator analyzes message and decides intent + next action.
        
        Returns:
            {
                "intent": str,
                "action": str,
                "agent_to_use": str,
                "reason": str,
                "estimated_missing_info": list,  # optional
                "error_message": str  # optional
            }
        """
        crew_instance = Crew(
            agents=[self.workflow_orchestrator()],
            tasks=[self.analyze_and_route_task()],
            process=Process.sequential,
            verbose=False,
        )
        
        result = await crew_instance.kickoff_async(inputs={
            "user_message": user_message,
            "current_phase": current_phase,
            "collected_info": json.dumps(collected_info, ensure_ascii=False, indent=2),
            "questions_asked": json.dumps(questions_asked, ensure_ascii=False),
            "has_existing_prd": "yes" if has_existing_prd else "no",
            "has_stories": "yes" if has_stories else "no"
        })
        
        # Parse JSON response
        try:
            result_str = str(result).strip()
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            routing_data = json.loads(result_str)
            
            # Validate required fields
            required_fields = ["intent", "action", "agent_to_use"]
            if not all(field in routing_data for field in required_fields):
                raise ValueError("Missing required fields in orchestrator response")
            
            logger.info(
                f"[Orchestrator] Intent: {routing_data['intent']}, "
                f"Action: {routing_data['action']}, "
                f"Agent: {routing_data['agent_to_use']}"
            )
            
            return routing_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse orchestrator routing: {e}, result: {result}")
            # Fallback
            return {
                "intent": "create_feature",
                "action": "ASK_CLARIFICATION",
                "agent_to_use": "requirements_engineer",
                "reason": "Fallback routing (parse failed)",
                "estimated_missing_info": []
            }
