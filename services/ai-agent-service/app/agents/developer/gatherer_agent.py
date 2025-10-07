"""
Developer Agent - Gatherer Implementation

This module implements the Developer Agent's gatherer functionality for collecting
and analyzing product requirements. It follows the Developer Agent Workflow
and integrates with the existing Product Owner gatherer patterns.
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..product_owner.gatherer.state import BriefState
from ..product_owner.gatherer import nodes as po_nodes


class TaskStatus(str, Enum):
    """Task status enumeration"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    TESTING = "testing"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(str, Enum):
    """Task priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DeveloperGathererState(BriefState):
    """Extended state for Developer Agent gatherer"""
    
    # Task management
    task_id: Optional[str] = None
    task_description: Optional[str] = None
    acceptance_criteria: List[str] = []
    story_points: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    
    # Developer-specific fields
    technical_requirements: List[str] = []
    dependencies: List[str] = []
    estimated_effort: Optional[str] = None
    complexity_score: Optional[float] = None
    
    # Code generation
    code_solution: Optional[str] = None
    test_cases: List[str] = []
    documentation: Optional[str] = None
    
    # Quality gates
    lint_passed: bool = False
    tests_passed: bool = False
    coverage_score: Optional[float] = None
    security_scan_passed: bool = False


class DeveloperGathererAgent:
    """Developer Agent with gatherer capabilities"""
    
    def __init__(self):
        """Initialize Developer Agent"""
        self.langfuse = Langfuse(
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
            host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        self.callback_handler = CallbackHandler()
        self.llm = ChatOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            callbacks=[self.callback_handler]
        )
        self.app, self.memory = self._build_graph()
    
    def _build_graph(self) -> tuple:
        """Build LangGraph workflow for Developer Agent"""
        g = StateGraph(DeveloperGathererState)
        
        # Add nodes
        g.add_node("initialize", self._initialize)
        g.add_node("analyze_requirements", self._analyze_requirements)
        g.add_node("estimate_effort", self._estimate_effort)
        g.add_node("break_down_task", self._break_down_task)
        g.add_node("implement_solution", self._implement_solution)
        g.add_node("write_tests", self._write_tests)
        g.add_node("run_quality_gates", self._run_quality_gates)
        g.add_node("create_pull_request", self._create_pull_request)
        g.add_node("handle_feedback", self._handle_feedback)
        g.add_node("finalize", self._finalize)
        
        # Set entry point
        g.set_entry_point("initialize")
        
        # Add edges
        g.add_edge("initialize", "analyze_requirements")
        g.add_edge("analyze_requirements", "estimate_effort")
        
        # Conditional edge after effort estimation
        g.add_conditional_edges(
            "estimate_effort",
            self._after_effort_estimation,
            {
                "break_down": "break_down_task",
                "implement": "implement_solution"
            }
        )
        
        g.add_edge("break_down_task", "implement_solution")
        g.add_edge("implement_solution", "write_tests")
        g.add_edge("write_tests", "run_quality_gates")
        
        # Conditional edge after quality gates
        g.add_conditional_edges(
            "run_quality_gates",
            self._after_quality_gates,
            {
                "pass": "create_pull_request",
                "fail": "handle_feedback",
                "retry": "implement_solution"
            }
        )
        
        g.add_edge("create_pull_request", "finalize")
        g.add_edge("handle_feedback", "implement_solution")
        g.add_edge("finalize", END)
        
        # Compile with memory
        memory = MemorySaver()
        app = g.compile(checkpointer=memory)
        return app, memory
    
    def _initialize(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Initialize Developer Agent session"""
        if not state.get("task_id"):
            state["task_id"] = f"task-{uuid.uuid4()}"
        
        state["status"] = TaskStatus.IN_PROGRESS
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        
        return state
    
    def _analyze_requirements(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Analyze task requirements and acceptance criteria"""
        task_description = state.get("task_description", "")
        
        # Use LLM to analyze requirements
        system_prompt = """Bạn là một Developer Agent chuyên nghiệp. 
        Phân tích task description và xác định:
        1. Functional requirements
        2. Non-functional requirements  
        3. Technical constraints
        4. Dependencies
        5. Acceptance criteria
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Task: {task_description}")
        ]
        
        response = self.llm.invoke(messages)
        
        # Parse response and update state
        # This would be more sophisticated in practice
        state["technical_requirements"] = [task_description]
        state["dependencies"] = []
        
        return state
    
    def _estimate_effort(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Estimate development effort and complexity"""
        requirements = state.get("technical_requirements", [])
        
        # Simple complexity scoring
        complexity_score = min(len(requirements) * 0.2, 1.0)
        state["complexity_score"] = complexity_score
        
        # Estimate effort based on complexity
        if complexity_score > 0.7:
            state["estimated_effort"] = "High (3-5 days)"
        elif complexity_score > 0.4:
            state["estimated_effort"] = "Medium (1-3 days)"
        else:
            state["estimated_effort"] = "Low (< 1 day)"
        
        return state
    
    def _break_down_task(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Break down complex tasks into subtasks"""
        # Implementation for task breakdown
        state["technical_requirements"] = [
            "Setup development environment",
            "Implement core functionality", 
            "Write unit tests",
            "Create documentation"
        ]
        return state
    
    def _implement_solution(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Implement the code solution"""
        requirements = state.get("technical_requirements", [])
        
        # Generate code solution using LLM
        system_prompt = """Bạn là một expert Python developer.
        Implement code solution theo requirements với:
        - Clean, maintainable code
        - Type hints
        - Docstrings
        - Error handling
        - Best practices
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Requirements: {requirements}")
        ]
        
        response = self.llm.invoke(messages)
        state["code_solution"] = response.content
        
        return state
    
    def _write_tests(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Write unit tests for the solution"""
        code_solution = state.get("code_solution", "")
        
        # Generate test cases using LLM
        system_prompt = """Bạn là một expert test engineer.
        Tạo comprehensive unit tests với:
        - Happy path tests
        - Edge cases
        - Error conditions
        - Mock external dependencies
        - 80%+ coverage target
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Code to test: {code_solution}")
        ]
        
        response = self.llm.invoke(messages)
        state["test_cases"] = [response.content]
        
        return state
    
    def _run_quality_gates(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Run quality gates (lint, test, security)"""
        # Simulate quality gate results
        state["lint_passed"] = True
        state["tests_passed"] = True
        state["coverage_score"] = 0.85
        state["security_scan_passed"] = True
        
        return state
    
    def _create_pull_request(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Create pull request for code review"""
        # Implementation for PR creation
        state["status"] = TaskStatus.IN_REVIEW
        return state
    
    def _handle_feedback(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Handle feedback from code review"""
        # Implementation for feedback handling
        return state
    
    def _finalize(self, state: DeveloperGathererState) -> DeveloperGathererState:
        """Finalize the task"""
        state["status"] = TaskStatus.DONE
        state["finalized"] = True
        return state
    
    def _after_effort_estimation(self, state: DeveloperGathererState) -> str:
        """Determine next step after effort estimation"""
        complexity = state.get("complexity_score", 0)
        if complexity > 0.7:
            return "break_down"
        return "implement"
    
    def _after_quality_gates(self, state: DeveloperGathererState) -> str:
        """Determine next step after quality gates"""
        if (state.get("lint_passed") and 
            state.get("tests_passed") and 
            state.get("security_scan_passed")):
            return "pass"
        return "fail"
    
    async def start_task(
        self,
        task_description: str,
        acceptance_criteria: List[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Start a new development task"""
        
        if not session_id:
            session_id = f"dev-session-{uuid.uuid4()}"
        
        initial_state = {
            "task_description": task_description,
            "acceptance_criteria": acceptance_criteria or [],
            "priority": priority,
            "last_user_input": task_description
        }
        
        # Run workflow
        result = self.app.invoke(
            initial_state,
            config={
                "configurable": {"thread_id": session_id},
                "recursion_limit": 8,
                "callbacks": [self.callback_handler]
            }
        )
        
        return {
            "session_id": session_id,
            "task_id": result.get("task_id"),
            "status": result.get("status"),
            "code_solution": result.get("code_solution"),
            "test_cases": result.get("test_cases"),
            "quality_gates": {
                "lint_passed": result.get("lint_passed"),
                "tests_passed": result.get("tests_passed"),
                "coverage_score": result.get("coverage_score"),
                "security_scan_passed": result.get("security_scan_passed")
            }
        }
    
    async def continue_task(
        self,
        session_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        """Continue existing development task"""
        
        # Get current state
        config = {"configurable": {"thread_id": session_id}}
        current_state = self.app.get_state(config)
        
        if not current_state:
            raise ValueError(f"Session {session_id} not found")
        
        # Update state with new input
        updated_state = {
            **current_state.values,
            "last_user_input": user_input
        }
        
        # Continue workflow
        result = self.app.invoke(updated_state, config=config)
        
        return {
            "session_id": session_id,
            "task_id": result.get("task_id"),
            "status": result.get("status"),
            "code_solution": result.get("code_solution"),
            "test_cases": result.get("test_cases")
        }


# Factory function for easy instantiation
def create_developer_gatherer() -> DeveloperGathererAgent:
    """Create a new Developer Gatherer Agent instance"""
    return DeveloperGathererAgent()


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = create_developer_gatherer()
        
        # Start a new task
        result = await agent.start_task(
            task_description="Implement user authentication API endpoint",
            acceptance_criteria=[
                "POST /api/v1/auth/login accepts email and password",
                "Returns JWT token on successful authentication",
                "Returns 401 for invalid credentials",
                "Rate limiting: 5 attempts per minute"
            ],
            priority=TaskPriority.HIGH
        )
        
        print("Task started:", result)
    
    asyncio.run(main())
