"""Tester Tools - LangChain tools for test context."""

import logging
import re
from pathlib import Path
from uuid import UUID

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _get_project_path(project_id: str) -> Path | None:
    """Get project path from database."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Project
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            return Path(project.project_path)
    return None


@tool
def get_test_files(project_id: str) -> str:
    """List all test files in the project.
    
    Call this when:
    - Need to see what test files exist
    - User asks about test structure
    - Before analyzing test coverage
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of test files with paths
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        test_patterns = ["**/*.test.ts", "**/*.test.js", "**/*.spec.ts", "**/*.spec.js", "**/test_*.py", "**/*_test.py"]
        test_files = []
        
        for pattern in test_patterns:
            test_files.extend(project_path.glob(pattern))
        
        # Filter out node_modules
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        
        if not test_files:
            return "No test files found in project."
        
        lines = [f"Found {len(test_files)} test files:"]
        for f in sorted(test_files)[:20]:
            rel_path = f.relative_to(project_path)
            lines.append(f"- {rel_path}")
        
        if len(test_files) > 20:
            lines.append(f"... and {len(test_files) - 20} more")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.warning(f"[get_test_files] Error: {e}")
        return f"Error listing test files: {str(e)}"


@tool
def read_test_file(project_id: str, file_path: str) -> str:
    """Read content of a specific test file.
    
    Call this when:
    - Need to see test implementation details
    - User asks about specific tests
    - Analyzing test quality
    
    Args:
        project_id: The project UUID
        file_path: Relative path to test file
        
    Returns:
        Content of the test file (truncated if too long)
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        full_path = project_path / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"
        
        content = full_path.read_text(encoding='utf-8')
        
        # Truncate if too long
        if len(content) > 3000:
            content = content[:3000] + "\n\n... (truncated)"
        
        return f"File: {file_path}\n\n{content}"
        
    except Exception as e:
        logger.warning(f"[read_test_file] Error: {e}")
        return f"Error reading file: {str(e)}"


@tool
def get_test_summary(project_id: str) -> str:
    """Get summary of tests: count by type, recent tests.
    
    Call this when:
    - User asks about test coverage or status
    - Need overview of testing state
    - Reporting on test progress
    
    Args:
        project_id: The project UUID
        
    Returns:
        Test summary with counts and types
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        # Count test files by type
        integration_tests = list(project_path.glob("**/integration*.test.*"))
        unit_tests = list(project_path.glob("**/*.test.*"))
        unit_tests = [f for f in unit_tests if f not in integration_tests]
        
        # Filter out node_modules
        integration_tests = [f for f in integration_tests if "node_modules" not in str(f)]
        unit_tests = [f for f in unit_tests if "node_modules" not in str(f)]
        
        # Count test cases in integration tests
        total_test_cases = 0
        for test_file in integration_tests:
            try:
                content = test_file.read_text(encoding='utf-8')
                # Count test('...') or it('...')
                test_cases = len(re.findall(r"(?:test|it)\s*\(['\"]", content))
                total_test_cases += test_cases
            except:
                pass
        
        lines = [
            "Test Summary:",
            f"- Integration test files: {len(integration_tests)}",
            f"- Unit test files: {len(unit_tests)}",
            f"- Total test cases (integration): {total_test_cases}",
        ]
        
        # Recent test files
        all_tests = integration_tests + unit_tests
        if all_tests:
            recent = sorted(all_tests, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            lines.append("\nRecent test files:")
            for f in recent:
                rel = f.relative_to(project_path)
                lines.append(f"- {rel}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.warning(f"[get_test_summary] Error: {e}")
        return f"Error getting test summary: {str(e)}"


@tool
def search_tests(project_id: str, query: str) -> str:
    """Search for tests by name or content.
    
    Call this when:
    - User asks about specific tests (e.g., "tests for login")
    - Need to find tests related to a feature
    - Looking for test patterns
    
    Args:
        project_id: The project UUID
        query: Search term (test name, feature, etc.)
        
    Returns:
        Matching tests with file and line info
    """
    try:
        project_path = _get_project_path(project_id)
        if not project_path:
            return "Project path not configured."
        
        test_files = list(project_path.glob("**/*.test.*")) + list(project_path.glob("**/*.spec.*"))
        test_files = [f for f in test_files if "node_modules" not in str(f)]
        
        matches = []
        query_lower = query.lower()
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Check if it's a test definition
                        if re.search(r"(?:test|it|describe)\s*\(['\"]", line):
                            rel_path = test_file.relative_to(project_path)
                            matches.append(f"- {rel_path}:{i+1}: {line.strip()[:80]}")
            except:
                pass
        
        if not matches:
            return f"No tests found matching '{query}'"
        
        result = [f"Tests matching '{query}':"]
        result.extend(matches[:15])
        
        if len(matches) > 15:
            result.append(f"... and {len(matches) - 15} more matches")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.warning(f"[search_tests] Error: {e}")
        return f"Error searching tests: {str(e)}"


@tool
def get_stories_in_review(project_id: str) -> str:
    """Get stories currently in REVIEW status that need testing.
    
    Call this when:
    - Need to see what stories need tests
    - User asks about pending test work
    - Before generating tests
    
    Args:
        project_id: The project UUID
        
    Returns:
        List of stories in REVIEW with details
    """
    try:
        from sqlmodel import Session, select
        from app.core.db import engine
        from app.models import Story, StoryStatus
        
        with Session(engine) as session:
            stories = session.exec(
                select(Story)
                .where(Story.project_id == UUID(project_id))
                .where(Story.status == StoryStatus.REVIEW)
                .order_by(Story.updated_at.desc())
            ).all()
            
            if not stories:
                return "No stories in REVIEW status."
            
            lines = [f"Stories in REVIEW ({len(stories)}):"]
            for s in stories:
                lines.append(f"- {s.title}")
                if s.acceptance_criteria:
                    lines.append(f"  Criteria: {s.acceptance_criteria[:100]}...")
            
            return "\n".join(lines)
            
    except Exception as e:
        logger.warning(f"[get_stories_in_review] Error: {e}")
        return f"Error fetching stories: {str(e)}"


# Tool registry
TESTER_TOOLS = [
    get_test_files,
    read_test_file,
    get_test_summary,
    search_tests,
    get_stories_in_review,
]


def get_tester_tools():
    """Get list of tools available to Tester."""
    return TESTER_TOOLS
