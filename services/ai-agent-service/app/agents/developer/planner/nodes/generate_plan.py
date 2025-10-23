"""
Generate Plan Node

PHASE 4: Implementation Planning - Create detailed implementation plan
"""

import json
import os

from langchain_core.messages import AIMessage

from ..state import ImplementationPlan, PlannerState


def _detect_task_scope(codebase_analysis) -> dict:
    """
    Detect if task needs backend, frontend, or both based on files to be created/modified.

    Args:
        codebase_analysis: CodebaseAnalysis object with files_to_create and files_to_modify

    Returns:
        Dict with needs_backend, needs_frontend, is_fullstack flags
    """
    backend_patterns = [
        "/models/",
        "/services/",
        "/controllers/",
        "/routes/",
        "/repositories/",
        "/middleware/",
        "/api/",
        "/database/",
        "/config/",
    ]
    frontend_patterns = [
        "/components/",
        "/pages/",
        "/hooks/",
        "/stores/",
        "/src/",
        "/assets/",
        "/styles/",
        "/public/",
        "/views/",
    ]

    needs_backend = False
    needs_frontend = False

    # Combine all files to analyze
    all_files = codebase_analysis.files_to_create + codebase_analysis.files_to_modify

    for file_item in all_files:
        # Handle both dict format (with 'path' key) and string format
        if isinstance(file_item, dict):
            file_path = file_item.get("path", "")
        else:
            file_path = str(file_item)

        file_path_lower = file_path.lower()

        # Check backend patterns
        if any(pattern in file_path_lower for pattern in backend_patterns):
            needs_backend = True

        # Check frontend patterns
        if any(pattern in file_path_lower for pattern in frontend_patterns):
            needs_frontend = True

        # Early exit if both detected
        if needs_backend and needs_frontend:
            break

    return {
        "needs_backend": needs_backend,
        "needs_frontend": needs_frontend,
        "is_fullstack": needs_backend and needs_frontend,
    }


def _load_agents_md_from_path(codebase_path: str, category: str) -> dict | None:
    """
    Load AGENTS.md from a specific category (backend or frontend).

    Args:
        codebase_path: Path to the codebase
        category: "backend" or "frontend"

    Returns:
        Dict with content and metadata, or None if not found
    """
    if not codebase_path or category not in ["backend", "frontend"]:
        return None

    # Possible subdirectory names for each category
    category_dirs = {
        "backend": ["backend", "be", "server", "api"],
        "frontend": ["frontend", "fe", "client", "web", "ui"],
    }

    search_dirs = category_dirs.get(category, [])

    # Try to find AGENTS.md in category-specific directories
    for subdir in search_dirs:
        agents_path = os.path.join(codebase_path, subdir, "AGENTS.md")
        try:
            if os.path.exists(agents_path):
                with open(agents_path, encoding="utf-8") as f:
                    content = f.read()
                    project_type = _detect_project_type(content)
                    stack_category = _detect_stack_category(content)

                    print(f"✅ Loaded {category.upper()} AGENTS.md from: {agents_path}")
                    print(f"   Project Type: {project_type}")

                    return {
                        "content": content,
                        "path": agents_path,
                        "project_type": project_type,
                        "stack_category": stack_category,
                    }
        except Exception as e:
            print(f"⚠️ Error loading {agents_path}: {e}")
            continue

    return None


def _combine_guidelines(
    backend_md: dict | None, frontend_md: dict | None, max_chars: int = 20000
) -> str:
    """
    Combine backend and frontend guidelines intelligently.

    Args:
        backend_md: Backend AGENTS.md dict (with 'content' key)
        frontend_md: Frontend AGENTS.md dict (with 'content' key)
        max_chars: Maximum total characters

    Returns:
        Combined guidelines text
    """
    backend_content = backend_md.get("content", "") if backend_md else ""
    frontend_content = frontend_md.get("content", "") if frontend_md else ""

    # Only backend
    if backend_content and not frontend_content:
        if len(backend_content) > max_chars:
            return backend_content[:max_chars] + "\n\n... (truncated for brevity)"
        return backend_content

    # Only frontend
    if frontend_content and not backend_content:
        if len(frontend_content) > max_chars:
            return frontend_content[:max_chars] + "\n\n... (truncated for brevity)"
        return frontend_content

    # Both exist
    if backend_content and frontend_content:
        total_length = len(backend_content) + len(frontend_content)

        # Both fit completely
        if total_length <= max_chars:
            return f"""## BACKEND ARCHITECTURE GUIDELINES

{backend_content}

## FRONTEND ARCHITECTURE GUIDELINES

{frontend_content}"""

        # Need to truncate - give each 50% of space
        be_limit = max_chars // 2
        fe_limit = max_chars // 2

        return f"""## BACKEND ARCHITECTURE GUIDELINES

{backend_content[:be_limit]}
... (truncated)

## FRONTEND ARCHITECTURE GUIDELINES

{frontend_content[:fe_limit]}
... (truncated)"""

    return ""


def load_architecture_guidelines(
    codebase_path: str = "", task_scope: dict | None = None
) -> dict:
    """
    Load architecture guidelines from AGENTS.md file(s) if available.
    Supports loading separate backend and frontend guidelines for fullstack tasks.

    Args:
        codebase_path: Path to codebase root
        task_scope: Optional dict with needs_backend and needs_frontend flags

    Returns:
        Dict containing architecture guidelines and project info
    """
    guidelines = {
        "has_agents_md": False,
        "architecture_content": "",
        "project_type": "unknown",
        "stack_category": "unknown",
        "backend_guidelines": None,
        "frontend_guidelines": None,
        "is_fullstack": False,
    }

    # Determine what to load
    needs_backend = task_scope.get("needs_backend", True) if task_scope else True
    needs_frontend = task_scope.get("needs_frontend", False) if task_scope else False
    is_fullstack = task_scope.get("is_fullstack", False) if task_scope else False

    guidelines["is_fullstack"] = is_fullstack

    # Try to load category-specific AGENTS.md first
    if needs_backend:
        backend_md = _load_agents_md_from_path(codebase_path, "backend")
        if backend_md:
            guidelines["backend_guidelines"] = backend_md
            guidelines["has_agents_md"] = True

    if needs_frontend:
        frontend_md = _load_agents_md_from_path(codebase_path, "frontend")
        if frontend_md:
            guidelines["frontend_guidelines"] = frontend_md
            guidelines["has_agents_md"] = True

    # Fallback: Try to find single AGENTS.md in root (for monorepo or single-stack projects)
    if not guidelines["has_agents_md"] and codebase_path:
        possible_paths = [os.path.join(codebase_path, "AGENTS.md")]

        # Also search subdirectories
        for root, dirs, files in os.walk(codebase_path):
            if "AGENTS.md" in files:
                possible_paths.append(os.path.join(root, "AGENTS.md"))
                break

        for agents_path in possible_paths:
            try:
                if os.path.exists(agents_path):
                    with open(agents_path, encoding="utf-8") as f:
                        content = f.read()
                        project_type = _detect_project_type(content)
                        stack_category = _detect_stack_category(content)

                        guidelines["has_agents_md"] = True
                        guidelines["project_type"] = project_type
                        guidelines["stack_category"] = stack_category

                        # Store in appropriate category
                        md_dict = {
                            "content": content,
                            "path": agents_path,
                            "project_type": project_type,
                            "stack_category": stack_category,
                        }

                        if stack_category == "backend":
                            guidelines["backend_guidelines"] = md_dict
                        elif stack_category == "frontend":
                            guidelines["frontend_guidelines"] = md_dict
                        else:
                            # Unknown - store in both if fullstack, otherwise in backend
                            if is_fullstack:
                                guidelines["backend_guidelines"] = md_dict
                                guidelines["frontend_guidelines"] = md_dict
                            else:
                                guidelines["backend_guidelines"] = md_dict

                        print(f"✅ Loaded AGENTS.md from: {agents_path}")
                        print(f"   Project Type: {project_type}")
                        print(f"   Stack Category: {stack_category}")
                        break
            except Exception as e:
                print(f"⚠️ Error loading {agents_path}: {e}")
                continue

    # Combine guidelines
    guidelines["architecture_content"] = _combine_guidelines(
        guidelines["backend_guidelines"], guidelines["frontend_guidelines"]
    )

    # Set project type and stack category from loaded guidelines
    if guidelines["backend_guidelines"] and guidelines["frontend_guidelines"]:
        guidelines["project_type"] = "fullstack"
        guidelines["stack_category"] = "fullstack"
    elif guidelines["backend_guidelines"]:
        guidelines["project_type"] = guidelines["backend_guidelines"]["project_type"]
        guidelines["stack_category"] = "backend"
    elif guidelines["frontend_guidelines"]:
        guidelines["project_type"] = guidelines["frontend_guidelines"]["project_type"]
        guidelines["stack_category"] = "frontend"

    # Fallback: Detect project type from package.json if no AGENTS.md found
    if not guidelines["has_agents_md"] and codebase_path:
        detected_type = _detect_project_from_package_json(codebase_path)
        if detected_type:
            guidelines["project_type"] = detected_type["type"]
            guidelines["stack_category"] = detected_type["category"]
            print(f"✅ Detected {detected_type['type']} project from package.json")

    return guidelines


def _detect_project_type(content: str) -> str:
    """Detect specific project type from AGENTS.md content."""
    # Backend frameworks
    if "Express.js" in content and "MongoDB" in content:
        return "express_mongodb"
    elif "Express.js" in content:
        return "express"
    elif "FastAPI" in content:
        return "fastapi"
    elif "Django" in content:
        return "django"

    # Frontend frameworks
    elif "React" in content and "Vite" in content:
        return "react_vite"
    elif "React" in content and "Next.js" in content:
        return "nextjs"
    elif "Vue" in content:
        return "vue"
    elif "Angular" in content:
        return "angular"

    return "unknown"


def _detect_stack_category(content: str) -> str:
    """Detect whether project is backend or frontend."""
    backend_keywords = [
        "Express.js",
        "FastAPI",
        "Django",
        "Flask",
        "MongoDB",
        "PostgreSQL",
        "API",
    ]
    frontend_keywords = [
        "React",
        "Vue",
        "Angular",
        "Vite",
        "Next.js",
        "Component",
        "useState",
    ]

    backend_score = sum(1 for keyword in backend_keywords if keyword in content)
    frontend_score = sum(1 for keyword in frontend_keywords if keyword in content)

    if backend_score > frontend_score:
        return "backend"
    elif frontend_score > backend_score:
        return "frontend"

    return "unknown"


def _detect_project_from_package_json(codebase_path: str) -> dict | None:
    """Detect project type from package.json dependencies."""
    package_json_path = os.path.join(codebase_path, "package.json")
    if not os.path.exists(package_json_path):
        return None

    try:
        with open(package_json_path) as f:
            package_data = json.load(f)
            dependencies = {
                **package_data.get("dependencies", {}),
                **package_data.get("devDependencies", {}),
            }

            # Backend detection
            if "express" in dependencies:
                return {"type": "express", "category": "backend"}

            # Frontend detection
            if "react" in dependencies:
                if "vite" in dependencies:
                    return {"type": "react_vite", "category": "frontend"}
                elif "next" in dependencies:
                    return {"type": "nextjs", "category": "frontend"}
                return {"type": "react", "category": "frontend"}

            if "vue" in dependencies:
                return {"type": "vue", "category": "frontend"}

    except Exception as e:
        print(f"⚠️ Error reading package.json: {e}")

    return None


def detect_project_structure(
    codebase_path: str = "", stack_category: str = "unknown"
) -> dict:
    """
    Detect existing project structure based on stack category.

    Args:
        codebase_path: Path to codebase root
        stack_category: 'backend' or 'frontend'

    Returns:
        Dict with information about existing structure
    """
    structure = {
        "src_structure": "unknown",
        "detected_folders": [],
    }

    if not codebase_path:
        return structure

    # Check if using src/ folder structure
    src_path = os.path.join(codebase_path, "src")
    if os.path.exists(src_path):
        structure["src_structure"] = "src_based"
        base_path = src_path
    else:
        structure["src_structure"] = "root_based"
        base_path = codebase_path

    # Define folders to check based on stack category
    if stack_category == "backend":
        folders_to_check = [
            "models",
            "repositories",
            "services",
            "controllers",
            "routes",
            "middleware",
            "middlewares",
            "tests",
            "utils",
            "config",
        ]
    elif stack_category == "frontend":
        folders_to_check = [
            "components",
            "pages",
            "hooks",
            "services",
            "stores",
            "utils",
            "types",
            "api-request",
            "routes",
            "assets",
        ]
    else:
        # Generic folders
        folders_to_check = ["src", "tests", "utils", "config", "lib", "components"]

    # Check which folders exist
    for folder in folders_to_check:
        folder_path = os.path.join(base_path, folder)
        if os.path.exists(folder_path):
            structure["detected_folders"].append(folder)

    return structure


def _get_architecture_guidelines_text(
    architecture_guidelines: dict, project_structure: dict
) -> str:
    """
    Generate architecture guidelines text for the prompt based on project type.

    Args:
        architecture_guidelines: Guidelines loaded from AGENTS.md
        project_structure: Detected project structure

    Returns:
        Formatted architecture guidelines text
    """
    # If AGENTS.md is available, use it as the primary source
    if architecture_guidelines["has_agents_md"]:
        agents_md_content = architecture_guidelines.get("architecture_content", "")

        # Truncate if too long (keep first 10000 chars to fit in prompt)
        if len(agents_md_content) > 10000:
            agents_md_content = (
                agents_md_content[:10000] + "\n\n... (truncated for brevity)"
            )

        return f"""
**CRITICAL: AGENTS.md ARCHITECTURE GUIDELINES**

The project has an AGENTS.md file with detailed architecture guidelines.
YOU MUST FOLLOW THESE GUIDELINES EXACTLY when generating the implementation plan.

Project Type: {architecture_guidelines["project_type"]}
Stack Category: {architecture_guidelines["stack_category"]}

---
{agents_md_content}
---
"""

    # Fallback: Provide general guidelines based on stack category
    stack_category = architecture_guidelines.get("stack_category", "unknown")

    if stack_category == "backend":
        return _get_backend_fallback_guidelines(
            architecture_guidelines, project_structure
        )
    elif stack_category == "frontend":
        return _get_frontend_fallback_guidelines(
            architecture_guidelines, project_structure
        )
    else:
        return _get_general_fallback_guidelines()


def _get_backend_fallback_guidelines(
    architecture_guidelines: dict, project_structure: dict
) -> str:
    """Fallback guidelines for backend projects without AGENTS.md."""
    return f"""
### BACKEND ARCHITECTURE GUIDELINES

**Project Type**: {architecture_guidelines.get("project_type", "unknown")}
**Detected Folders**: {", ".join(project_structure.get("detected_folders", []))}

**IMPORTANT**: This project does not have an AGENTS.md file. Follow these general backend principles:

1. **Layered Architecture** (if applicable):
   - Models/Entities → Repositories/DAL → Services/Business Logic → Controllers/Handlers → Routes/Endpoints
   - Keep each layer focused on its responsibility
   - Avoid mixing concerns between layers

2. **File Organization**:
   - Group related functionality together
   - Use consistent naming conventions
   - Separate configuration from business logic

3. **Error Handling**:
   - Implement proper error handling at each layer
   - Use custom error classes for business logic errors
   - Return appropriate HTTP status codes

4. **Testing**:
   - Write unit tests for business logic
   - Write integration tests for API endpoints
   - Aim for good test coverage

5. **Code Quality**:
   - Follow existing code patterns in the codebase
   - Add proper documentation and comments
   - Use type hints/annotations where applicable
"""


def _get_frontend_fallback_guidelines(
    architecture_guidelines: dict, project_structure: dict
) -> str:
    """Fallback guidelines for frontend projects without AGENTS.md."""
    return f"""
### FRONTEND ARCHITECTURE GUIDELINES

**Project Type**: {architecture_guidelines.get("project_type", "unknown")}
**Detected Folders**: {", ".join(project_structure.get("detected_folders", []))}

**IMPORTANT**: This project does not have an AGENTS.md file. Follow these general frontend principles:

1. **Component Architecture**:
   - Use functional components with hooks (React/Vue)
   - Keep components small and focused
   - Separate presentational and container components
   - Use TypeScript for type safety

2. **File Organization**:
   - Components in `components/` or `src/components/`
   - Pages/Routes in `pages/` or `src/pages/`
   - Custom hooks in `hooks/` or `src/hooks/`
   - Services/API calls in `services/` or `src/services/`
   - State management in `stores/` or `src/stores/`

3. **State Management**:
   - Use appropriate state management (Context, Redux, Zustand, Pinia, etc.)
   - Keep state close to where it's used
   - Avoid prop drilling

4. **API Integration**:
   - Centralize API calls in service files
   - Use proper error handling
   - Implement loading states
   - Consider using data fetching libraries (React Query, SWR, etc.)

5. **Styling**:
   - Follow existing styling approach (CSS Modules, Tailwind, styled-components, etc.)
   - Keep styles modular and reusable
   - Use consistent naming conventions

6. **Testing**:
   - Write unit tests for components
   - Write integration tests for user flows
   - Use testing libraries appropriate for the framework
"""


def _get_general_fallback_guidelines() -> str:
    """Fallback guidelines for unknown project types."""
    return """
### GENERAL ARCHITECTURE GUIDELINES

**IMPORTANT**: Project type could not be determined and no AGENTS.md file was found.

Follow these general principles:
- Maintain separation of concerns
- Follow existing code patterns in the codebase
- Ensure proper error handling
- Add appropriate tests for new functionality
- Use consistent naming conventions
- Document complex logic
- Keep functions/methods focused and small
"""


def validate_plan_compliance(
    implementation_plan: ImplementationPlan, architecture_guidelines: dict
) -> dict:
    """
    Validate that the generated implementation plan is reasonable and complete.

    Args:
        implementation_plan: Generated implementation plan
        architecture_guidelines: Architecture guidelines from AGENTS.md

    Returns:
        Dict with validation results and suggestions
    """
    validation_result = {
        "is_compliant": True,
        "warnings": [],
        "errors": [],
        "suggestions": [],
    }

    # Basic validation: Check for test coverage
    has_tests = any(
        "test" in step.title.lower() or "test" in step.description.lower()
        for step in implementation_plan.steps
    )
    if not has_tests:
        validation_result["suggestions"].append(
            "Consider adding test implementation steps for better code quality"
        )

    # Check if plan has reasonable number of steps
    if len(implementation_plan.steps) == 0:
        validation_result["errors"].append("Implementation plan has no steps")
        validation_result["is_compliant"] = False
    elif len(implementation_plan.steps) > 20:
        validation_result["warnings"].append(
            f"Implementation plan has {len(implementation_plan.steps)} steps, which might be too many. Consider consolidating."
        )

    # Check if each step has description
    for i, step in enumerate(implementation_plan.steps):
        if not step.description or len(step.description.strip()) < 10:
            validation_result["warnings"].append(
                f"Step {i + 1} '{step.title}' has insufficient description"
            )

    # If AGENTS.md is available, suggest following it
    if architecture_guidelines.get("has_agents_md"):
        validation_result["suggestions"].append(
            "Ensure the plan follows the architecture guidelines specified in AGENTS.md"
        )

    return validation_result


def generate_plan(state: PlannerState) -> PlannerState:
    """
    Generate Plan node - PHASE 4: Create detailed implementation plan.

    Tasks:
    1. Determine task complexity score (1-10)
    2. Create simple or complex plan based on complexity
    3. Include implementation steps với detailed guidance
    4. Estimate effort và story points
    5. Document risks và assumptions
    6. Structure output trong ImplementationPlan model

    Args:
        state: PlannerState với dependency_mapping

    Returns:
        Updated PlannerState với implementation_plan populated
    """
    print("\n" + "=" * 80)
    print("PLAN: GENERATE PLAN NODE - Phase 4: Implementation Planning")
    print("=" * 80)

    try:
        task_requirements = state.task_requirements
        dependency_mapping = state.dependency_mapping
        codebase_analysis = state.codebase_analysis

        print(f"🎯 Generating implementation plan for: {task_requirements.task_id}")
        print(f"📁 Files to create: {len(codebase_analysis.files_to_create)}")
        print(f"✏️  Files to modify: {len(codebase_analysis.files_to_modify)}")
        print(f"📦 Affected modules: {len(codebase_analysis.affected_modules)}")

        # Detect task scope (backend, frontend, or fullstack)
        task_scope = _detect_task_scope(codebase_analysis)
        print("\n🔍 Task Scope Detection:")
        print(f"   Needs Backend: {task_scope['needs_backend']}")
        print(f"   Needs Frontend: {task_scope['needs_frontend']}")
        if task_scope["is_fullstack"]:
            print("   ⚡ FULLSTACK task detected - will load both BE and FE guidelines")

        # Load architecture guidelines from AGENTS.md with task scope
        codebase_path = getattr(state, "codebase_path", "") or ""
        architecture_guidelines = load_architecture_guidelines(
            codebase_path, task_scope
        )
        project_structure = detect_project_structure(
            codebase_path, architecture_guidelines.get("stack_category", "unknown")
        )

        print("\n🏗️ Architecture Guidelines:")
        print(f"   Has AGENTS.md: {architecture_guidelines['has_agents_md']}")
        print(f"   Project Type: {architecture_guidelines['project_type']}")
        print(f"   Stack Category: {architecture_guidelines['stack_category']}")
        print(f"   Is Fullstack: {architecture_guidelines['is_fullstack']}")
        if architecture_guidelines.get("backend_guidelines"):
            print(
                f"   Backend Guidelines: Loaded ({len(architecture_guidelines['backend_guidelines'].get('content', ''))} chars)"
            )
        if architecture_guidelines.get("frontend_guidelines"):
            print(
                f"   Frontend Guidelines: Loaded ({len(architecture_guidelines['frontend_guidelines'].get('content', ''))} chars)"
            )
        print(
            f"   Detected Folders: {', '.join(project_structure.get('detected_folders', []))}"
        )

        # Load detailed codebase context (existing files, functions, classes)
        from app.agents.developer.planner.tools.codebase_analyzer import (
            analyze_codebase_context,
        )

        try:
            detailed_codebase_context = analyze_codebase_context(codebase_path)
            print(
                f"✅ Loaded detailed codebase context ({len(detailed_codebase_context)} chars)"
            )
        except Exception as e:
            print(f"⚠️ Failed to load detailed codebase context: {e}")
            detailed_codebase_context = "Detailed codebase analysis not available"

        # Use LLM for plan generation with Chain of Vibe methodology
        import json
        import os

        from langchain_openai import ChatOpenAI

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Create Chain of Vibe prompt for plan generation
        plan_prompt = f"""# CHAIN OF VIBE IMPLEMENTATION PLANNING

You are an expert implementation planner using the "Chain of Vibe" methodology for hierarchical, incremental task decomposition.

## METHODOLOGY: Chain of Vibe Task Decomposition

**Core Principles:**
1. **Hierarchical Breakdown**: Each major step decomposes into atomic sub-steps
2. **Logical Dependencies**: Steps ordered by technical dependencies (data → logic → UI)
3. **Actionable Granularity**: Each sub-step is a single, testable change (~15-30 minutes)
4. **Incremental Execution**: Each sub-step produces working code that can be committed
5. **Full-Stack Coverage**: Unified plan covering backend → frontend → integration
6. **NO DUPLICATES**: NEVER create files/functions that already exist - MODIFY them instead

## TASK CONTEXT

Tech Stack: {state.tech_stack or "unknown"}
Task ID: {task_requirements.task_id}
Task Title: {task_requirements.task_title}

Requirements:
{json.dumps(task_requirements.requirements, indent=2)}

Acceptance Criteria:
{json.dumps(task_requirements.acceptance_criteria, indent=2)}

Technical Specs:
{json.dumps(task_requirements.technical_specs, indent=2)}

Codebase Analysis:
Files to Create: {len(codebase_analysis.files_to_create)}
{json.dumps([f["path"] for f in codebase_analysis.files_to_create], indent=2)}

Files to Modify: {len(codebase_analysis.files_to_modify)}
{json.dumps([f["path"] for f in codebase_analysis.files_to_modify], indent=2)}

Affected Modules:
{json.dumps(codebase_analysis.affected_modules, indent=2)}

API Endpoints:
{json.dumps(codebase_analysis.api_endpoints, indent=2)}

Database Changes:
{json.dumps(codebase_analysis.database_changes, indent=2)}

Dependency Mapping:
{dependency_mapping.model_dump_json(indent=2)}

## DETAILED CODEBASE CONTEXT

**CRITICAL**: The following shows EXISTING files, classes, and functions in the codebase.
DO NOT create duplicate files or functions that already exist.
If a file already exists with similar functionality, MODIFY it instead of creating a new one.

{detailed_codebase_context}

## ARCHITECTURE GUIDELINES

Project Type: {architecture_guidelines["project_type"]}
Stack Category: {architecture_guidelines["stack_category"]}
Has AGENTS.md: {architecture_guidelines["has_agents_md"]}
Is Fullstack Task: {architecture_guidelines["is_fullstack"]}

{"**⚡ IMPORTANT: This is a FULLSTACK task requiring both BACKEND and FRONTEND changes.**" if architecture_guidelines["is_fullstack"] else ""}
{"**You MUST follow the architecture guidelines for BOTH backend and frontend sections below.**" if architecture_guidelines["is_fullstack"] else ""}

Existing Project Structure:
{json.dumps(project_structure, indent=2)}

{_get_architecture_guidelines_text(architecture_guidelines, project_structure)}

## OUTPUT FORMAT

Generate a detailed implementation plan in JSON format:

```json
{{
            "task_id": "{task_requirements.task_id}",
  "description": "Clear description of what will be implemented",
  "complexity_score": 1-10,
  "plan_type": "simple|complex",

  "functional_requirements": [
    "Requirement 1 extracted from task",
    "Requirement 2 extracted from task"
  ],

  "steps": [
    {{
                "step": 1,
      "title": "Setup JWT authentication foundation",
      "description": "Install dependencies and configure JWT infrastructure",
      "category": "backend",
      "sub_steps": [
        {{
                    "sub_step": "1.1",
          "title": "Install jsonwebtoken and bcrypt libraries",
          "description": "Add JWT and password hashing libraries to package.json",
          "action_type": "setup|create|modify|test",
          "files_affected": ["package.json"],
          "test":"Run npm install and verify jsonwebtoken and bcrypt are installed correctly"
        }},
        {{
                    "sub_step": "1.2",
          "title": "Create JWT utility functions",
          "description": "Implement signToken() and verifyToken() helper functions",
          "action_type": "create",
          "files_affected": ["src/utils/jwt.js"],
          "test": "Import and call signToken() with test payload, verify it returns valid JWT string"
        }},
        {{
                    "sub_step": "1.3",
          "title": "Add JWT_SECRET to environment config",
          "description": "Add JWT_SECRET variable to .env and config loader",
          "action_type": "modify",
          "files_affected": [".env.example", "src/config/environment.js"],
          "test": "Start application and verify JWT_SECRET is loaded correctly from environment"
        }}
      ],
    }},
    {{
                "step": 2,
      "title": "Implement login API endpoint",
      "description": "Create authentication endpoint with credential validation",
      "category": "backend",
      "sub_steps": [
        {{
                    "sub_step": "2.1",
          "title": "Create auth router and login route",
          "description": "Setup POST /api/auth/login route with Express router",
          "action_type": "create",
          "files_affected": ["src/routes/auth.routes.js", "src/app.js"],
          "test": "Send POST request to /api/auth/login and verify route is accessible (404 → 400/500)"
        }},
        {{
                    "sub_step": "2.2",
          "title": "Implement login controller logic",
          "description": "Create controller to validate credentials and generate JWT",
          "action_type": "create",
          "files_affected": ["src/controllers/auth.controller.js"],
          "test": "Call login controller with test credentials and verify JWT token is generated"
        }},
        {{
                    "sub_step": "2.3",
          "title": "Add request validation middleware",
          "description": "Validate email format and password presence",
          "action_type": "create",
          "files_affected": ["src/middleware/validation.js"],
          "test": "Send invalid request (missing email/password) and verify 400 validation error"
        }}
      ],
    }},
    {{
                "step": 3,
      "title": "Create frontend Login Form component",
      "description": "Build React login form with validation and state management",
      "category": "frontend",
      "sub_steps": [
        {{
                    "sub_step": "3.1",
          "title": "Create LoginForm component structure",
          "description": "Setup functional component with form fields and basic styling",
          "action_type": "create",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Import and render LoginForm component, verify form fields are displayed correctly"
        }},
        {{
                    "sub_step": "3.2",
          "title": "Add form validation logic",
          "description": "Implement client-side validation with error messages",
          "action_type": "modify",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Submit form with invalid data and verify validation error messages appear"
        }},
        {{
                    "sub_step": "3.3",
          "title": "Add loading and error states",
          "description": "Implement loading spinner and API error display",
          "action_type": "modify",
          "files_affected": ["src/components/LoginForm.jsx"],
          "test": "Trigger loading state and verify spinner appears, trigger error and verify error message displays"
        }}
      ],
    }},
    {{
                "step": 4,
      "title": "Implement authentication state management",
      "description": "Create custom hook and API service for auth flow",
      "category": "frontend",
      "sub_steps": [
        {{
                    "sub_step": "4.1",
          "title": "Create auth API service",
          "description": "Implement API client for authentication endpoints",
          "action_type": "create",
          "files_affected": ["src/services/auth.service.js"],
          "test": "Call auth service login method with test data and verify API request is made correctly"
        }},
        {{
                    "sub_step": "4.2",
          "title": "Create useAuth custom hook",
          "description": "Build hook managing auth state and login function",
          "action_type": "create",
          "files_affected": ["src/hooks/useAuth.js"],
          "test": "Use useAuth hook in test component and verify auth state and login function work"
        }},
        {{
                    "sub_step": "4.3",
          "title": "Add token storage logic",
          "description": "Implement localStorage for JWT persistence",
          "action_type": "modify",
          "files_affected": ["src/hooks/useAuth.js", "src/services/auth.service.js"],
          "test": "Login and verify JWT token is stored in localStorage, refresh page and verify token persists"
        }}
      ],
    }},
    {{
                "step": 5,
      "title": "End-to-end integration testing",
      "description": "Test complete authentication flow from UI to backend",
      "category": "integration",
      "sub_steps": [
        {{
                    "sub_step": "5.1",
          "title": "Test successful login flow",
          "description": "Verify complete flow with valid credentials",
          "action_type": "test",
          "files_affected": ["tests/integration/auth.test.js"],
          "test": "Run integration test and verify successful login returns JWT token and user data"
        }},
        {{
                    "sub_step": "5.2",
          "title": "Test error scenarios",
          "description": "Verify handling of invalid credentials and network errors",
          "action_type": "test",
          "files_affected": ["tests/integration/auth.test.js"],
          "test": "Run error scenario tests and verify proper error handling and user feedback"
        }}
      ],
      "dependencies": [4],
      "estimated_hours": 0.7,
      "complexity": "low"
    }}
  ],

  "database_changes": [
    {{
                "change": "Add users table",
      "fields": ["id", "email", "password_hash", "created_at", "updated_at"],
      "affected_step": 1
    }}
  ],

  "external_dependencies": [
    {{"package": "jsonwebtoken", "version": "^9.0.0", "purpose": "JWT token generation"}},
    {{"package": "bcrypt", "version": "^5.1.0", "purpose": "Password hashing"}}
  ],

  "internal_dependencies": [
    {{"module": "User model", "required_by_step": 2}},
    {{"module": "Validation middleware", "required_by_step": 2}}
  ],

  "total_estimated_hours": 4.4,
  "story_points": 5,

  "execution_order": [
    "Execute steps sequentially: 1 → 2 → 3 → 4 → 5",
    "Within each step, execute sub-steps in order",
    "Test after each sub-step before proceeding",
    "Commit code after each completed sub-step"
  ]
}}
```

## CRITICAL REQUIREMENTS FOR INCREMENTAL EXECUTION

### Sub-Step Design Rules:
1. **Atomic Changes**: Each sub-step modifies 1-3 files maximum
2. **Single Responsibility**: One clear action per sub-step
3. **Testable**: Each sub-step has a verification method
4. **Committable**: Code should compile/run after each sub-step
5. **Time-Boxed**: 15-30 minutes per sub-step (never exceed 45 min)

### Action Types:
- `setup`: Install dependencies, configure environment
- `create`: Create new files/functions/components
- `modify`: Edit existing code incrementally
- `test`: Write or run tests

### Code Changes Format:
Each sub-step must specify `code_changes` with:
- `type`: What kind of change (create_file, modify_function, add_route, etc.)
- `specifics`: Exact functions/components/endpoints being added/modified
- `template`: (optional) Reference to code template to use

### Test Field Requirements:
Each sub-step must include a "test" field with immediate verification:
- **Specific and actionable**: Clear instructions for verifying completion
- **Quick verification**: Should take 1-3 minutes to execute
- **Immediate feedback**: Verify the sub-step works before proceeding
- **Examples**:
  - Setup: "Run npm install and verify package is installed correctly"
  - Create: "Import function and call with test data, verify expected output"
  - Modify: "Start application and verify new configuration is loaded"
  - Test: "Run test suite and verify all tests pass"

## EXAMPLES

### Good Sub-Step (Atomic, Testable):
```json
{{
            "sub_step": "2.1",
  "title": "Create login route handler",
  "description": "Add POST /api/auth/login route to Express router",
  "action_type": "create",
  "files_affected": ["src/routes/auth.routes.js"],
  "test": "Send POST to /api/auth/login and verify route is accessible (404 → 400/500)"
}}
```

### Bad Sub-Step (Too Vague):
```json
{{
            "sub_step": "2.1",
  "title": "Setup authentication",
  "description": "Create authentication system",
  // ❌ Too broad, multiple files, no clear verification
}}
```

## GENERATE PLAN NOW

Analyze the task requirements and generate a complete Chain of Vibe implementation plan with:
- Clear step hierarchy (major steps → atomic sub-steps)
- Logical dependency ordering
- Specific file changes for each sub-step
- **"test" field for each sub-step** with immediate verification instructions
- Realistic time estimates (sub-steps: 15-30 min, steps: 0.5-2 hours)

Output valid JSON following the exact format above.
"""

        print("🤖 Calling LLM for Chain of Vibe plan generation...")

        # Call LLM
        response = llm.invoke(plan_prompt)
        llm_output = response.content

        print(f"📝 LLM Response: {llm_output[:200]}...")

        # Parse JSON response from LLM - Handle markdown code blocks
        try:
            # Strip markdown code blocks if present
            cleaned_output = llm_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]  # Remove ```json
            elif cleaned_output.startswith("```"):
                cleaned_output = cleaned_output[3:]  # Remove ```
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]  # Remove trailing ```
            cleaned_output = cleaned_output.strip()

            print(f"🧹 Cleaned LLM output: {cleaned_output[:100]}...")

            parsed_plan = json.loads(cleaned_output)

            # Extract simplified plan data
            complexity_score = parsed_plan.get("complexity_score", 5)
            plan_type = parsed_plan.get("plan_type", "simple")

            # Convert steps to ImplementationStep objects
            from ..state import ImplementationStep

            steps_data = parsed_plan.get("steps", [])
            implementation_steps = []

            for step_data in steps_data:
                step = ImplementationStep(
                    step=step_data.get("step", 0),
                    title=step_data.get("title", ""),
                    description=step_data.get("description", ""),
                    category=step_data.get("category", "backend"),
                    sub_steps=step_data.get("sub_steps", []),
                    dependencies=step_data.get("dependencies", []),
                    estimated_hours=step_data.get("estimated_hours", 0.0),
                    complexity=step_data.get("complexity", "medium"),
                )
                implementation_steps.append(step)

            # Extract other simplified fields
            functional_requirements = parsed_plan.get("functional_requirements", [])
            database_changes = parsed_plan.get("database_changes", [])
            external_dependencies = parsed_plan.get("external_dependencies", [])
            internal_dependencies = parsed_plan.get("internal_dependencies", [])
            execution_order = parsed_plan.get("execution_order", [])
            total_estimated_hours = parsed_plan.get("total_estimated_hours", 0.0)
            story_points = parsed_plan.get("story_points", 0)

            print(
                f"✅ Successfully parsed Chain of Vibe plan with complexity {complexity_score}/10, {len(implementation_steps)} steps, {total_estimated_hours}h"
            )

        except json.JSONDecodeError as e:
            print(f"❌ LLM response not valid JSON after cleaning: {e}")
            print(f"Raw LLM output: {llm_output[:200]}...")
            print(
                f"Cleaned output: {cleaned_output[:200] if 'cleaned_output' in locals() else 'N/A'}..."
            )
            # Fallback for JSON parsing failure
            complexity_score = 5
            plan_type = "simple"
            implementation_steps = []
            functional_requirements = task_requirements.requirements or []
            database_changes = []
            external_dependencies = []
            internal_dependencies = []
            execution_order = []
            total_estimated_hours = 4.0
            story_points = 3

        print(f"INFO: Complexity Score: {complexity_score}/10")

        # Use implementation steps from LLM if available, otherwise create minimal fallback
        if not implementation_steps:
            print("⚠️ No implementation steps from LLM, using minimal fallback")
            from ..state import ImplementationStep

            fallback_step = ImplementationStep(
                step=1,
                title="Implement feature",
                description="Complete the requested feature implementation",
                category="backend",
                sub_steps=[],
                dependencies=[],
                estimated_hours=total_estimated_hours,
                complexity="medium",
            )
            implementation_steps = [fallback_step]

        # Calculate totals if not provided
        if total_estimated_hours == 0:
            total_estimated_hours = sum(
                step.estimated_hours for step in implementation_steps
            )

        if story_points == 0:
            story_points = estimate_story_points(
                complexity_score, total_estimated_hours
            )

        # Create simplified ImplementationPlan object
        implementation_plan = ImplementationPlan(
            task_id=task_requirements.task_id,
            description=task_requirements.task_title,
            complexity_score=complexity_score,
            plan_type=plan_type,
            functional_requirements=functional_requirements,
            steps=implementation_steps,
            database_changes=database_changes,
            external_dependencies=external_dependencies,
            internal_dependencies=internal_dependencies,
            execution_order=execution_order,
            total_estimated_hours=total_estimated_hours,
            story_points=story_points,
        )

        # Validate plan compliance
        print("🔍 Validating implementation plan...")
        validation_result = validate_plan_compliance(
            implementation_plan, architecture_guidelines
        )

        # Log validation results
        if validation_result["warnings"]:
            print("⚠️ Plan validation warnings:")
            for warning in validation_result["warnings"]:
                print(f"   - {warning}")

        if validation_result["suggestions"]:
            print("💡 Plan suggestions:")
            for suggestion in validation_result["suggestions"]:
                print(f"   - {suggestion}")

        if validation_result["errors"]:
            print("❌ Plan validation errors:")
            for error in validation_result["errors"]:
                print(f"   - {error}")
        else:
            print("✅ Plan passes validation")

        # Store validation results in state
        state.tools_output["plan_validation"] = validation_result

        # Update state
        state.implementation_plan = implementation_plan
        state.current_phase = "validate_plan"
        state.status = "plan_generated"

        # Store in tools_output
        state.tools_output["implementation_plan"] = implementation_plan.model_dump()

        # Add AI message
        plan_result = {
            "phase": "Chain of Vibe Implementation Planning",
            "plan_type": plan_type,
            "complexity_score": complexity_score,
            "total_steps": len(implementation_steps),
            "estimated_hours": total_estimated_hours,
            "story_points": story_points,
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 3: Chain of Vibe Implementation Planning - COMPLETED

Plan Results:
{json.dumps(plan_result, indent=2)}

Implementation Steps:
{chr(10).join(f"{step.step}. {step.title} ({step.estimated_hours}h)" for step in implementation_steps)}

Total Effort: {total_estimated_hours} hours ({story_points} story points)

Ready to proceed to Plan Validation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Chain of Vibe implementation plan generated successfully")
        print(f"PLAN: Plan Type: {plan_type}")
        print(f"INFO: Complexity: {complexity_score}/10")
        print(f"TIME:  Total Hours: {total_estimated_hours}")
        print(f"SCORE: Story Points: {story_points}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in plan generation: {e}")
        print("🔍 DEBUG: Exception details:")
        import traceback

        traceback.print_exc()

        # Set error status
        state.status = "error_plan_generation"
        state.error_message = f"Plan generation failed: {str(e)}"

        # Ensure implementation_plan is set to empty but valid structure
        # This prevents downstream nodes from accessing uninitialized fields
        state.implementation_plan = ImplementationPlan()

        # Set phase to finalize để handle error properly
        state.current_phase = "finalize"

        print(
            "❌ GENERATE PLAN FAILED: Set empty implementation_plan and routing to finalize"
        )
        print(f"   Error status: {state.status}")
        print(f"   Error message: {state.error_message}")

        return state


def estimate_story_points(complexity_score: int, total_hours: float) -> int:
    """Estimate story points using Fibonacci sequence based on complexity and hours."""
    # Fibonacci sequence: 1, 2, 3, 5, 8, 13, 21
    fibonacci = [1, 2, 3, 5, 8, 13, 21]

    # Base estimation on complexity score and hours
    if complexity_score <= 2 and total_hours <= 4:
        return 1
    elif complexity_score <= 4 and total_hours <= 8:
        return 2
    elif complexity_score <= 6 and total_hours <= 16:
        return 3
    elif complexity_score <= 7 and total_hours <= 24:
        return 5
    elif complexity_score <= 8 and total_hours <= 40:
        return 8
    elif complexity_score <= 9 and total_hours <= 60:
        return 13
    else:
        return 21


# Chain of Vibe methodology implementation complete
