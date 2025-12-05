"""Plan Tests node - Analyze stories and create test plan."""

import json
import logging
import os
import re
import unicodedata
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.core_nodes import detect_testing_context, send_message
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)

# Use custom API endpoint if configured
_api_key = os.getenv("TESTER_API_KEY") or os.getenv("OPENAI_API_KEY")
_base_url = os.getenv("TESTER_BASE_URL") or os.getenv("OPENAI_BASE_URL")
_model = os.getenv("TESTER_MODEL", "gpt-4.1")

_llm = ChatOpenAI(
    model=_model,
    temperature=0,
    api_key=_api_key,
    base_url=_base_url,
) if _base_url else ChatOpenAI(model=_model, temperature=0)


def _cfg(state: dict, name: str) -> dict:
    """Get LLM config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else {}


def _parse_json(content: str) -> dict:
    """Parse JSON from LLM response."""
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        pass
    
    # Extract from markdown
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.warning(f"[_parse_json] Failed: {content[:300]}...")
        raise e


def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[-\s]+", "-", text).strip("-")
    return text[:50] if text else "unnamed"


def _extract_keywords_from_stories(stories: list) -> list[str]:
    """Extract keywords from story titles and descriptions for searching source code."""
    keywords = set()
    
    # Common stop words to ignore
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "shall", "can", "need", "dare", "ought",
        "used", "i", "you", "he", "she", "it", "we", "they", "what", "which",
        "who", "whom", "this", "that", "these", "those", "am", "user", "users",
        "feature", "story", "test", "tests", "testing", "should", "when", "then",
        "given", "want", "so", "that", "able", "view", "see", "display", "show",
    }
    
    for story in stories:
        title = story.get("title", "") or ""
        description = story.get("description", "") or ""
        text = f"{title} {description}".lower()
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-z][a-z0-9]*\b', text)
        
        for word in words:
            if len(word) >= 3 and word not in stop_words:
                keywords.add(word)
    
    return list(keywords)[:15]  # Limit to top 15 keywords


def _find_source_files_for_story(workspace_path: str, keywords: list[str]) -> list[str]:
    """Find source files related to story keywords using glob and grep."""
    from pathlib import Path
    import subprocess
    
    found_files = set()
    path = Path(workspace_path)
    
    if not path.exists():
        return []
    
    # 1. Search in common source directories
    source_patterns = [
        "src/app/api/**/*.ts",
        "src/app/api/**/*.tsx", 
        "src/components/**/*.tsx",
        "src/components/**/*.ts",
        "src/lib/**/*.ts",
        "src/services/**/*.ts",
        "src/hooks/**/*.ts",
        "src/utils/**/*.ts",
        "app/api/**/*.ts",
        "pages/api/**/*.ts",
    ]
    
    for pattern in source_patterns:
        for file_path in path.glob(pattern):
            if "node_modules" not in str(file_path):
                # Check if file contains any keyword
                try:
                    content = file_path.read_text(encoding="utf-8").lower()
                    for keyword in keywords:
                        if keyword in content or keyword in str(file_path).lower():
                            found_files.add(str(file_path.relative_to(path)))
                            break
                except Exception:
                    pass
    
    # 2. Also find API route files by common naming patterns
    api_keywords = ["product", "cart", "order", "user", "auth", "category", "item", "checkout", "payment"]
    for keyword in keywords:
        if keyword in api_keywords or any(k in keyword for k in api_keywords):
            # Look for route files with this name
            for route_file in path.glob(f"**/api/**/{keyword}*/**/route.ts"):
                if "node_modules" not in str(route_file):
                    found_files.add(str(route_file.relative_to(path)))
            for route_file in path.glob(f"**/api/**/{keyword}*/route.ts"):
                if "node_modules" not in str(route_file):
                    found_files.add(str(route_file.relative_to(path)))
    
    return list(found_files)[:20]  # Limit to 20 files


def _preload_test_dependencies(workspace_path: str, test_plan: list, stories: list = None) -> dict:
    """Pre-load source files that tests will need as context (MetaGPT-style).
    
    This function:
    1. Extracts keywords from stories
    2. Finds actual source files related to those keywords
    3. Reads their content so LLM knows actual exports, types, functions
    
    Returns:
        Dict mapping file_path -> content
    """
    from pathlib import Path
    
    dependencies_content = {}
    
    if not workspace_path or not Path(workspace_path).exists():
        return dependencies_content
    
    # 1. Find source files related to stories
    if stories:
        keywords = _extract_keywords_from_stories(stories)
        logger.info(f"[plan_tests] Extracted keywords: {keywords}")
        
        related_files = _find_source_files_for_story(workspace_path, keywords)
        logger.info(f"[plan_tests] Found {len(related_files)} related source files")
        
        for file_path in related_files:
            full_path = Path(workspace_path) / file_path
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8")
                    # Keep more content for source files (important for LLM to understand)
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    dependencies_content[file_path] = content
                    logger.info(f"[plan_tests] Pre-loaded source: {file_path}")
                except Exception as e:
                    logger.warning(f"[plan_tests] Failed to pre-load {file_path}: {e}")
    
    # 2. Collect source files mentioned in test plan
    source_files = set()
    for step in test_plan:
        deps = step.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str) and dep:
                    source_files.add(dep)
        
        # Also extract from description (look for file paths)
        description = step.get("description", "")
        file_patterns = re.findall(r'src/[^\s,\)]+\.(ts|tsx|js|jsx)', description)
        for match in file_patterns:
            if isinstance(match, tuple):
                continue
            source_files.add(match)
    
    # 3. Always include common test setup files
    common_files = [
        "jest.config.ts",
        "jest.setup.ts",
        "src/lib/prisma.ts",
        "prisma/schema.prisma",
    ]
    source_files.update(common_files)
    
    # Pre-load each file
    for file_path in source_files:
        if file_path in dependencies_content:
            continue  # Already loaded
        full_path = Path(workspace_path) / file_path
        if full_path.exists() and full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8")
                if len(content) > 3000:
                    content = content[:3000] + "\n... (truncated)"
                dependencies_content[file_path] = content
                logger.info(f"[plan_tests] Pre-loaded: {file_path}")
            except Exception as e:
                logger.warning(f"[plan_tests] Failed to pre-load {file_path}: {e}")
    
    return dependencies_content


def _detect_test_structure(project_path: str) -> dict:
    """Detect existing test folder structure in the project.
    
    Strategy for integration tests:
    1. First priority: Find existing "integration" folder
    2. Second: Check for common test FOLDERS  
    3. Fallback: Create in __tests__/integration/
    
    Note: Don't use folders like "lib/", "utils/" for story tests - those are for unit tests.
    
    Returns:
        dict with:
        - integration_folder: Path for integration tests
        - e2e_folder: Path for e2e tests
        - existing_tests: List of existing test files
        - existing_specs: List of existing spec files
    """
    from pathlib import Path
    
    structure = {
        "integration_folder": "__tests__/integration",  # default
        "e2e_folder": "e2e",  # default
        "existing_tests": [],
        "existing_specs": [],
    }
    
    path = Path(project_path)
    if not path.exists():
        return structure
    
    # Exclude patterns for file searching
    exclude_patterns = [
        "node_modules", 
        ".worktrees", 
        "boilerplate", 
        "templates",
    ]
    
    # For integration tests: Prioritize folders with "integration" in name
    # Don't use lib/, utils/, etc. - those are for unit tests
    integration_candidates = [
        "src/__tests__/integration",  # Next.js common pattern
        "__tests__/integration",
        "tests/integration",
        "test/integration",
        "__tests__",
        "tests",
    ]
    
    for folder in integration_candidates:
        if (path / folder).is_dir():
            structure["integration_folder"] = folder
            logger.info(f"[_detect_test_structure] Found integration folder: {folder}")
            break
    
    # If no folder exists, create __tests__/integration as default
    if not (path / structure["integration_folder"]).exists():
        structure["integration_folder"] = "__tests__/integration"
        logger.info(f"[_detect_test_structure] Will use default integration folder: {structure['integration_folder']}")
    
    # Collect existing test files for reference (but don't use their folder)
    test_files = list(path.glob("**/*.test.ts")) + list(path.glob("**/*.test.js"))
    test_files = [f for f in test_files if not any(p in str(f) for p in exclude_patterns)]
    test_files = [f for f in test_files if len(f.relative_to(path).parts) <= 4]
    if test_files:
        structure["existing_tests"] = [str(f.relative_to(path)) for f in test_files[:5]]
    
    # E2E detection - similar logic (reuse exclude_patterns)
    spec_files = list(path.glob("**/*.spec.ts")) + list(path.glob("**/*.spec.js"))
    spec_files = [f for f in spec_files if not any(p in str(f) for p in exclude_patterns)]
    # Also exclude deeply nested paths
    spec_files = [f for f in spec_files if len(f.relative_to(path).parts) <= 4]
    
    if spec_files:
        spec_files.sort(key=lambda f: len(f.parts))
        first_spec = spec_files[0].relative_to(path)
        structure["e2e_folder"] = str(first_spec.parent)
        structure["existing_specs"] = [str(f.relative_to(path)) for f in spec_files[:5]]
        logger.info(f"[_detect_test_structure] Found e2e folder from files: {structure['e2e_folder']}")
    else:
        # Fallback: Check for e2e folders
        e2e_candidates = [
            "src/__tests__/e2e",
            "__tests__/e2e",
            "e2e",
            "tests/e2e",
            "playwright",
        ]
        for folder in e2e_candidates:
            if (path / folder).is_dir():
                structure["e2e_folder"] = folder
                logger.info(f"[_detect_test_structure] Found e2e folder from dir: {folder}")
                break
    
    return structure


async def plan_tests(state: TesterState, agent=None) -> dict:
    """Analyze stories and create test plan.
    
    This node:
    1. Detects testing context (auth, ORM, mocks, ESM warnings)
    2. Analyzes stories to identify testable scenarios
    3. Decides test type (integration vs e2e) for each
    4. Creates a step-by-step test plan
    
    Output:
    - test_plan: List of test steps
    - testing_context: Auth patterns, ORM, existing mocks
    - total_steps: Number of steps
    - current_step: 0 (starting)
    """
    print("[NODE] plan_tests")
    
    stories = state.get("stories", [])
    project_id = state.get("project_id", "")
    
    # Get project path and detect testing context
    project_path = None
    testing_context = {}
    test_structure = {}
    
    with Session(engine) as session:
        project = session.get(Project, UUID(project_id))
        if project and project.project_path:
            project_path = project.project_path
            # Detect testing context (auth, ORM, mocks, ESM warnings)
            testing_context = detect_testing_context(project_path)
            # Detect test folder structure
            test_structure = _detect_test_structure(project_path)
            logger.info(f"[plan_tests] Testing context: auth={testing_context.get('auth_library')}, orm={testing_context.get('orm')}")
            logger.info(f"[plan_tests] Test structure: integration={test_structure.get('integration_folder')}, e2e={test_structure.get('e2e_folder')}")
    
    # These are no longer pre-populated, but kept for compatibility
    related_code = state.get("related_code", {})
    project_context = state.get("project_context", "")
    
    if not stories:
        logger.info("[plan_tests] No stories to plan")
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "message": "Không có stories để tạo test plan.",
        }
    
    # Format stories for prompt
    stories_text = json.dumps(stories, indent=2, ensure_ascii=False)
    
    # Format related code
    related_code_text = ""
    if related_code:
        for story_id, code in related_code.items():
            story = next((s for s in stories if s.get("id") == story_id), None)
            if story:
                related_code_text += f"\n### Code for '{story.get('title', 'Unknown')}':\n{code}\n"
    else:
        related_code_text = "No related code found."
    
    try:
        # Call LLM to create test plan
        response = await _llm.ainvoke(
            [
                SystemMessage(content=get_system_prompt("plan_tests")),
                HumanMessage(content=get_user_prompt(
                    "plan_tests",
                    stories=stories_text,
                    related_code=related_code_text[:4000],
                    project_context=project_context[:2000] if project_context else "N/A",
                    test_structure=json.dumps(test_structure, indent=2),
                )),
            ],
            config=_cfg(state, "plan_tests"),
        )
        
        result = _parse_json(response.content)
        test_plan = result.get("test_plan", [])
        
        # Ensure each step has required fields
        integration_folder = test_structure.get("integration_folder", "__tests__/integration")
        e2e_folder = test_structure.get("e2e_folder", "e2e")
        
        for i, step in enumerate(test_plan):
            step["order"] = step.get("order", i + 1)
            step["type"] = step.get("type", "integration")
            
            # Generate file path if not provided - use detected folders
            if not step.get("file_path"):
                story_title = step.get("story_title", "unknown")
                slug = _slugify(story_title)
                if step["type"] == "e2e":
                    step["file_path"] = f"{e2e_folder}/story-{slug}.spec.ts"
                else:
                    step["file_path"] = f"{integration_folder}/story-{slug}.test.ts"
        
        total_steps = len(test_plan)
        
        # Pre-load dependencies (MetaGPT-style - reduces tool calls in implement)
        # Pass stories so we can find related source files
        workspace_path = state.get("workspace_path", "") or project_path
        dependencies_content = _preload_test_dependencies(workspace_path, test_plan, stories)
        logger.info(f"[plan_tests] Pre-loaded {len(dependencies_content)} dependency files")
        
        # Build message
        msg = f"📋 **Test Plan** ({total_steps} bước)\n"
        for step in test_plan:
            test_type = "🔧 Integration" if step["type"] == "integration" else "🌐 E2E"
            msg += f"\n{step['order']}. {test_type}: {step.get('description', 'N/A')}"
            msg += f"\n   📁 {step.get('file_path', 'N/A')}"
        
        logger.info(f"[plan_tests] Created plan with {total_steps} steps")
        
        # Notify via appropriate channel
        await send_message(state, agent, msg, "progress")
        
        return {
            "test_plan": test_plan,
            "testing_context": testing_context,
            "dependencies_content": dependencies_content,
            "total_steps": total_steps,
            "current_step": 0,
            "review_count": 0,
            "summarize_count": 0,
            "total_lbtm_count": 0,
            "message": msg,
            "action": "IMPLEMENT" if total_steps > 0 else "RESPOND",
        }
        
    except Exception as e:
        logger.error(f"[plan_tests] Error: {e}", exc_info=True)
        error_msg = f"Lỗi khi tạo test plan: {str(e)}"
        await send_message(state, agent, error_msg, "error")
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "error": str(e),
            "message": error_msg,
        }
