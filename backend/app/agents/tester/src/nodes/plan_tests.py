"""Plan Tests node - Analyze stories and create test plan."""

import json
import logging
import os
import re
import unicodedata
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlmodel import Session

from app.agents.tester.src.state import TesterState
from app.agents.tester.src.prompts import get_system_prompt, get_user_prompt
from app.agents.tester.src.core_nodes import detect_testing_context, send_message
from app.agents.tester.src._llm import plan_llm
from app.core.db import engine
from app.models import Project

logger = logging.getLogger(__name__)

_llm = plan_llm


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


# =============================================================================
# VALIDATION
# =============================================================================

# Invalid patterns that should not be used as story titles/test names
INVALID_STORY_PATTERNS = [
    "jest-config",
    "config-removal", 
    "config-cleanup",
    "unnamed",
    "unknown",
    "untitled",
    "test-file",
    "example-test",
    "sample-test",
]


def _is_valid_story_for_testing(story: dict) -> bool:
    """Check if a story is valid for test generation.
    
    Rejects stories that:
    - Have invalid/placeholder titles
    - Are about config/setup tasks (not user features)
    - Have empty or missing required fields
    """
    title = story.get("title", "") or ""
    slug = _slugify(title)
    
    # Check for invalid patterns
    for pattern in INVALID_STORY_PATTERNS:
        if pattern in slug:
            logger.warning(f"[_is_valid_story_for_testing] Rejected story with invalid pattern '{pattern}': {title}")
            return False
    
    # Must have meaningful title (at least 5 chars after slugify)
    if len(slug) < 5:
        logger.warning(f"[_is_valid_story_for_testing] Rejected story with short title: {title}")
        return False
    
    # Check for config/setup related titles (not user features)
    config_keywords = ["config", "setup", "install", "migrate", "upgrade", "refactor", "cleanup", "remove"]
    title_lower = title.lower()
    if any(kw in title_lower for kw in config_keywords) and "user" not in title_lower:
        logger.warning(f"[_is_valid_story_for_testing] Rejected config/setup story: {title}")
        return False
    
    return True


def _filter_valid_stories(stories: list) -> list:
    """Filter out invalid stories before test planning."""
    valid_stories = [s for s in stories if _is_valid_story_for_testing(s)]
    
    if len(valid_stories) < len(stories):
        rejected_count = len(stories) - len(valid_stories)
        logger.info(f"[_filter_valid_stories] Filtered out {rejected_count} invalid stories")
    
    return valid_stories


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


def _get_existing_routes(workspace_path: str) -> list[str]:
    """Scan project for existing API routes.
    
    This ensures we only generate tests for code that actually exists,
    preventing LLM from hallucinating imports for non-existent routes.
    
    Returns:
        List of existing route paths (e.g., ["app/api/books/featured/route.ts"])
    """
    from pathlib import Path
    
    routes = []
    path = Path(workspace_path)
    
    if not path.exists():
        return routes
    
    # Check common API directories
    api_dirs = [
        path / "src" / "app" / "api",  # Next.js 13+ with src
        path / "app" / "api",           # Next.js 13+ without src
        path / "pages" / "api",         # Next.js pages router
    ]
    
    for api_dir in api_dirs:
        if api_dir.exists():
            for route_file in api_dir.rglob("route.ts"):
                if "node_modules" not in str(route_file):
                    relative = route_file.relative_to(path)
                    routes.append(str(relative).replace("\\", "/"))
            
            # Also check for pages API (older Next.js pattern)
            for api_file in api_dir.rglob("*.ts"):
                if "node_modules" not in str(api_file) and api_file.name != "route.ts":
                    relative = api_file.relative_to(path)
                    routes.append(str(relative).replace("\\", "/"))
    
    logger.info(f"[_get_existing_routes] Found {len(routes)} existing API routes")
    return routes


def _load_api_source_code(workspace_path: str, routes: list[str]) -> str:
    """Load actual API source code for LLM to analyze.
    
    This helps LLM understand WHAT each API actually does:
    - What query params are supported
    - What the response structure looks like
    - What database operations are performed
    
    Returns:
        Formatted string with API source code
    """
    from pathlib import Path
    
    if not workspace_path or not routes:
        return "No API source code available."
    
    path = Path(workspace_path)
    api_sources = []
    
    for route in routes[:10]:  # Limit to 10 routes to avoid token overflow
        route_path = path / route
        if route_path.exists():
            try:
                content = route_path.read_text(encoding="utf-8")
                # Truncate long files
                if len(content) > 2000:
                    content = content[:2000] + "\n// ... (truncated)"
                
                # Extract route URL from path
                # e.g., "src/app/api/categories/route.ts" -> "/api/categories"
                route_url = route.replace("src/app", "").replace("app", "")
                route_url = route_url.replace("/route.ts", "").replace("/route.tsx", "")
                route_url = route_url.replace("\\", "/")
                if not route_url.startswith("/"):
                    route_url = "/" + route_url
                
                api_sources.append(f"### {route_url}\nFile: {route}\n```typescript\n{content}\n```")
            except Exception as e:
                logger.warning(f"[_load_api_source_code] Failed to load {route}: {e}")
    
    if not api_sources:
        return "No API source code available."
    
    return "\n\n".join(api_sources)


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
    """Get standardized test folder structure for Next.js projects.
    
    FIXED STRUCTURE (Best Practice for Next.js):
    - Integration tests: src/__tests__/integration/
    - Unit tests: src/__tests__/unit/
    
    This ensures consistent folder structure across all projects.
    
    Returns:
        dict with:
        - integration_folder: Fixed path for integration tests
        - unit_folder: Fixed path for unit tests
        - existing_tests: List of existing test files (for reference)
    """
    from pathlib import Path
    
    # FIXED STRUCTURE - DO NOT CHANGE based on existing files
    # This ensures consistent test organization
    structure = {
        "integration_folder": "src/__tests__/integration",  # FIXED: Next.js standard
        "unit_folder": "src/__tests__/unit",  # FIXED: Next.js standard
        "existing_tests": [],
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
    
    # Create folders if they don't exist
    integration_path = path / structure["integration_folder"]
    unit_path = path / structure["unit_folder"]
    
    if not integration_path.exists():
        try:
            integration_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[_detect_test_structure] Created integration folder: {structure['integration_folder']}")
        except Exception as e:
            logger.warning(f"[_detect_test_structure] Failed to create integration folder: {e}")
    
    if not unit_path.exists():
        try:
            unit_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"[_detect_test_structure] Created unit folder: {structure['unit_folder']}")
        except Exception as e:
            logger.warning(f"[_detect_test_structure] Failed to create unit folder: {e}")
    
    # Collect existing test files for reference only (not to determine folder)
    test_files = list(path.glob("**/*.test.ts")) + list(path.glob("**/*.test.tsx"))
    test_files = [f for f in test_files if not any(p in str(f) for p in exclude_patterns)]
    test_files = [f for f in test_files if len(f.relative_to(path).parts) <= 5]
    if test_files:
        structure["existing_tests"] = [str(f.relative_to(path)) for f in test_files[:5]]
    
    logger.info(f"[_detect_test_structure] Using fixed structure: integration={structure['integration_folder']}, unit={structure['unit_folder']}")
    
    return structure


async def plan_tests(state: TesterState, agent=None) -> dict:
    """Analyze stories and create test plan.
    
    This node:
    1. Detects testing context (auth, ORM, mocks, ESM warnings)
    2. Analyzes stories to identify testable scenarios
    3. Decides test scenarios for each story
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
            logger.info(f"[plan_tests] Test structure: integration={test_structure.get('integration_folder')}")
    
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
    
    # Filter out invalid stories (config tasks, placeholder titles, etc.)
    valid_stories = _filter_valid_stories(stories)
    
    if not valid_stories:
        logger.info("[plan_tests] No valid stories after filtering")
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "message": "Không có stories hợp lệ để tạo test (các stories về config/setup không được test).",
        }
    
    # Use filtered stories for planning
    stories = valid_stories
    
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
    
    # Get workspace path (worktree or project path)
    workspace_path = state.get("workspace_path") or project_path
    
    # Get existing API routes to constrain test planning
    existing_routes = []
    if workspace_path:
        existing_routes = _get_existing_routes(workspace_path)
    existing_routes_text = "\n".join(f"- {r}" for r in existing_routes) if existing_routes else "No API routes found."
    
    # Load actual API source code for LLM to analyze
    api_source_code = ""
    if workspace_path and existing_routes:
        api_source_code = _load_api_source_code(workspace_path, existing_routes)
        logger.info(f"[plan_tests] Loaded {len(api_source_code)} chars of API source code")
    
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
                    existing_routes=existing_routes_text,
                    api_source_code=api_source_code,
                )),
            ],
            config=_cfg(state, "plan_tests"),
        )
        
        result = _parse_json(response.content)
        test_plan = result.get("test_plan", [])
        
        # FIXED folder paths - always use standard structure
        integration_folder = "src/__tests__/integration"
        unit_folder = "src/__tests__/unit"
        
        # Validate and fix each step
        validated_plan = []
        for i, step in enumerate(test_plan):
            step["order"] = step.get("order", i + 1)
            # Keep LLM's test type decision, default to integration
            step["type"] = step.get("type", "integration")
            
            story_title = step.get("story_title", "unknown")
            slug = _slugify(story_title)
            
            # Skip invalid steps (config/setup related)
            if not _is_valid_story_for_testing({"title": story_title}):
                logger.warning(f"[plan_tests] Skipping invalid step: {story_title}")
                continue
            
            # ALWAYS regenerate file path based on test type
            if step["type"] == "unit":
                step["file_path"] = f"{unit_folder}/story-{slug}.test.tsx"
                step["skills"] = ["unit-test"]
            else:
                step["file_path"] = f"{integration_folder}/story-{slug}.test.ts"
                step["skills"] = ["integration-test"]
            
            # Dependencies will be auto-discovered from source files
            if "dependencies" not in step:
                step["dependencies"] = []
            
            validated_plan.append(step)
        
        # Use validated plan
        test_plan = validated_plan
        
        # Re-number steps after filtering
        for i, step in enumerate(test_plan):
            step["order"] = i + 1
        
        total_steps = len(test_plan)
        
        # Pre-load dependencies (MetaGPT-style - reduces tool calls in implement)
        # Pass stories so we can find related source files
        workspace_path = state.get("workspace_path", "") or project_path
        dependencies_content = _preload_test_dependencies(workspace_path, test_plan, stories)
        logger.info(f"[plan_tests] Pre-loaded {len(dependencies_content)} dependency files")
        
        # Build message
        msg = f"📋 **Test Plan** ({total_steps} bước)\n"
        for step in test_plan:
            test_icon = "🧩 Unit" if step["type"] == "unit" else "🔧 Integration"
            msg += f"\n{step['order']}. {test_icon}: {step.get('description', 'N/A')}"
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
