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

        # Determine task scope: prioritize labels from state, fallback to file path detection
        task_scope_from_labels = None
        if state.task_scope:
            # Convert task_scope string to dict format
            if state.task_scope == "backend":
                task_scope_from_labels = {
                    "needs_backend": True,
                    "needs_frontend": False,
                    "is_fullstack": False,
                }
            elif state.task_scope == "frontend":
                task_scope_from_labels = {
                    "needs_backend": False,
                    "needs_frontend": True,
                    "is_fullstack": False,
                }
            elif state.task_scope == "full-stack":
                task_scope_from_labels = {
                    "needs_backend": True,
                    "needs_frontend": True,
                    "is_fullstack": True,
                }

        # If no scope from labels, detect from file paths
        if task_scope_from_labels:
            task_scope = task_scope_from_labels
            scope_source = "LABELS"
        else:
            task_scope = _detect_task_scope(codebase_analysis)
            scope_source = "FILE PATHS"

        print("\n🔍 Task Scope Detection:")
        print(f"   Source: {scope_source}")
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

        # Import prompt generator
        from ..utils.prompts import create_chain_of_vibe_prompt

        # Create Chain of Vibe prompt for plan generation
        # Use task_scope from state if available, otherwise use detected scope
        task_scope_for_prompt = state.task_scope or (
            "full-stack"
            if task_scope["is_fullstack"]
            else ("backend" if task_scope["needs_backend"] else "frontend")
        )

        print(f"📋 Task Scope for Prompt: {task_scope_for_prompt}")

        # Format existing dependencies for prompt
        existing_dependencies_str = ""
        if state.codebase_analysis and state.codebase_analysis.existing_dependencies:
            existing_deps_dict = state.codebase_analysis.existing_dependencies

            # Format dependencies from package.json or requirements.txt
            all_deps = []

            # Node.js dependencies
            if existing_deps_dict.get("dependencies"):
                for pkg_name, version in existing_deps_dict["dependencies"].items():
                    all_deps.append(f"{pkg_name}@{version}")

            # Node.js devDependencies
            if existing_deps_dict.get("devDependencies"):
                for pkg_name, version in existing_deps_dict["devDependencies"].items():
                    all_deps.append(f"{pkg_name}@{version} (dev)")

            # Python dependencies
            if existing_deps_dict.get("dependencies") and not existing_deps_dict.get(
                "devDependencies"
            ):
                # This is likely Python format
                for pkg_name, version in existing_deps_dict["dependencies"].items():
                    all_deps.append(f"{pkg_name}=={version}")

            if all_deps:
                existing_dependencies_str = "Existing packages found:\n"
                for dep in all_deps:
                    existing_dependencies_str += f"- {dep}\n"
                print(
                    f"📦 Found {len(all_deps)} existing dependencies from package files"
                )
            else:
                print("📦 No existing dependencies found in package files")
        else:
            print("📦 No codebase analysis or existing dependencies available")

        plan_prompt = create_chain_of_vibe_prompt(
            state=state,
            task_requirements=task_requirements,
            detailed_codebase_context=detailed_codebase_context,
            project_structure=project_structure,
            architecture_guidelines_text=_get_architecture_guidelines_text(
                architecture_guidelines, project_structure
            ),
            task_scope=task_scope_for_prompt,
            existing_dependencies=existing_dependencies_str,
        )

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
                )
                implementation_steps.append(step)

            # Extract other simplified fields
            functional_requirements = parsed_plan.get("functional_requirements", [])
            database_changes = parsed_plan.get("database_changes", [])
            external_dependencies = parsed_plan.get("external_dependencies", [])
            internal_dependencies = parsed_plan.get("internal_dependencies", [])
            execution_order = parsed_plan.get("execution_order", [])
            story_points = parsed_plan.get("story_points", 0)

            # Validate external_dependencies structure
            if external_dependencies:
                print(
                    f"🔍 Validating {len(external_dependencies)} external dependencies..."
                )
                required_fields = [
                    "package",
                    "version",
                    "purpose",
                    "category",
                    "already_installed",
                    "installation_method",
                    "install_command",
                    "package_file",
                    "dependency_type",
                ]
                valid_categories = ["backend", "frontend"]
                valid_methods = ["npm", "yarn", "pip", "poetry"]
                valid_types = ["production", "development"]

                for i, dep in enumerate(external_dependencies):
                    # Check required fields
                    missing_fields = [
                        field for field in required_fields if field not in dep
                    ]
                    if missing_fields:
                        print(f"⚠️ Dependency {i + 1} missing fields: {missing_fields}")

                    # Validate category
                    if dep.get("category") not in valid_categories:
                        print(
                            f"⚠️ Dependency {i + 1} invalid category: {dep.get('category')}"
                        )

                    # Validate already_installed is boolean
                    if not isinstance(dep.get("already_installed"), bool):
                        print(
                            f"⚠️ Dependency {i + 1} already_installed must be boolean: {dep.get('already_installed')}"
                        )

                    # Validate installation_method
                    if dep.get("installation_method") not in valid_methods:
                        print(
                            f"⚠️ Dependency {i + 1} invalid installation_method: {dep.get('installation_method')}"
                        )

                    # Validate dependency_type
                    if dep.get("dependency_type") not in valid_types:
                        print(
                            f"⚠️ Dependency {i + 1} invalid dependency_type: {dep.get('dependency_type')}"
                        )

                    # Validate directory consistency
                    category = dep.get("category", "")
                    package_file = dep.get("package_file", "")
                    install_command = dep.get("install_command", "")

                    if category == "backend":
                        if package_file and not any(
                            dir_name in package_file for dir_name in ["be/", "backend/"]
                        ):
                            print(
                                f"⚠️ Dependency {i + 1} backend category but package_file doesn't contain 'be/' or 'backend/': {package_file}"
                            )
                        if install_command and not any(
                            dir_name in install_command
                            for dir_name in ["cd be", "cd backend"]
                        ):
                            print(
                                f"⚠️ Dependency {i + 1} backend category but install_command doesn't contain 'cd be' or 'cd backend': {install_command}"
                            )

                    elif category == "frontend":
                        if package_file and not any(
                            dir_name in package_file
                            for dir_name in ["fe/", "frontend/"]
                        ):
                            print(
                                f"⚠️ Dependency {i + 1} frontend category but package_file doesn't contain 'fe/' or 'frontend/': {package_file}"
                            )
                        if install_command and not any(
                            dir_name in install_command
                            for dir_name in ["cd fe", "cd frontend"]
                        ):
                            print(
                                f"⚠️ Dependency {i + 1} frontend category but install_command doesn't contain 'cd fe' or 'cd frontend': {install_command}"
                            )

                print("✅ External dependencies validation completed")
            else:
                print("📦 No external dependencies in plan")

            print(
                f"✅ Successfully parsed Chain of Vibe plan with complexity {complexity_score}/10, {len(implementation_steps)} steps, {story_points} story points"
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
            )
            implementation_steps = [fallback_step]

        # Calculate story points if not provided
        if story_points == 0:
            # Simple estimation based on complexity and number of steps
            story_points = min(13, max(1, complexity_score + len(implementation_steps)))

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
            "story_points": story_points,
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 3: Chain of Vibe Implementation Planning - COMPLETED

Plan Results:
{json.dumps(plan_result, indent=2)}

Implementation Steps:
{chr(10).join(f"{step.step}. {step.title}" for step in implementation_steps)}


Ready to proceed to Plan Validation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Chain of Vibe implementation plan generated successfully")
        print(f"PLAN: Plan Type: {plan_type}")
        print(f"INFO: Complexity: {complexity_score}/10")
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
