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
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Analyze actual codebase for context
        # Use dynamic codebase_path from state, or fall back to default
        default_codebase_path = (
            r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
        )
        codebase_path = state.codebase_path or default_codebase_path
        print(f"🔍 Analyzing codebase at: {codebase_path}")

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
        state.current_phase = "map_dependencies"
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
        print(f"ERROR: Error in codebase analysis: {e}")
        state.status = "error_codebase_analysis"
        state.error_message = f"Codebase analysis failed: {str(e)}"
        return state
