"""Plan Tests node - Analyze stories and create test plan (aligned with Developer V2).

Uses FileRepository for zero-shot planning (Developer V2 pattern):
- Pre-computes workspace context (file tree, components, API routes)
- Single LLM call with full context
- No tool calls needed for planning
"""

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
from app.agents.tester.src.core_nodes import detect_testing_context, send_message, generate_user_message
from app.agents.tester.src._llm import plan_llm
from app.agents.tester.src.config import MAX_SCENARIOS_UNIT, MAX_SCENARIOS_INTEGRATION
from app.agents.tester.src.utils.file_repository import FileRepository
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


def _extract_feature_name(story_title: str) -> str:
    """Extract feature name from story title for test file naming.
    
    Examples:
    - "As a user, I want to see featured books" -> "featured-books"
    - "Homepage with categories and search" -> "homepage"
    - "User can add items to cart" -> "cart"
    
    This creates cleaner, feature-based test file names instead of long slugs.
    """
    title_lower = story_title.lower()
    
    # Common feature keywords to extract (priority order)
    feature_keywords = [
        # E-commerce
        "cart", "checkout", "payment", "order", "product", "catalog",
        # Content
        "book", "category", "categories", "search", "featured", "bestseller",
        "new-arrival", "recommendation",
        # User
        "auth", "login", "register", "profile", "account", "user",
        # Navigation
        "homepage", "home", "navigation", "menu", "header", "footer",
        # Other
        "dashboard", "admin", "settings", "notification",
    ]
    
    # Try to find a matching keyword
    for keyword in feature_keywords:
        if keyword in title_lower:
            # Check for compound keywords
            if keyword == "book" and "featured" in title_lower:
                return "featured-books"
            if keyword == "book" and "bestseller" in title_lower:
                return "bestsellers"
            if keyword == "book" and "new" in title_lower:
                return "new-arrivals"
            if keyword == "category" or keyword == "categories":
                return "categories"
            return keyword.replace("_", "-")
    
    # Fallback: extract first meaningful noun from title
    # Remove common prefixes like "As a user, I want to..."
    cleaned = re.sub(r'^(as a \w+,?\s*)?(i want to\s*)?(be able to\s*)?(see|view|browse|display|show)?\s*', '', title_lower)
    
    # Get first few words
    words = re.findall(r'\b[a-z]{3,}\b', cleaned)
    if words:
        # Take first 2 meaningful words
        return '-'.join(words[:2])
    
    # Final fallback
    return _slugify(story_title)[:20] or "feature"


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


def _analyze_component(file_path: str, content: str) -> dict:
    """Extract component info for better test generation.
    
    Analyzes component source to extract:
    - Component name
    - Props interface  
    - Data attributes (data-testid, data-slot, etc.)
    - Whether it has skeleton/loading state
    
    Returns:
        Dict with component analysis info
    """
    info = {
        "name": "",
        "props": [],
        "data_attributes": [],
        "has_skeleton": False,
        "exports": [],
    }
    
    # Extract component name from filename
    filename = file_path.split("/")[-1].replace(".tsx", "").replace(".ts", "")
    info["name"] = filename
    
    # Extract exports (export function X, export const X, export default)
    export_patterns = [
        r'export\s+(?:function|const)\s+(\w+)',
        r'export\s+default\s+(?:function\s+)?(\w+)',
        r'export\s+\{\s*([^}]+)\s*\}',
    ]
    for pattern in export_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if isinstance(match, str):
                for name in match.split(","):
                    name = name.strip()
                    if name and name not in info["exports"]:
                        info["exports"].append(name)
    
    # Extract props from interface/type (simplified)
    # Look for: interface Props { ... } or type Props = { ... }
    props_pattern = r'(?:interface|type)\s+\w*Props\w*\s*(?:=\s*)?\{([^}]+)\}'
    props_match = re.search(props_pattern, content, re.DOTALL)
    if props_match:
        props_content = props_match.group(1)
        # Extract property names
        prop_names = re.findall(r'(\w+)\s*[?:]', props_content)
        info["props"] = list(set(prop_names))[:10]  # Limit to 10 props
    
    # Extract data attributes used in JSX
    data_attrs = re.findall(r'data-(\w+)(?:=|["\'])', content)
    info["data_attributes"] = list(set(data_attrs))
    
    # Check for skeleton/loading patterns
    if "skeleton" in content.lower() or "loading" in content.lower():
        info["has_skeleton"] = True
    
    return info


def _find_components_for_unit_test(workspace_path: str, keywords: list[str]) -> list[dict]:
    """Find components specifically for unit testing with detailed analysis.
    
    Unlike _find_source_files_for_story which finds any matching file,
    this function:
    1. Focuses on component files (.tsx)
    2. Excludes UI primitives (button, input, etc.)
    3. Scores by keyword relevance
    4. Analyzes each component for props, exports, data attributes
    
    Returns:
        List of component info dicts with path, name, props, exports, data_attributes
    """
    from pathlib import Path
    
    path = Path(workspace_path)
    if not path.exists():
        return []
    
    components = []
    
    # Component directories to search (prioritized)
    component_patterns = [
        "src/components/**/*.tsx",
        "components/**/*.tsx",
        "src/app/**/components/**/*.tsx",
    ]
    
    # UI primitives to exclude (these are too generic)
    exclude_dirs = ["ui/", "primitives/", "icons/", "ui\\", "primitives\\", "icons\\"]
    
    for pattern in component_patterns:
        for file_path in path.glob(pattern):
            if "node_modules" not in str(file_path):
                relative_path = str(file_path.relative_to(path)).replace("\\", "/")
                
                # Skip UI primitives
                if any(ex in relative_path for ex in exclude_dirs):
                    continue
                
                # Skip test files
                if ".test." in relative_path or "__tests__" in relative_path:
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    content_lower = content.lower()
                    filename_lower = relative_path.lower()
                    
                    # Score by keyword relevance
                    score = 0
                    for keyword in keywords:
                        if keyword in content_lower:
                            score += 1
                        if keyword in filename_lower:
                            score += 2  # Filename match is more relevant
                    
                    if score > 0:
                        # Analyze component
                        component_info = _analyze_component(relative_path, content)
                        component_info["path"] = relative_path
                        component_info["score"] = score
                        components.append(component_info)
                        
                except Exception as e:
                    logger.warning(f"[_find_components_for_unit_test] Failed to read {file_path}: {e}")
    
    # Sort by score (highest first) and limit
    components.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    logger.info(f"[_find_components_for_unit_test] Found {len(components)} relevant components")
    return components[:10]  # Return top 10 most relevant


def _format_component_context(components: list[dict]) -> str:
    """Format component info for LLM context.
    
    Creates a structured summary of available components for unit testing.
    """
    if not components:
        return "No specific components found for unit testing."
    
    lines = ["## Available Components for Unit Testing:\n"]
    
    for comp in components:
        lines.append(f"### {comp.get('name', 'Unknown')}")
        lines.append(f"- **Path**: `{comp.get('path', '')}`")
        
        if comp.get("exports"):
            lines.append(f"- **Exports**: {', '.join(comp['exports'][:5])}")
        
        if comp.get("props"):
            lines.append(f"- **Props**: {', '.join(comp['props'][:8])}")
        
        if comp.get("data_attributes"):
            attrs = [f"data-{a}" for a in comp["data_attributes"][:5]]
            lines.append(f"- **Data Attributes**: {', '.join(attrs)}")
        
        if comp.get("has_skeleton"):
            lines.append("- **Has Loading/Skeleton**: Yes")
        
        lines.append("")
    
    lines.append("⚠️ ONLY use props and attributes listed above!")
    
    return "\n".join(lines)


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
    
    # ==========================================================================
    # ZERO-SHOT PLANNING with FileRepository (Developer V2 pattern)
    # ==========================================================================
    # Build FileRepository ONCE - pre-computes all context instantly (no LLM calls)
    file_repo = FileRepository(workspace_path) if workspace_path else None
    
    if file_repo:
        logger.info(f"[plan_tests] FileRepository: {len(file_repo.file_tree)} files, "
                   f"{len(file_repo.components)} components, {len(file_repo.api_routes)} routes")
    
    # Get existing API routes from FileRepository
    existing_routes = file_repo.api_routes if file_repo else []
    existing_routes_text = "\n".join(f"- {r}" for r in existing_routes) if existing_routes else "No API routes found."
    
    # Load API source code from FileRepository
    api_source_code = file_repo.get_api_source_code() if file_repo else ""
    if api_source_code:
        logger.info(f"[plan_tests] Loaded {len(api_source_code)} chars of API source code")
    
    # Find components for unit tests using FileRepository
    keywords = _extract_keywords_from_stories(stories) if stories else []
    logger.info(f"[plan_tests] Extracted keywords: {keywords}")
    
    if file_repo:
        unit_test_components = file_repo.get_components_for_keywords(keywords)
        component_context = file_repo.format_component_context(unit_test_components)
    else:
        unit_test_components = _find_components_for_unit_test(workspace_path, keywords)
        component_context = _format_component_context(unit_test_components)
    
    logger.info(f"[plan_tests] Analyzed {len(unit_test_components)} components for unit tests")
    
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
                    component_context=component_context,
                )),
            ],
            config=_cfg(state, "plan_tests"),
        )
        
        result = _parse_json(response.content)
        test_plan = result.get("test_plan", [])
        
        # FIXED folder paths - always use standard structure
        integration_folder = "src/__tests__/integration"
        unit_folder = "src/__tests__/unit"
        
        # Validate and CONSOLIDATE steps - enforce MAX 2 files per story (1 IT + 1 UT)
        # Group steps by story_id and test type, then merge
        from collections import defaultdict
        
        steps_by_story_type = defaultdict(list)
        
        for step in test_plan:
            story_id = step.get("story_id", "default")
            test_type = step.get("type", "integration")
            key = (story_id, test_type)
            steps_by_story_type[key].append(step)
        
        validated_plan = []
        
        for (story_id, test_type), steps in steps_by_story_type.items():
            # Take first step as base, merge scenarios from others
            base_step = steps[0].copy()
            
            # Merge scenarios from all steps of same type
            all_scenarios = []
            all_dependencies = []
            descriptions = []
            
            for s in steps:
                scenarios = s.get("scenarios", [])
                if isinstance(scenarios, list):
                    all_scenarios.extend(scenarios)
                deps = s.get("dependencies", [])
                if isinstance(deps, list):
                    all_dependencies.extend(deps)
                desc = s.get("description", "")
                if desc:
                    descriptions.append(desc)
            
            # Deduplicate - limit scenarios by test type (from config)
            # Integration: MAX_SCENARIOS_INTEGRATION (branch coverage)
            # Unit: MAX_SCENARIOS_UNIT (render correctness)
            max_scenarios = MAX_SCENARIOS_UNIT if test_type == "unit" else MAX_SCENARIOS_INTEGRATION
            all_scenarios = list(dict.fromkeys(all_scenarios))[:max_scenarios]
            all_dependencies = list(dict.fromkeys(all_dependencies))
            
            story_title = base_step.get("story_title", "unknown")
            feature_name = _extract_feature_name(story_title)
            
            # Skip invalid steps (config/setup related)
            if not _is_valid_story_for_testing({"title": story_title}):
                logger.warning(f"[plan_tests] Skipping invalid step: {story_title}")
                continue
            
            # Set consolidated values
            base_step["scenarios"] = all_scenarios
            base_step["dependencies"] = all_dependencies
            base_step["description"] = descriptions[0] if descriptions else f"Test {test_type} for {story_title}"
            
            # Set file path - feature-based naming (e.g., "featured-books.test.ts")
            if test_type == "unit":
                base_step["file_path"] = f"{unit_folder}/{feature_name}.test.tsx"
                base_step["skills"] = ["unit-test"]
            else:
                base_step["file_path"] = f"{integration_folder}/{feature_name}.test.ts"
                base_step["skills"] = ["integration-test"]
            
            logger.info(f"[plan_tests] Feature name: '{feature_name}' from story: '{story_title[:40]}...'")
            
            validated_plan.append(base_step)
            
            if len(steps) > 1:
                logger.info(f"[plan_tests] Consolidated {len(steps)} {test_type} steps into 1 file for story: {story_title[:30]}")
        
        # Use validated plan
        test_plan = validated_plan
        
        # MANDATORY COVERAGE: Ensure both integration AND unit tests exist
        has_integration = any(s["type"] == "integration" for s in test_plan)
        has_unit = any(s["type"] == "unit" for s in test_plan)
        
        # Get story info for auto-generating missing test type
        if test_plan and (not has_integration or not has_unit):
            first_story = stories[0] if stories else {}
            story_title = first_story.get("title", "Unknown Story")
            feature_name = _extract_feature_name(story_title)
            
            if not has_integration:
                # Add integration test with branch coverage scenarios
                logger.info(f"[plan_tests] Auto-adding integration test for coverage")
                test_plan.append({
                    "type": "integration",
                    "story_id": first_story.get("id", ""),
                    "story_title": story_title,
                    "file_path": f"{integration_folder}/{feature_name}.test.ts",
                    "description": f"Test API with branch coverage: {story_title[:40]}",
                    "scenarios": [
                        "returns data on success (happy path)",
                        "returns empty array when no data (empty case)",
                        "handles error gracefully (error case)"
                    ],
                    "skills": ["integration-test"],
                    "dependencies": [],
                })
            
            if not has_unit:
                # Add unit test - focus on render correctness (not branch coverage)
                logger.info(f"[plan_tests] Auto-adding unit test for coverage")
                test_plan.append({
                    "type": "unit",
                    "story_id": first_story.get("id", ""),
                    "story_title": story_title,
                    "file_path": f"{unit_folder}/{feature_name}.test.tsx",
                    "description": f"Test component renders correctly: {story_title[:40]}",
                    "scenarios": [
                        "renders correctly with valid props",
                        "handles user interaction"
                    ],
                    "skills": ["unit-test"],
                    "dependencies": [],
                })
        
        # Re-number steps after filtering and adding
        for i, step in enumerate(test_plan):
            step["order"] = i + 1
        
        total_steps = len(test_plan)
        
        # Pre-load dependencies using FileRepository (Developer V2 pattern)
        if file_repo:
            dependencies_content = file_repo.preload_dependencies(test_plan, stories)
        else:
            workspace_path = state.get("workspace_path", "") or project_path
            dependencies_content = _preload_test_dependencies(workspace_path, test_plan, stories)
        logger.info(f"[plan_tests] Pre-loaded {len(dependencies_content)} dependency files")
        
        # component_context already created before LLM call (used for scenario planning)
        
        # Build message (persona-driven intro + technical details)
        intro = await generate_user_message(
            "plan_created",
            f"{total_steps} test steps planned",
            agent,
            f"{len([s for s in test_plan if s['type']=='unit'])} unit, {len([s for s in test_plan if s['type']=='integration'])} integration"
        )
        msg = f"{intro}\n"
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
            "component_context": component_context,
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
        error_msg = await generate_user_message(
            "default",
            f"Error creating test plan: {str(e)[:100]}",
            agent
        )
        await send_message(state, agent, error_msg, "error")
        return {
            "test_plan": [],
            "testing_context": testing_context,
            "total_steps": 0,
            "current_step": 0,
            "error": str(e),
            "message": error_msg,
        }
