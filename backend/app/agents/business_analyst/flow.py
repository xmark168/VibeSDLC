"""Business Analyst Flow - Requirements analysis and PRD generation using Flows.

ARCHITECTURE NOTE:
Refactored from Crew hierarchical process to Flow-based architecture for:
- Explicit control flow with @start, @listen, @router decorators
- Better state management with Pydantic models
- Improved observability with flow visualization
- Easier testing and extension
"""

import json
import logging
from typing import Optional, Any
from pathlib import Path
from uuid import UUID

from crewai.flow.flow import Flow, listen, router, start, or_
from crewai import Agent, LLM
from pydantic import BaseModel, Field
from litellm import completion

from app.agents.core.agent_context import AgentContext
from .tools import (
    load_prd_from_file, save_prd_to_file, update_prd_section,
    load_user_stories_from_file, save_user_stories_to_file, add_user_story,
    validate_prd_completeness, validate_user_story,
    create_ask_user_question_tool
)

logger = logging.getLogger(__name__)


class BAFlowState(BaseModel):
    """Structured state for BA workflow with Pydantic validation."""
    
    user_message: str = ""
    intent: str = "unknown"  # interview | prd_create | prd_update | stories | domain_analysis
    collected_info: dict = Field(default_factory=dict)
    existing_prd: Optional[dict] = None
    result: Optional[dict] = None
    phase: str = "initial"
    is_complete: bool = False
    questions_asked: list = Field(default_factory=list)
    project_path: str = ""
    agent_name: str = "Business Analyst"
    personality_traits: list = Field(default_factory=list)
    communication_style: str = "professional and clear"


class BusinessAnalystFlow(Flow[BAFlowState]):
    """Flow-based Business Analyst workflow.
    
    Replaces hierarchical Crew with explicit event-driven flow:
    - Entry: analyze_user_request (@start)
    - Router: route_workflow based on intent
    - Branches: gather_requirements, generate_prd, update_prd, extract_stories, analyze_domain
    - Exit: finalize_output
    """
    
    def __init__(
        self,
        agent_context: AgentContext,
        project_files: Any,
        agent_name: str = "Business Analyst",
        personality_traits: list[str] | None = None,
        communication_style: str | None = None,
        initial_state: Optional[BAFlowState] = None
    ):
        """Initialize BA Flow.
        
        Args:
            agent_context: Context for agent operations (messaging, question asking)
            project_files: ProjectFiles instance for file operations
            agent_name: Human-friendly name
            personality_traits: List of personality traits
            communication_style: Communication style description
            initial_state: Initial state (optional)
        """
        super().__init__(initial_state)
        
        self.agent_context = agent_context
        self.project_files = project_files
        self.llm = LLM(model="gpt-4o", temperature=0.2)
        
        # Store persona info in state
        if not self.state.agent_name:
            self.state.agent_name = agent_name
        if not self.state.personality_traits:
            self.state.personality_traits = personality_traits or []
        if not self.state.communication_style:
            self.state.communication_style = communication_style or "professional and clear"
        
        # Create tools
        self.ask_user_question_tool = create_ask_user_question_tool(agent_context)
        
        # Load agent configs for creating Agent instances
        from pathlib import Path
        import yaml
        config_path = Path(__file__).parent / "config" / "agents.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.agents_config = yaml.safe_load(f)
        
        logger.info(f"BusinessAnalystFlow initialized: {agent_name}")
    
    def _build_persona_description(self) -> str:
        """Build persona description for agents."""
        traits_str = ", ".join(self.state.personality_traits) if self.state.personality_traits else "professional"
        return f"""You are {self.state.agent_name}, a Business Analyst.

Personality Traits: {traits_str}
Communication Style: {self.state.communication_style}

Embody this personality in all responses while maintaining professionalism."""
    
    # ==================== ENTRY POINT ====================
    
    @start()
    def analyze_user_request(self):
        """Analyze user request to determine intent and workflow path.
        
        Determines:
        - interview: Need to gather more requirements
        - prd_create: Create new PRD
        - prd_update: Update existing PRD
        - stories: Extract user stories from PRD
        - domain_analysis: Provide domain insights
        
        Returns:
            intent string for router
        """
        logger.info(f"[Flow] Analyzing user request: {self.state.user_message[:80]}...")
        
        # Load existing PRD if available
        if self.project_files:
            try:
                existing_prd = self._run_async(self.project_files.load_prd())
                if existing_prd:
                    self.state.existing_prd = existing_prd
                    logger.info("[Flow] Loaded existing PRD")
            except Exception as e:
                logger.debug(f"[Flow] No existing PRD: {e}")
        
        # Use LLM to analyze intent
        prompt = f"""Analyze this user request and determine the intent:

User Message: {self.state.user_message}

Existing PRD: {"Yes" if self.state.existing_prd else "No"}
Collected Info: {json.dumps(self.state.collected_info, ensure_ascii=False)}

Choose ONE intent:
1. "interview" - User request is vague/incomplete, need to ask clarification questions
2. "prd_create" - User wants to create a new PRD (sufficient info provided)
3. "prd_update" - User wants to update existing PRD
4. "stories" - User wants to extract user stories from PRD
5. "domain_analysis" - User wants domain/business analysis

Return ONLY the intent keyword (interview/prd_create/prd_update/stories/domain_analysis).
"""
        
        try:
            response = completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            intent = response["choices"][0]["message"]["content"].strip().lower()
            
            # Validate intent
            valid_intents = ["interview", "prd_create", "prd_update", "stories", "domain_analysis"]
            if intent not in valid_intents:
                logger.warning(f"[Flow] Invalid intent '{intent}', defaulting to 'interview'")
                intent = "interview"
            
            self.state.intent = intent
            logger.info(f"[Flow] Determined intent: {intent}")
            
            return intent
            
        except Exception as e:
            logger.error(f"[Flow] Intent analysis failed: {e}", exc_info=True)
            self.state.intent = "interview"
            return "interview"
    
    # ==================== ROUTER ====================
    
    @router(analyze_user_request)
    def route_workflow(self):
        """Route to appropriate workflow based on determined intent.
        
        Returns:
            Route label for @listen decorators
        """
        route_map = {
            "interview": "gather_requirements",
            "prd_create": "generate_prd",
            "prd_update": "update_prd",
            "stories": "extract_stories",
            "domain_analysis": "analyze_domain"
        }
        
        route = route_map.get(self.state.intent, "gather_requirements")
        logger.info(f"[Flow] Routing to: {route}")
        
        return route
    
    # ==================== WORKFLOW BRANCHES ====================
    
    @listen("gather_requirements")
    def gather_requirements(self):
        """Conduct requirements interview - ask clarification questions.
        
        Uses requirements_engineer persona to generate targeted questions.
        """
        logger.info("[Flow] Gathering requirements through interview...")
        
        try:
            # Create requirements engineer agent
            persona = self._build_persona_description()
            agent_config = self.agents_config['requirements_engineer']
            
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=f"{persona}\n\n{agent_config['backstory']}",
                llm=self.llm,
                tools=[self.ask_user_question_tool],
                verbose=True,
                allow_delegation=False
            )
            
            # Task: Generate 2-3 targeted clarification questions
            task_prompt = f"""Based on the user's request, generate 2-3 targeted clarification questions.

User Request: {self.state.user_message}
Existing PRD: {json.dumps(self.state.existing_prd, ensure_ascii=False) if self.state.existing_prd else "None"}
Already Collected: {json.dumps(self.state.collected_info, ensure_ascii=False)}

Focus on:
- Missing critical information (target users, goals, constraints)
- Unclear requirements or scope
- Technical or business context needed

Use the ask_user_question tool to ask ONE question at a time.
Ask the most important question first.

Return your questions as JSON:
{{
    "questions": ["question1", "question2"],
    "rationale": "why these questions are needed",
    "missing_info": ["info1", "info2"]
}}
"""
            
            result = agent.execute_task(task_prompt)
            
            # Parse result
            result_data = self._parse_json_result(str(result))
            
            questions = result_data.get("questions", [])
            if not questions:
                # Fallback if agent didn't generate questions
                questions = [f"Can you provide more details about: {self.state.user_message[:100]}?"]
            
            # Store questions
            self.state.questions_asked.extend(questions)
            
            return {
                "questions": questions,
                "context": result_data.get("rationale", "Need more information"),
                "missing_info": result_data.get("missing_info", [])
            }
            
        except Exception as e:
            logger.error(f"[Flow] Requirements gathering failed: {e}", exc_info=True)
            return {
                "questions": [f"Can you provide more details about your request?"],
                "context": "Need clarification",
                "error": str(e)
            }
    
    @listen("generate_prd")
    def generate_prd(self):
        """Generate comprehensive PRD document.
        
        Uses prd_specialist persona to create structured PRD following industry standards.
        """
        logger.info("[Flow] Generating PRD...")
        
        try:
            # Create PRD specialist agent
            persona = self._build_persona_description()
            agent_config = self.agents_config['prd_specialist']
            
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=f"{persona}\n\n{agent_config['backstory']}",
                llm=self.llm,
                tools=[save_prd_to_file, validate_prd_completeness],
                verbose=True,
                allow_delegation=False
            )
            
            # Task: Generate complete PRD
            task_prompt = f"""Generate a comprehensive Product Requirements Document (PRD).

User Request: {self.state.user_message}
Collected Information: {json.dumps(self.state.collected_info, ensure_ascii=False)}
Existing PRD (reference): {json.dumps(self.state.existing_prd, ensure_ascii=False) if self.state.existing_prd else "None"}

Include these sections:
1. project_name: Clear project name
2. version: Version number (e.g., "1.0")
3. overview: Executive summary (2-3 paragraphs)
4. goals: Business objectives and success metrics
5. target_users: User personas and roles
6. features: List of functional requirements with priorities (P0/P1/P2)
7. non_functional_requirements: Performance, security, scalability
8. acceptance_criteria: Clear "definition of done" for each feature
9. technical_constraints: Platform, integrations, limitations
10. dependencies: External dependencies
11. out_of_scope: What's explicitly NOT included

Return the PRD as valid JSON following this structure.
Ensure all requirements are clear, testable, and actionable.
"""
            
            result = agent.execute_task(task_prompt)
            
            # Parse PRD
            prd_data = self._parse_json_result(str(result))
            
            # Validate completeness
            validation_str = validate_prd_completeness(json.dumps(prd_data))
            validation = json.loads(validation_str) if isinstance(validation_str, str) else validation_str
            
            if not validation.get("is_complete", False):
                logger.warning(f"[Flow] PRD incomplete: {validation.get('missing_sections')}")
            
            # Save PRD to files
            if self.project_files and self.state.project_path:
                try:
                    save_result = save_prd_to_file(self.state.project_path, json.dumps(prd_data))
                    logger.info(f"[Flow] PRD saved: {save_result}")
                except Exception as e:
                    logger.error(f"[Flow] Failed to save PRD: {e}")
            
            return prd_data
            
        except Exception as e:
            logger.error(f"[Flow] PRD generation failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "project_name": "Failed PRD Generation",
                "overview": f"Error generating PRD: {str(e)}"
            }
    
    @listen("update_prd")
    def update_prd(self):
        """Update existing PRD sections.
        
        Loads existing PRD, modifies requested sections, saves back.
        """
        logger.info("[Flow] Updating PRD...")
        
        try:
            if not self.state.existing_prd:
                return {"error": "No existing PRD to update"}
            
            # Create PRD specialist agent
            persona = self._build_persona_description()
            agent_config = self.agents_config['prd_specialist']
            
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=f"{persona}\n\n{agent_config['backstory']}",
                llm=self.llm,
                tools=[update_prd_section, validate_prd_completeness],
                verbose=True,
                allow_delegation=False
            )
            
            # Task: Update PRD
            task_prompt = f"""Update the existing PRD based on user request.

User Request: {self.state.user_message}
Current PRD: {json.dumps(self.state.existing_prd, ensure_ascii=False, indent=2)}
Collected Info: {json.dumps(self.state.collected_info, ensure_ascii=False)}

Identify which sections need updates and provide updated content.
Maintain existing structure and quality standards.

Return the complete updated PRD as JSON with a "change_summary" field explaining what changed.
"""
            
            result = agent.execute_task(task_prompt)
            
            # Parse updated PRD
            updated_prd = self._parse_json_result(str(result))
            
            # Save updated PRD
            if self.project_files and self.state.project_path:
                try:
                    save_result = save_prd_to_file(self.state.project_path, json.dumps(updated_prd))
                    logger.info(f"[Flow] PRD updated: {save_result}")
                except Exception as e:
                    logger.error(f"[Flow] Failed to save updated PRD: {e}")
            
            return updated_prd
            
        except Exception as e:
            logger.error(f"[Flow] PRD update failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "change_summary": f"Update failed: {str(e)}"
            }
    
    @listen("extract_stories")
    def extract_stories(self):
        """Extract user stories from PRD.
        
        Uses story_writer persona to create INVEST-compliant user stories.
        """
        logger.info("[Flow] Extracting user stories...")
        
        try:
            if not self.state.existing_prd:
                return {"error": "No PRD available to extract stories from"}
            
            # Create story writer agent
            persona = self._build_persona_description()
            agent_config = self.agents_config['story_writer']
            
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=f"{persona}\n\n{agent_config['backstory']}",
                llm=self.llm,
                tools=[save_user_stories_to_file, validate_user_story],
                verbose=True,
                allow_delegation=False
            )
            
            # Task: Extract stories
            task_prompt = f"""Extract user stories from the PRD following INVEST principles.

PRD: {json.dumps(self.state.existing_prd, ensure_ascii=False, indent=2)}

For each feature in the PRD, create user stories with:
- title: As a [role], I want [feature], so that [benefit]
- description: Detailed context and implementation notes
- acceptance_criteria: List of Gherkin-format criteria (Given/When/Then)
- story_points: Fibonacci estimation (1, 2, 3, 5, 8, 13)
- priority: High/Medium/Low based on business value
- dependencies: Links to other stories if needed

Return array of story objects as JSON.
Each story should be independent, valuable, estimable, small, and testable.
"""
            
            result = agent.execute_task(task_prompt)
            
            # Parse stories
            stories = self._parse_json_result(str(result))
            
            # Ensure stories is a list
            if isinstance(stories, dict) and "stories" in stories:
                stories = stories["stories"]
            elif not isinstance(stories, list):
                stories = [stories]
            
            # Save stories to files
            if self.project_files and self.state.project_path and isinstance(stories, list):
                try:
                    save_result = save_user_stories_to_file(self.state.project_path, json.dumps(stories))
                    logger.info(f"[Flow] Stories saved: {save_result}")
                except Exception as e:
                    logger.error(f"[Flow] Failed to save stories: {e}")
            
            return stories
            
        except Exception as e:
            logger.error(f"[Flow] Story extraction failed: {e}", exc_info=True)
            return [{"error": str(e), "title": "Story extraction failed"}]
    
    @listen("analyze_domain")
    def analyze_domain(self):
        """Provide domain and business context analysis.
        
        Uses domain_expert persona to analyze business domain.
        """
        logger.info("[Flow] Analyzing domain...")
        
        try:
            # Create domain expert agent
            persona = self._build_persona_description()
            agent_config = self.agents_config['domain_expert']
            
            agent = Agent(
                role=agent_config['role'],
                goal=agent_config['goal'],
                backstory=f"{persona}\n\n{agent_config['backstory']}",
                llm=self.llm,
                tools=[self.ask_user_question_tool],
                verbose=True,
                allow_delegation=False
            )
            
            # Task: Domain analysis
            task_prompt = f"""Provide domain and business context analysis.

User Request: {self.state.user_message}
Existing PRD: {json.dumps(self.state.existing_prd, ensure_ascii=False) if self.state.existing_prd else "None"}
Collected Info: {json.dumps(self.state.collected_info, ensure_ascii=False)}

Analyze:
1. Business domain (e-commerce, healthcare, finance, etc.)
2. Key business processes and workflows
3. Industry best practices and standards
4. Regulatory and compliance considerations
5. Domain-specific features or requirements
6. Common challenges and solutions

Return analysis as JSON:
{{
    "domain": "identified domain",
    "analysis_text": "detailed analysis (2-3 paragraphs)",
    "key_insights": ["insight1", "insight2", ...],
    "best_practices": ["practice1", "practice2", ...],
    "recommendations": ["recommendation1", "recommendation2", ...]
}}
"""
            
            result = agent.execute_task(task_prompt)
            
            # Parse analysis
            analysis = self._parse_json_result(str(result))
            
            return analysis
            
        except Exception as e:
            logger.error(f"[Flow] Domain analysis failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "analysis_text": f"Domain analysis failed: {str(e)}"
            }
    
    # ==================== FINALIZATION ====================
    
    @listen(or_(gather_requirements, generate_prd, update_prd, extract_stories, analyze_domain))
    def finalize_output(self, workflow_result):
        """Finalize output and prepare response for user.
        
        Args:
            workflow_result: Result from workflow branch
            
        Returns:
            Formatted final output
        """
        logger.info(f"[Flow] Finalizing output for intent: {self.state.intent}")
        
        # Store result in state
        self.state.result = workflow_result
        self.state.phase = self.state.intent
        self.state.is_complete = True
        
        # Generate summary and next steps based on intent
        summary = ""
        next_steps = []
        
        if self.state.intent == "interview":
            questions = workflow_result.get("questions", [])
            summary = f"Generated {len(questions)} clarification questions to gather complete requirements."
            next_steps = [
                "Answer the clarification questions",
                "Provide any additional context needed",
                "Once requirements are complete, I'll generate the PRD"
            ]
        
        elif self.state.intent == "prd_create":
            project_name = workflow_result.get("project_name", "Project")
            summary = f"Successfully generated comprehensive PRD for '{project_name}'."
            next_steps = [
                "Review the PRD document",
                "Request updates if needed",
                "Extract user stories when ready",
                "Share PRD with stakeholders"
            ]
        
        elif self.state.intent == "prd_update":
            change_summary = workflow_result.get("change_summary", "PRD updated")
            summary = f"PRD updated successfully. {change_summary}"
            next_steps = [
                "Review the updated sections",
                "Request further updates if needed",
                "Re-extract user stories if PRD changed significantly"
            ]
        
        elif self.state.intent == "stories":
            story_count = len(workflow_result) if isinstance(workflow_result, list) else 0
            summary = f"Successfully extracted {story_count} user stories from PRD."
            next_steps = [
                "Review user stories for completeness",
                "Refine story points and priorities",
                "Add to sprint backlog",
                "Share with development team"
            ]
        
        elif self.state.intent == "domain_analysis":
            domain = workflow_result.get("domain", "Unknown") if isinstance(workflow_result, dict) else "Unknown"
            summary = f"Completed domain analysis for {domain} domain."
            next_steps = [
                "Review domain insights and recommendations",
                "Apply best practices to requirements",
                "Consider domain-specific constraints",
                "Proceed with PRD generation"
            ]
        
        # Build final output
        final_output = {
            "action_taken": self.state.intent,
            "result": workflow_result,
            "summary": summary,
            "next_steps": next_steps,
            "state_id": str(self.state.id) if hasattr(self.state, 'id') else None
        }
        
        logger.info(f"[Flow] Flow completed: {self.state.intent}")
        
        return final_output
    
    # ==================== HELPER METHODS ====================
    
    def _run_async(self, coro):
        """Run async coroutine in sync context."""
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro)
    
    def _parse_json_result(self, result_str: str) -> dict | list:
        """Parse JSON result with fallback."""
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            return json.loads(result_str)
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.warning(f"[Flow] Could not parse result as JSON: {e}")
            return {"raw_result": result_str, "parse_error": str(e)}
