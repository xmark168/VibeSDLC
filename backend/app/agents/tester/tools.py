"""Tester specific tools for reading stories and generating integration test files."""

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from app.models import Story, StoryStatus
from app.core.db import engine
from pathlib import Path
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class QueryStoriesInput(BaseModel):
    """Input for QueryStoriesFromDBTool"""
    project_id: str = Field(..., description="Project UUID as string")
    story_ids: list[str] = Field(
        default=[],
        description="Optional list of story UUIDs to filter. Empty = get all REVIEW stories"
    )


class QueryStoriesFromDBTool(BaseTool):
    """Query user stories from database by project_id, filtered by REVIEW status"""
    
    name: str = "query_stories_from_db"
    description: str = (
        "Query user stories from the project database that are in REVIEW status. "
        "Returns list of stories with id, title, description, acceptance_criteria, story_points, status. "
        "Use this to read actual user stories created by Business Analyst that are ready for integration testing."
    )
    args_schema: type[BaseModel] = QueryStoriesInput
    
    def _run(self, project_id: str, story_ids: list[str] = None):
        """Query stories from database with REVIEW status"""
        try:
            with Session(engine) as session:
                # Query stories with REVIEW status
                query = select(Story).where(
                    Story.project_id == UUID(project_id),
                    Story.status == StoryStatus.REVIEW
                )
                
                # Optional filter by specific story IDs
                if story_ids:
                    query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
                
                stories = session.exec(query).all()
                
                result = [
                    {
                        "id": str(story.id),
                        "title": story.title,
                        "description": story.description,
                        "acceptance_criteria": story.acceptance_criteria,
                        "story_points": story.story_point,
                        "status": story.status.value,
                        "priority": story.priority
                    }
                    for story in stories
                ]
                
                logger.info(f"[QueryStoriesTool] Retrieved {len(result)} stories with REVIEW status")
                return result
                
        except Exception as e:
            logger.error(f"[QueryStoriesTool] Error: {e}", exc_info=True)
            return []


class GenerateTestFileInput(BaseModel):
    """Input for GenerateTestFileTool"""
    project_path: str = Field(..., description="Absolute path to project directory")
    filename: str = Field(..., description="Test filename (e.g., 'review-batch-2025-11-26.integration.test.ts')")
    test_content: str = Field(..., description="Full test file content in TypeScript")


class GenerateTestFileTool(BaseTool):
    """Generate integration test file in project tests/integration directory"""
    
    name: str = "generate_test_file"
    description: str = (
        "Generate an integration test file in the project's tests/integration/ directory. "
        "Creates the tests/integration directory if it doesn't exist. "
        "Use this to save generated integration test code for Next.js API + Prisma DB testing."
    )
    args_schema: type[BaseModel] = GenerateTestFileInput
    
    def _run(self, project_path: str, filename: str, test_content: str):
        """Generate integration test file"""
        try:
            # Create tests/integration directory
            tests_dir = Path(project_path) / "tests" / "integration"
            tests_dir.mkdir(parents=True, exist_ok=True)
            
            # Write test file
            test_file = tests_dir / filename
            test_file.write_text(test_content, encoding='utf-8')
            
            logger.info(f"[GenerateTestFile] Created: {test_file}")
            return str(test_file)
            
        except Exception as e:
            logger.error(f"[GenerateTestFile] Error: {e}", exc_info=True)
            return f"Error: {str(e)}"


def get_tester_tools() -> list:
    """Get list of tools available to Tester.

    Returns:
        List of CrewAI Tool instances for integration test generation
    """
    return [
        QueryStoriesFromDBTool(),
        GenerateTestFileTool()
    ]
