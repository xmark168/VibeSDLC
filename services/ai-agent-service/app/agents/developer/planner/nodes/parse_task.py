"""
Parse Task Node

PHASE 1: Task Parsing - Extract requirements, acceptance criteria, constraints
"""

from langchain_core.messages import AIMessage

from app.agents.developer.planner.state import PlannerState, TaskRequirements


def parse_task(state: PlannerState) -> PlannerState:
    """
    Parse Task node - PHASE 1: Extract requirements và constraints.

    Tasks:
    1. Parse task description để extract requirements
    2. Identify acceptance criteria và business rules
    3. Extract technical specifications
    4. Document assumptions và constraints
    5. Structure output trong TaskRequirements model

    Args:
        state: PlannerState với task_description

    Returns:
        Updated PlannerState với task_requirements populated
    """
    print("\n" + "=" * 80)
    print("PLAN: PARSE TASK NODE - Phase 1: Task Parsing")
    print("=" * 80)

    try:
        # Use actual LLM with proper prompt from templates
        import json
        import os

        from langchain_openai import ChatOpenAI

        from app.agents.developer.planner.utils.prompts import TASK_PARSING_PROMPT

        task_description = state.task_description

        print(f"🔍 Analyzing task: {task_description[:100]}...")

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Bind tools to LLM - LLM has full autonomy to decide when/if to use them
        from ..tools.tavily_search import tavily_search_tool

        llm_with_tools = llm.bind_tools([tavily_search_tool])

        # Format prompt with context
        formatted_prompt = TASK_PARSING_PROMPT.format(
            task_description=task_description,
            context=state.codebase_context or "No additional context provided",
        )

        print("🤖 Calling LLM for task parsing (autonomous mode - tools available)...")

        # Call LLM - it autonomously decides whether to use tools
        response = llm_with_tools.invoke(formatted_prompt)

        # Handle tool calls if LLM autonomously decided to use them
        if hasattr(response, "tool_calls") and response.tool_calls:
            print(
                f"🔧 LLM autonomously requested {len(response.tool_calls)} tool call(s)"
            )

            # Execute tool calls and collect results
            from langchain_core.messages import HumanMessage, ToolMessage

            tool_messages = []
            for tool_call in response.tool_calls:
                print(
                    f"   → Executing: {tool_call['name']} with args: {tool_call['args']}"
                )

                # Execute the tool
                if tool_call["name"] == "tavily_search_tool":
                    tool_result = tavily_search_tool.invoke(tool_call["args"])
                    tool_messages.append(
                        ToolMessage(
                            content=str(tool_result), tool_call_id=tool_call["id"]
                        )
                    )
                    print(f"   ✓ Tool result: {str(tool_result)[:100]}...")

            # If tools were called, give LLM the results and let it continue
            if tool_messages:
                print("🔄 Feeding tool results back to LLM for final analysis...")

                # Create follow-up prompt asking for JSON output
                follow_up_prompt = f"""Based on the search results provided, now generate the task parsing output.

Original task: {task_description}

Please output ONLY a valid JSON object following this exact format (no markdown, no explanations):
{{{{
  "task_id": "Generated task ID",
  "task_title": "Clear, descriptive title",
  "functional_requirements": ["requirement 1", "requirement 2"],
  "acceptance_criteria": ["criteria 1", "criteria 2"],
  "business_rules": {{}},
  "technical_specs": {{}},
  "assumptions": [],
  "clarifications_needed": []
}}}}"""

                messages = [
                    HumanMessage(content=formatted_prompt),
                    response,
                    *tool_messages,
                    HumanMessage(content=follow_up_prompt),
                ]
                response = llm_with_tools.invoke(messages)
                print("✓ LLM completed analysis with tool results")

        llm_output = response.content

        print(f"📝 LLM Response: {llm_output[:200]}...")

        # Extract basic information
        task_id = f"TSK-{hash(task_description) % 10000:04d}"

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
            # Support both "requirements" and "functional_requirements" keys
            requirements = parsed_data.get(
                "functional_requirements"
            ) or parsed_data.get("requirements", [])
            acceptance_criteria = parsed_data.get("acceptance_criteria", [])
            business_rules = parsed_data.get("business_rules", {})
            technical_specs = parsed_data.get("technical_specs", {})
            assumptions = parsed_data.get("assumptions", [])
            constraints = parsed_data.get("constraints", [])

            print(
                f"✅ Successfully parsed LLM JSON with {len(requirements)} requirements, {len(acceptance_criteria)} criteria"
            )

        except json.JSONDecodeError as e:
            print(f"❌ LLM response not valid JSON after cleaning: {e}")
            print(f"Raw LLM output: {llm_output[:200]}...")
            print(
                f"Cleaned output: {cleaned_output[:200] if 'cleaned_output' in locals() else 'N/A'}..."
            )
            # NO FALLBACK - Return empty data if LLM fails
            requirements = []
            acceptance_criteria = []
            business_rules = {}
            technical_specs = {}
            assumptions = []
            constraints = []

        # Default assumptions
        assumptions.extend(
            [
                "Existing codebase patterns will be followed",
                "Database migrations will be handled appropriately",
            ]
        )

        # Default constraints
        constraints.extend(
            [
                "Must maintain backward compatibility",
                "Must follow existing code style and patterns",
                "Must include appropriate error handling",
            ]
        )

        # Create TaskRequirements object
        task_requirements = TaskRequirements(
            task_id=task_id,
            task_title=(
                task_description[:100] + "..."
                if len(task_description) > 100
                else task_description
            ),
            requirements=requirements,
            acceptance_criteria=acceptance_criteria,
            business_rules=business_rules,
            technical_specs=technical_specs,
            assumptions=assumptions,
            constraints=constraints,
        )

        # Update state
        state.task_requirements = task_requirements
        state.current_phase = "analyze_codebase"
        state.status = "task_parsed"

        # Store in tools_output for reference
        state.tools_output["task_parsing"] = task_requirements.model_dump()

        # Add AI message to conversation
        parsing_result = {
            "phase": "Task Parsing",
            "task_id": task_id,
            "requirements_count": len(requirements),
            "acceptance_criteria_count": len(acceptance_criteria),
            "business_rules_count": len(business_rules),
            "technical_specs": list(technical_specs.keys()),
            "status": "completed",
        }

        ai_message = AIMessage(
            content=f"""Phase 1: Task Parsing - COMPLETED

Task Analysis Results:
{json.dumps(parsing_result, indent=2)}

Key Requirements Identified:
{chr(10).join(f"- {req}" for req in requirements)}

Acceptance Criteria:
{chr(10).join(f"- {criteria}" for criteria in acceptance_criteria)}

Ready to proceed to Phase 2: Codebase Analysis."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Task parsing completed successfully")
        print(f"INFO: Requirements: {len(requirements)}")
        print(f"PLAN: Acceptance Criteria: {len(acceptance_criteria)}")
        print(f"STEP: Technical Specs: {list(technical_specs.keys())}")
        print(f"ITER: Next Phase: {state.current_phase}")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in task parsing: {e}")
        state.status = "error_task_parsing"
        state.error_message = f"Task parsing failed: {str(e)}"
        return state
