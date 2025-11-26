"""Business Analyst Crew - Requirements analysis and PRD generation."""

import json
import logging

from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task


logger = logging.getLogger(__name__)


@CrewBase
class BusinessAnalystCrew:
    """Business Analyst crew for requirements analysis."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def business_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['business_analyst'],
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
        """Analyze requirements for a user message."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
            tasks=[self.analyze_requirements_task()],
            verbose=True,
        )
        
        result = await crew_instance.kickoff_async(inputs={"user_message": user_message})
        return str(result)
    
    async def check_needs_clarification(self, message: str) -> bool:
        """Check if message needs clarification."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Analyze with user-selected context."""
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Detect user intent from message.
        
        Returns:
            Intent name: create_feature, edit_prd, edit_story, or general_discussion
        """
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Generate next interview question.
        
        Returns:
            Question dict with text, type, options, allow_multiple
        """
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Generate PRD from interview data.
        
        Returns:
            PRD dict with project_name, version, overview, features, etc.
        """
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Extract user stories from PRD.
        
        Returns:
            List of story dicts with title, description, acceptance_criteria, etc.
        """
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
        """Update existing PRD based on edit request.
        
        Returns:
            Updated PRD dict with change_summary field
        """
        crew_instance = Crew(
            agents=[self.business_analyst()],
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
