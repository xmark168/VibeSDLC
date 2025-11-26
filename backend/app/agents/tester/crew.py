"""Tester Crew - Integration test generation for Next.js + Prisma."""

import json
import logging
from datetime import datetime
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, crew, task
from app.agents.tester.tools import get_tester_tools

logger = logging.getLogger(__name__)


@CrewBase
class TesterCrew:
    """Multi-agent Tester crew for integration test generation."""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'
    
    @agent
    def test_strategist(self) -> Agent:
        """Test strategy and planning specialist with DB query tool"""
        tools = get_tester_tools()
        return Agent(
            role="Integration Test Strategist",
            goal="Analyze user stories in REVIEW status and create comprehensive integration test scenarios for Next.js API + Prisma",
            backstory=(
                "You are a senior QA Engineer specializing in Next.js and Prisma integration testing. "
                "You excel at reading acceptance criteria (GIVEN-WHEN-THEN format) and identifying API endpoints from stories. "
                "You map acceptance criteria to database operations and create test scenarios that verify both API and DB state."
            ),
            verbose=True,
            allow_delegation=False,
            tools=tools
        )
    
    @agent
    def test_case_writer(self) -> Agent:
        """Test case writing specialist"""
        return Agent(
            role="Test Case Writer",
            goal="Write detailed, executable test cases for integration testing",
            backstory=(
                "You are a meticulous QA Engineer who writes crystal-clear test cases for integration testing. "
                "Your test cases follow the AAA pattern (Arrange, Act, Assert) and include both API response verification and database state validation. "
                "You follow industry standards: Test ID (TC-INT-XXX), Title, Steps, Expected Results for both API and DB."
            ),
            verbose=True,
            allow_delegation=False
        )
    
    @agent
    def test_automation_engineer(self) -> Agent:
        """Test automation code generator for Next.js + Jest"""
        tools = get_tester_tools()
        return Agent(
            role="Next.js Test Automation Engineer",
            goal="Generate executable Jest integration tests for Next.js API + Prisma DB",
            backstory=(
                "You are an expert in writing integration tests for Next.js applications using Jest and Prisma. "
                "You write clean, maintainable test code following Next.js testing patterns: "
                "- Use NextRequest for API testing "
                "- Import API handlers directly from app/api/ "
                "- Use Prisma Client for DB verification "
                "- Setup/teardown with beforeAll, afterAll, beforeEach "
                "- AAA pattern (Arrange, Act, Assert) "
                "Your tests are ready to execute with 'npm test'."
            ),
            verbose=True,
            allow_delegation=False,
            tools=tools
        )
    
    @task
    def analyze_stories_task(self) -> Task:
        """Analyze user stories from DB"""
        return Task(
            description=(
                "Read user stories with REVIEW status from database using query_stories_from_db tool.\n\n"
                "Input:\n"
                "- project_id: {project_id}\n"
                "- story_ids: {story_ids} (optional filter)\n\n"
                "For each story, analyze:\n"
                "1. Title and description (user perspective)\n"
                "2. Acceptance criteria (GIVEN-WHEN-THEN format) - identify API endpoint\n"
                "3. Database operations mentioned in AC\n"
                "4. Test scenarios: Happy path, error cases, edge cases\n\n"
                "Output JSON with test scenarios for all stories."
            ),
            expected_output="JSON array of test scenarios for all stories",
            agent=self.test_strategist()
        )
    
    @task
    def generate_test_cases_task(self) -> Task:
        """Generate detailed test cases"""
        return Task(
            description=(
                "Based on test scenarios from previous task, write detailed integration test cases.\n\n"
                "For each scenario, create test case with:\n"
                "- Test ID (TC-INT-001, TC-INT-002, ...)\n"
                "- Title (clear, describes API + DB verification)\n"
                "- Test Steps: Arrange (setup DB), Act (call API), Assert (verify response + DB)\n"
                "- Expected Results (both API and DB)\n\n"
                "Output JSON array of detailed test cases."
            ),
            expected_output="JSON array of detailed test cases",
            agent=self.test_case_writer()
        )
    
    @task
    def generate_test_file_task(self) -> Task:
        """Generate Next.js integration test file"""
        return Task(
            description=(
                "Convert test cases into Next.js integration test code.\n\n"
                "Input: project_path={project_path}, timestamp={timestamp}\n\n"
                "Generate ONE TypeScript file with Jest tests using NextRequest + Prisma.\n"
                "Use generate_test_file tool to save.\n"
                "Filename: review-batch-{timestamp}.integration.test.ts\n\n"
                "Output JSON with filename, path, test_count, stories_covered."
            ),
            expected_output="JSON object with test file info",
            agent=self.test_automation_engineer()
        )
    
    async def generate_tests_from_stories(
        self,
        project_id: str,
        story_ids: list[str],
        project_path: str,
        tech_stack: str = "nodejs-react"
    ) -> dict:
        """Generate integration tests for user stories in REVIEW status."""
        logger.info(f"[TesterCrew] Starting integration test generation for project {project_id}")
        
        crew_instance = Crew(
            agents=[
                self.test_strategist(),
                self.test_case_writer(),
                self.test_automation_engineer()
            ],
            tasks=[
                self.analyze_stories_task(),
                self.generate_test_cases_task(),
                self.generate_test_file_task()
            ],
            process=Process.sequential,
            verbose=True
        )
        
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        
        result = await crew_instance.kickoff_async(inputs={
            "project_id": project_id,
            "story_ids": story_ids or [],
            "project_path": project_path,
            "tech_stack": tech_stack,
            "timestamp": timestamp
        })
        
        try:
            result_str = str(result).strip()
            if "```json" in result_str:
                result_str = result_str.split("```json")[1].split("```")[0].strip()
            elif "```" in result_str:
                result_str = result_str.split("```")[1].split("```")[0].strip()
            
            result_data = json.loads(result_str)
            logger.info(f"[TesterCrew] Successfully generated integration tests")
            return result_data
            
        except json.JSONDecodeError as e:
            logger.error(f"[TesterCrew] Failed to parse result: {e}")
            return {
                "test_file": None,
                "test_count": 0,
                "stories_covered": [],
                "error": str(e),
                "raw_output": str(result)
            }
