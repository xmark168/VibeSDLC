"""
Analyze Codebase Node

PHASE 2: Codebase Analysis - Analyze existing code, dependencies, affected files
"""

from langchain_core.messages import AIMessage

from app.agents.developer.planner.state import CodebaseAnalysis, PlannerState


def analyze_codebase(state: PlannerState) -> PlannerState:
    """
    Analyze Codebase node - PHASE 2: Analyze existing code và dependencies.

    Tasks:
    1. Use tools để analyze existing codebase
    2. Identify files to create/modify
    3. Map affected modules và dependencies
    4. Analyze database schema changes
    5. Map API endpoints changes
    6. Assess testing requirements

    Args:
        state: PlannerState với task_requirements

    Returns:
        Updated PlannerState với codebase_analysis populated
    """
    print("\n" + "=" * 80)
    print("🔍 ANALYZE CODEBASE NODE - Phase 2: Codebase Analysis")
    print("=" * 80)

    try:
        task_requirements = state.task_requirements
        task_description = state.task_description

        print(f"🎯 Analyzing codebase for task: {task_requirements.task_id}")

        # Use actual LLM with codebase analysis tools and proper prompt
        import json
        import os

        from langchain_openai import ChatOpenAI

        from app.agents.developer.planner.tools.codebase_analyzer import (
            analyze_codebase_context,
        )
        from app.templates.prompts.developer.planner import CODEBASE_ANALYSIS_PROMPT

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4.1",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Analyze actual codebase for context
        # Priority: sandbox path > explicit codebase_path > default local path
        default_codebase_path = (
            r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
        )

        if state.sandbox_id and state.codebase_path:
            # Using Daytona sandbox with cloned repository
            codebase_path = state.codebase_path
            print(f"🏗️  Using Daytona sandbox: {state.sandbox_id}")
            print(f"🔍 Analyzing codebase at: {codebase_path}")
        elif state.codebase_path:
            # Using explicit local codebase path
            codebase_path = state.codebase_path
            print(f"📁 Using local codebase path: {codebase_path}")
        else:
            # Fallback to default local path
            codebase_path = default_codebase_path
            print(f"🏠 Using default codebase path: {codebase_path}")

        try:
            codebase_context = analyze_codebase_context(codebase_path)
            print(
                f"✅ Codebase analysis completed - {len(codebase_context)} chars of context"
            )
        except Exception as e:
            print(f"⚠️ Codebase analysis failed: {e}")
            codebase_context = (
                "Codebase analysis not available - using LLM knowledge only"
            )

        # Format prompt with context
        formatted_prompt = CODEBASE_ANALYSIS_PROMPT.format(
            task_requirements=task_requirements.model_dump_json(indent=2),
            tech_stack=state.tech_stack or "unknown",
            codebase_context=codebase_context,
        )

        print("🤖 Calling LLM for codebase analysis...")

        # Call LLM
        response = llm.invoke(formatted_prompt)
        llm_output = response.content

        print(f"📝 LLM Response: {llm_output[:200]}...")

        # Try to parse JSON response from LLM
        files_to_create = []
        files_to_modify = []
        affected_modules = []
        database_changes = []
        api_endpoints = []
        external_dependencies = []
        internal_dependencies = []

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

            parsed_data = json.loads(cleaned_output)

            # Handle nested structure if LLM wraps data in "codebase_analysis"
            if "codebase_analysis" in parsed_data:
                analysis_data = parsed_data["codebase_analysis"]
            else:
                analysis_data = parsed_data

            files_to_create = analysis_data.get("files_to_create", [])
            files_to_modify = analysis_data.get("files_to_modify", [])
            affected_modules = analysis_data.get("affected_modules", [])
            database_changes = analysis_data.get("database_changes", [])
            api_endpoints = analysis_data.get("api_endpoints", [])
            external_dependencies = analysis_data.get("external_dependencies", [])
            internal_dependencies = analysis_data.get("internal_dependencies", [])

            print(
                f"✅ Successfully parsed LLM JSON with {len(files_to_create)} files to create, {len(files_to_modify)} files to modify, {len(api_endpoints)} API endpoints"
            )

        except json.JSONDecodeError as e:
            print(f"❌ LLM response not valid JSON after cleaning: {e}")
            print(f"Raw LLM output: {llm_output[:200]}...")
            print(
                f"Cleaned output: {cleaned_output[:200] if 'cleaned_output' in locals() else 'N/A'}..."
            )
            # NO FALLBACK - Return empty data if LLM fails
            files_to_create = []
            files_to_modify = []
            affected_modules = []
            database_changes = []
            api_endpoints = []
            external_dependencies = []
            internal_dependencies = []

        # 🔧 FALLBACK: Extract files from implementation steps if LLM didn't provide file operations
        if not files_to_create and not files_to_modify:
            print(
                "⚠️ LLM didn't provide file operations, extracting from implementation steps..."
            )
            files_to_create, files_to_modify = _extract_files_from_implementation_steps(
                state
            )
            print(
                f"🔧 Extracted: {len(files_to_create)} files to create, {len(files_to_modify)} files to modify"
            )

        # Create CodebaseAnalysis object
        codebase_analysis = CodebaseAnalysis(
            files_to_create=files_to_create,
            files_to_modify=files_to_modify,
            affected_modules=affected_modules,
            database_changes=database_changes,
            api_endpoints=api_endpoints,
            external_dependencies=external_dependencies,
            internal_dependencies=internal_dependencies,
        )

        # Update state
        state.codebase_analysis = codebase_analysis
        state.current_phase = "generate_plan"
        state.status = "codebase_analyzed"

        # Store in tools_output
        state.tools_output["codebase_analysis"] = codebase_analysis.model_dump()

        # Add AI message
        analysis_result = {
            "phase": "Codebase Analysis",
            "files_to_create": len(files_to_create),
            "files_to_modify": len(files_to_modify),
            "affected_modules": len(affected_modules),
            "database_changes": len(database_changes),
            "api_endpoints": len(api_endpoints),
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 2: Codebase Analysis - COMPLETED

        Analysis Results:
        {json.dumps(analysis_result, indent=2)}

        Files to Create:
        {chr(10).join(f"- {file['path']}: {file.get('purpose', file.get('reason', 'New file'))}" for file in files_to_create)}

        Files to Modify:
        {chr(10).join(f"- {file['path']}: {file['changes']}" for file in files_to_modify)}

        Affected Modules:
        {chr(10).join(f"- {module}" for module in affected_modules)}

        Ready to proceed to Phase 3: Dependency Mapping."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Codebase analysis completed successfully")
        print(f"📁 Files to create: {len(files_to_create)}")
        print(f"✏️  Files to modify: {len(files_to_modify)}")
        print(f"📦 Affected modules: {len(affected_modules)}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"❌ ERROR in analyze_codebase: {e}")
        import traceback

        traceback.print_exc()
        # Return state with error status
        state.status = "codebase_analysis_failed"
        state.error_message = str(e)
        # Keep current_phase as "analyze_codebase" since "error" is not a valid enum value
        return state


def _extract_files_from_implementation_steps(state):
    """
    Extract file operations from implementation steps when LLM fails to provide them.

    Args:
        state: PlannerState with implementation_plan containing steps

    Returns:
        tuple: (files_to_create, files_to_modify)
    """
    files_to_create = []
    files_to_modify = []

    if not hasattr(state, "implementation_plan") or not state.implementation_plan:
        print("❌ No implementation plan found in state")
        return files_to_create, files_to_modify

    implementation_steps = state.implementation_plan.implementation_steps
    if not implementation_steps:
        print("❌ No implementation steps found")
        return files_to_create, files_to_modify

    print(f"🔍 Processing {len(implementation_steps)} implementation steps...")

    seen_files = set()  # Track files we've already processed

    for i, step in enumerate(implementation_steps):
        step_files = step.get("files", [])
        step_title = step.get("title", f"Step {i + 1}")

        print(f"  Step {i + 1}: {step_title} -> {len(step_files)} files")

        for file_path in step_files:
            # If we've seen this file before, it should be a modification
            if file_path in seen_files:
                file_spec = {
                    "path": file_path,
                    "changes": step.get("description", step_title),
                    "complexity": step.get("complexity", "medium"),
                    "risk": "low",
                }
                files_to_modify.append(file_spec)
                print(f"    ✏️  MODIFY: {file_path} (already seen)")
            else:
                # New file - determine if create or modify based on patterns
                if _is_new_file(file_path, step):
                    file_spec = {
                        "path": file_path,
                        "reason": step.get("description", step_title),
                        "template": f"Implement {step_title}",
                        "estimated_lines": _estimate_file_size(file_path, step),
                        "complexity": step.get("complexity", "medium"),
                    }
                    files_to_create.append(file_spec)
                    print(f"    ✅ CREATE: {file_path}")
                else:
                    file_spec = {
                        "path": file_path,
                        "changes": step.get("description", step_title),
                        "complexity": step.get("complexity", "medium"),
                        "risk": "low",
                    }
                    files_to_modify.append(file_spec)
                    print(f"    ✏️  MODIFY: {file_path}")

                seen_files.add(file_path)

    print(
        f"🎯 Final extraction result: {len(files_to_create)} create, {len(files_to_modify)} modify"
    )
    return files_to_create, files_to_modify


def _is_new_file(file_path, step):
    """
    Determine if a file should be created or modified based on path and step context.

    Args:
        file_path: Path to the file
        step: Implementation step containing context

    Returns:
        bool: True if file should be created, False if modified
    """
    # Check step action/description for creation keywords
    action = step.get("action", "").lower()
    description = step.get("description", "").lower()
    title = step.get("title", "").lower()

    creation_keywords = ["create", "add", "implement", "new", "generate", "build"]
    modification_keywords = [
        "update",
        "modify",
        "change",
        "edit",
        "integrate",
        "include",
    ]

    # Check for explicit creation keywords
    for keyword in creation_keywords:
        if keyword in action or keyword in description or keyword in title:
            return True

    # Check for explicit modification keywords
    for keyword in modification_keywords:
        if keyword in action or keyword in description or keyword in title:
            return False

    # Special handling for documentation files
    if file_path.endswith((".md", ".txt", ".doc", ".rst")):
        # Documentation files with "update" in title/action are usually modifications
        if "update" in title or "update" in action or "document" in action:
            return False

    # Default heuristics based on file type and common patterns
    if file_path.endswith((".js", ".py", ".java", ".ts", ".go", ".rs")):
        # New source files are usually created
        if any(
            pattern in file_path
            for pattern in ["controller", "service", "model", "route", "middleware"]
        ):
            return True

    if file_path.endswith((".test.js", ".test.py", ".spec.js", ".spec.py")):
        # Test files are usually created
        return True

    if file_path in [
        "app/main.py",
        "app/main.js",
        "main.py",
        "main.js",
        "requirements.txt",
        "package.json",
    ]:
        # Main files and config files are usually modified
        return False

    # Default to creation for new files
    return True


def _estimate_file_size(file_path, step):
    """
    Estimate file size based on file type and step complexity.

    Args:
        file_path: Path to the file
        step: Implementation step containing context

    Returns:
        int: Estimated number of lines
    """
    complexity = step.get("complexity", "medium")

    # Base estimates by file type
    if file_path.endswith((".test.js", ".test.py", ".spec.js", ".spec.py")):
        base_lines = 200  # Test files tend to be longer
    elif file_path.endswith((".md", ".txt", ".doc")):
        base_lines = 50  # Documentation files
    elif "controller" in file_path or "route" in file_path:
        base_lines = 150  # API controllers/routes
    elif "model" in file_path:
        base_lines = 80  # Data models
    elif "service" in file_path:
        base_lines = 120  # Business logic services
    else:
        base_lines = 100  # Default

    # Adjust by complexity
    complexity_multiplier = {"low": 0.7, "medium": 1.0, "high": 1.5}

    final_estimate = int(base_lines * complexity_multiplier.get(complexity, 1.0))
    return max(final_estimate, 20)  # Minimum 20 lines
