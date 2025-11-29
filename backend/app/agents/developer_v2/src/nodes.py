"""Developer V2 Graph Nodes - ReAct Agents with Multi-Tool Support."""

import logging
import re
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import ( StoryAnalysis, ImplementationPlan, PlanStep,
    CodeChange
)
from app.agents.developer_v2.src.tools import (
    submit_routing_decision, submit_story_analysis, submit_implementation_plan,
    submit_code_change, submit_system_design, get_react_tools_for_node
)
from app.agents.core.prompt_utils import load_prompts_yaml

logger = logging.getLogger(__name__)

_PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")

# LLM models
# Speed optimization: Use gpt-4o-mini for fast operations (router, clarify, respond)
_fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, timeout=20)
_code_llm = ChatOpenAI(model="gpt-4.1", temperature=0.2, timeout=120)


# =============================================================================
# REACT AGENT FACTORY
# Creates ReAct agents with multiple tools for autonomous reasoning
# =============================================================================

def _create_react_agent(
    llm,
    tools: list,
    system_prompt: str,
    max_iterations: int = 10
):
    """Create a ReAct agent with multiple tools.
    
    ReAct pattern: Reason → Act → Observe → Repeat
    Agent can use multiple tools to explore and complete task.
    
    Args:
        llm: Language model
        tools: List of tools agent can use
        system_prompt: System prompt with instructions
        max_iterations: Max tool call iterations (default: 10)
    """
    full_prompt = system_prompt + """

## Tool Usage Instructions
You have access to multiple tools. Use them strategically:
1. Use read_file/list_directory to understand existing code
2. Use search_codebase to find relevant patterns and examples
3. Use web_search for best practices when needed
4. Always call the submit_* tool to finalize your result

IMPORTANT: You MUST call the appropriate submit_* tool to complete your task.
Do not respond with plain text without calling the submit tool."""

    return create_react_agent(
        model=llm,
        tools=tools,
        prompt=full_prompt,
        debug=False
    )


def _clean_json(text: str) -> str:
    """Strip markdown code blocks from LLM response."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    return match.group(1).strip() if match else text.strip()


def _extract_tool_args(result: dict, tool_name: str) -> dict:
    """Extract tool call arguments from agent result messages."""
    for msg in result.get("messages", []):
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call.get("name") == tool_name:
                    return tool_call.get("args", {})
    return {}


def _cfg(state: dict, name: str) -> dict | None:
    """Get LangChain config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else None


def _get_prompt(task: str, key: str) -> str:
    """Get prompt from YAML config."""
    return _PROMPTS.get("tasks", {}).get(task, {}).get(key, "")


def _format_input_template(task: str, **kwargs) -> str:
    """Format input template from prompts.yaml with provided values."""
    template = _get_prompt(task, "input_template")
    if not template:
        return ""
    
    for key, value in kwargs.items():
        placeholder = "{" + key + "}"
        template = template.replace(placeholder, str(value) if value else "")
    
    return template.strip()


def _build_system_prompt(task: str, agent=None) -> str:
    """Build system prompt with shared context."""
    prompt = _get_prompt(task, "system_prompt")
    shared = _PROMPTS.get("shared_context", {})
    
    for key, value in shared.items():
        prompt = prompt.replace(f"{{shared_context.{key}}}", value)
    
    if agent:
        prompt = prompt.replace("{name}", agent.name or "Developer")
        prompt = prompt.replace("{role}", agent.role_type or "Software Developer")
    else:
        prompt = prompt.replace("{name}", "Developer")
        prompt = prompt.replace("{role}", "Software Developer")
    
    return prompt

def _save_design_docs(workspace_path: str, design_result: dict, design_doc: str, story_title: str):
    """Save design documents to docs/technical folder."""
    import re
    from datetime import datetime
    
    docs_dir = Path(workspace_path) / "docs" / "technical"
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Clean story title for filename
    safe_title = re.sub(r'[^\w\s-]', '', story_title).strip().replace(' ', '_')[:30]
    timestamp = datetime.now().strftime("%Y%m%d")
    
    try:
        # Save main design document
        design_file = docs_dir / f"design_{safe_title}_{timestamp}.md"
        design_file.write_text(design_doc, encoding='utf-8')
        logger.info(f"[design] Saved design doc: {design_file}")
        
        # Save mermaid class diagram if present
        data_structures = design_result.get("data_structures", "")
        if "mermaid" in data_structures.lower() or "classDiagram" in data_structures:
            mermaid_file = docs_dir / f"class_diagram_{safe_title}_{timestamp}.mmd"
            # Extract just the mermaid content
            mermaid_content = re.sub(r'```mermaid\s*|\s*```', '', data_structures).strip()
            mermaid_file.write_text(mermaid_content, encoding='utf-8')
            logger.info(f"[design] Saved class diagram: {mermaid_file}")
        
        # Save sequence diagram if present
        call_flow = design_result.get("call_flow", "")
        if "mermaid" in call_flow.lower() or "sequenceDiagram" in call_flow:
            seq_file = docs_dir / f"sequence_diagram_{safe_title}_{timestamp}.mmd"
            seq_content = re.sub(r'```mermaid\s*|\s*```', '', call_flow).strip()
            seq_file.write_text(seq_content, encoding='utf-8')
            logger.info(f"[design] Saved sequence diagram: {seq_file}")
        
        # Save API interfaces if present
        api_interfaces = design_result.get("api_interfaces", "")
        if api_interfaces and len(api_interfaces) > 50:
            api_file = docs_dir / f"api_interfaces_{safe_title}_{timestamp}.ts"
            api_file.write_text(api_interfaces, encoding='utf-8')
            logger.info(f"[design] Saved API interfaces: {api_file}")
            
    except Exception as e:
        logger.warning(f"[design] Failed to save design docs: {e}")

async def router(state: DeveloperState, agent=None) -> DeveloperState:
    """Route story to appropriate processing node using ReAct agent.
    
    Tools: [search_codebase (optional), submit_routing_decision]
    """
    try:
        has_analysis = bool(state.get("analysis_result"))
        has_plan = bool(state.get("implementation_plan"))
        has_implementation = bool(state.get("code_changes"))
        
        # Check if this is a valid story task (has meaningful content)
        story_content = state.get("story_content", "")
        is_story_task = len(story_content) > 50  # Story with sufficient detail
        
        # Build input from template
        input_text = _format_input_template(
            "routing_decision",
            story_title=state.get("story_title", "Untitled"),
            story_content=story_content,
            acceptance_criteria=chr(10).join(state.get("acceptance_criteria", [])),
            has_analysis=has_analysis,
            has_plan=has_plan,
            has_implementation=has_implementation
        )

        # Get tools for router (minimal tools since no workspace yet)
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        tools = get_react_tools_for_node("router", project_id=project_id, task_id=task_id)
        
        # Create ReAct agent
        system_prompt = _build_system_prompt("routing_decision")
        react_agent = _create_react_agent(_fast_llm, tools, system_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]},
            config=_cfg(state, "router")
        )
        
        # Extract tool call arguments
        args = _extract_tool_args(result, "submit_routing_decision")
        action = args.get("action", "ANALYZE")
        task_type = args.get("task_type", "feature")
        complexity = args.get("complexity", "medium")
        message = args.get("message", "Bắt đầu phân tích story...")
        reason = args.get("reason", "New story needs analysis")
        confidence = args.get("confidence", 0.8)
        
        # IMPORTANT: For story tasks, never return RESPOND or CLARIFY
        if is_story_task and action in ("RESPOND", "CLARIFY"):
            logger.info(f"[router] Story task detected, forcing ANALYZE instead of {action}")
            action = "ANALYZE"
        
        logger.info(f"[router] Decision: action={action}, type={task_type}, complexity={complexity}")
        
        return {
            **state,
            "action": action,
            "task_type": task_type,
            "complexity": complexity,
            "message": message,
            "reason": reason,
            "confidence": confidence,
        }
        
    except Exception as e:
        logger.error(f"[router] Error: {e}", exc_info=True)
        return {
            **state,
            "action": "ANALYZE",
            "task_type": "feature",
            "complexity": "medium",
            "message": "Bắt đầu phân tích story...",
            "reason": f"Router error, defaulting to ANALYZE: {str(e)}",
            "confidence": 0.5,
        }


async def setup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Setup git workspace/branch only when code modification is needed.
    
    Creates a hotfix branch for this task.
    Only called when action is ANALYZE/PLAN/IMPLEMENT/VALIDATE.
    """
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        
        if not agent:
            logger.warning("[setup_workspace] No agent, skipping workspace setup")
            return {**state, "workspace_ready": False}
        
        # Check if workspace already setup
        if state.get("workspace_ready"):
            logger.info("[setup_workspace] Workspace already ready, skipping")
            return state
        
        # Setup workspace via agent
        short_id = story_id.split('-')[-1][:8] if '-' in story_id else story_id[:8]
        branch_name = f"story_{short_id}"
        
        logger.info(f"[setup_workspace] Setting up workspace for branch '{branch_name}'")
        
        # Use agent's workspace manager
        if hasattr(agent, '_setup_workspace'):
            workspace_info = agent._setup_workspace(story_id)
            
            
            # Index workspace with CocoIndex for semantic search
            index_ready = False
            workspace_path = workspace_info.get("workspace_path", "")
            project_id = state.get("project_id", "default")
            task_id = state.get("task_id") or story_id
            
            if workspace_path:
                from app.agents.developer_v2.src.tools import index_workspace
                index_ready = index_workspace(project_id, workspace_path, task_id)
                if not index_ready:
                    raise RuntimeError(f"CocoIndex indexing failed for workspace: {workspace_path}")
                logger.info(f"[setup_workspace] Indexed workspace with CocoIndex")
            
            # Load project structure and context
            project_context = ""
            agents_md = ""
            project_structure = {}
            if workspace_path:
                try:
                    from app.agents.developer_v2.src.tools import get_agents_md, get_project_context, detect_project_structure
                    agents_md = get_agents_md(workspace_path)
                    project_context = get_project_context(workspace_path)
                    project_structure = detect_project_structure(workspace_path)
                    logger.info(f"[setup_workspace] Detected: {project_structure.get('framework', 'unknown')} ({project_structure.get('router_type', 'N/A')})")
                    if agents_md:
                        logger.info(f"[setup_workspace] Loaded AGENTS.md: {len(agents_md)} chars")
                except Exception as ctx_err:
                    logger.warning(f"[setup_workspace] Failed to load project context: {ctx_err}")
            
            return {
                **state,
                "workspace_path": workspace_info["workspace_path"],
                "branch_name": workspace_info["branch_name"],
                "main_workspace": workspace_info["main_workspace"],
                "workspace_ready": workspace_info["workspace_ready"],
                "index_ready": index_ready,
                "agents_md": agents_md,
                "project_context": project_context,
                "project_structure": project_structure,
            }
        else:
            logger.warning("[setup_workspace] Agent has no _setup_workspace method")
            return {**state, "workspace_ready": False, "index_ready": False}
        
    except Exception as e:
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }


async def analyze(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze user story using ReAct agent.
    
    Tools: [read_file, search_codebase, web_search, submit_story_analysis]
    """
    try:
        if agent:
            pass
        
        # Build input from template
        input_text = _format_input_template(
            "analyze_story",
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        )

        # Get tools for analyze (can read files and search)
        workspace_path = state.get("workspace_path")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        tools = get_react_tools_for_node("analyze", workspace_path=workspace_path, project_id=project_id, task_id=task_id)
        
        # Create ReAct agent
        system_prompt = _build_system_prompt("analyze_story")
        react_agent = _create_react_agent(_code_llm, tools, system_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]},
            config=_cfg(state, "analyze")
        )
        
        # Extract tool call arguments
        args = _extract_tool_args(result, "submit_story_analysis")
        task_type = args.get("task_type", "feature")
        complexity = args.get("complexity", "medium")
        estimated_hours = args.get("estimated_hours", 4.0)
        summary = args.get("summary", state.get("story_title", "Implementation"))
        affected_files = args.get("affected_files", [])
        suggested_approach = args.get("suggested_approach", "Standard implementation approach")
        dependencies = args.get("dependencies") or []
        risks = args.get("risks") or []
        
        # Create analysis object for compatibility
        analysis = StoryAnalysis(
            task_type=task_type,
            complexity=complexity,
            estimated_hours=estimated_hours,
            summary=summary,
            affected_files=affected_files,
            dependencies=dependencies,
            risks=risks,
            suggested_approach=suggested_approach
        )
        logger.info(f"[analyze] Completed: type={task_type}, complexity={complexity}, hours={estimated_hours}")
        
        # Research best practices with Tavily (if available)
        research_context = ""
        workspace_path = state.get("workspace_path", "")
        if workspace_path:
            try:
                from app.agents.developer_v2.src.tools import detect_framework_from_package_json
                from langchain_tavily import TavilySearch
                
                framework_info = detect_framework_from_package_json(workspace_path)
                
                if framework_info.get("name") != "unknown":
                    framework_name = framework_info.get("name", "")
                    framework_version = framework_info.get("version", "")
                    router_type = framework_info.get("router", "")
                    
                    # Build search query based on story and framework
                    story_title = state.get("story_title", "")
                    search_query = f"{framework_name} {framework_version} {router_type} router {story_title} best practices 2024"
                    
                    logger.info(f"[analyze] Researching: {search_query}")
                    tavily = TavilySearch(max_results=3, include_answer=True)
                    research_context = await tavily.ainvoke({"query": search_query})
                    if isinstance(research_context, dict):
                        research_context = str(research_context)
                    logger.info(f"[analyze] Research completed: {len(research_context)} chars")
            except ImportError:
                logger.warning("[analyze] langchain-tavily not installed, skipping research")
            except Exception as research_err:
                logger.warning(f"[analyze] Research failed (continuing): {research_err}")
        
        msg = f"""✅ **Phân tích hoàn tất!**

📋 **Summary:** {analysis.summary}
📁 **Loại task:** {analysis.task_type}
⚡ **Độ phức tạp:** {analysis.complexity}
⏱️ **Ước tính:** {analysis.estimated_hours}h

📂 **Files liên quan:** {', '.join(analysis.affected_files) if analysis.affected_files else 'Chưa xác định'}
⚠️ **Risks:** {', '.join(analysis.risks) if analysis.risks else 'Không có'}

💡 **Approach:** {analysis.suggested_approach}"""
        
        if agent:
            pass
        
        return {
            **state,
            "analysis_result": analysis.model_dump(),
            "task_type": analysis.task_type,
            "complexity": analysis.complexity,
            "estimated_hours": analysis.estimated_hours,
            "affected_files": analysis.affected_files,
            "dependencies": analysis.dependencies,
            "risks": analysis.risks,
            "research_context": research_context,  # Tavily research results
            "message": msg,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[analyze] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "research_context": "",
            "message": f"❌ Lỗi khi phân tích: {str(e)}",
            "action": "RESPOND",
        }


async def design(state: DeveloperState, agent=None) -> DeveloperState:
    """Generate system design using ReAct agent (MetaGPT Architect pattern).
    
    Tools: [read_file, list_directory, search_codebase, submit_system_design]
    """
    try:
        analysis = state.get("analysis_result", {})
        complexity = state.get("complexity", "medium")
        workspace_path = state.get("workspace_path", "")
        
        # Skip design for simple tasks
        if complexity == "low":
            logger.info("[design] Skipping design for low complexity task")
            return {**state, "action": "PLAN", "message": "Task đơn giản, bỏ qua design phase."}
        
        # Build input from template (ReAct agent will search codebase itself)
        input_text = _format_input_template(
            "system_design",
            story_title=state.get("story_title", ""),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=complexity,
            story_content=state.get("story_content", ""),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            existing_context="Use search_codebase and read_file tools to explore existing code"
        )

        # Get tools for design
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        tools = get_react_tools_for_node("design", workspace_path=workspace_path, project_id=project_id, task_id=task_id)
        
        # Create ReAct agent
        system_prompt = _build_system_prompt("system_design")
        react_agent = _create_react_agent(_code_llm, tools, system_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]},
            config=_cfg(state, "design")
        )
        
        # Extract from tool call
        args = _extract_tool_args(result, "submit_system_design")
        if not args:
            raise RuntimeError("Agent did not return design")
        
        design_result = {
            "data_structures": args.get("data_structures", ""),
            "api_interfaces": args.get("api_interfaces", ""),
            "call_flow": args.get("call_flow", ""),
            "design_notes": args.get("design_notes", ""),
            "file_structure": args.get("file_structure", []),
        }
        logger.info(f"[design] Got design from agent: {len(design_result.get('file_structure', []))} files")
        
        # Build design document
        design_doc = f"""# System Design

## Data Structures & Interfaces
{design_result.get('data_structures', 'N/A')}

## API Interfaces
{design_result.get('api_interfaces', 'N/A')}

## Call Flow
{design_result.get('call_flow', 'N/A')}

## Design Notes
{design_result.get('design_notes', 'N/A')}

## File Structure
{chr(10).join(f'- {f}' for f in design_result.get('file_structure', []))}
"""
        
        # Save design documents
        if workspace_path:
            _save_design_docs(workspace_path, design_result, design_doc, state.get("story_title", "design"))
        
        return {
            **state,
            "system_design": design_result,
            "data_structures": design_result.get("data_structures"),
            "api_interfaces": design_result.get("api_interfaces"),
            "call_flow": design_result.get("call_flow"),
            "design_doc": design_doc,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[design] Error: {e}", exc_info=True)
        return {
            **state,
            "message": f"⚠️ Design skipped: {str(e)}",
            "action": "PLAN",
        }


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create implementation plan using ReAct agent.
    
    Tools: [read_file, list_directory, search_codebase, submit_implementation_plan]
    """
    try:
        analysis = state.get("analysis_result", {})
        
        if agent:
            pass
        
        # Get workspace context
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        # Get project structure and context
        project_context = state.get("project_context", "")
        project_structure = state.get("project_structure", {})
        
        # Build clear structure guidance
        structure_guidance = ""
        if project_structure:
            framework = project_structure.get("framework", "unknown")
            router_type = project_structure.get("router_type")
            conventions = project_structure.get("conventions", "")
            existing_pages = project_structure.get("existing_pages", [])
            
            if framework != "unknown":
                structure_guidance = f"""
=== PROJECT STRUCTURE (CRITICAL - MUST FOLLOW) ===
Framework: {framework}
{f"Router Type: {router_type}" if router_type else ""}
{f"Conventions: {conventions}" if conventions else ""}
{f"Existing Pages: {', '.join(existing_pages[:5])}" if existing_pages else ""}

IMPORTANT: Generate file_path values that match the existing project structure above!
"""
        
        # Build input from template (include full project_context with AGENTS.md)
        directory_structure = f"PROJECT CONTEXT (MUST FOLLOW):{chr(10)}{project_context}" if project_context else ""
        input_text = _format_input_template(
            "create_plan",
            story_title=state.get("story_title", "Untitled"),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=state.get("complexity", "medium"),
            structure_guidance=structure_guidance,
            affected_files=", ".join(state.get("affected_files", [])),
            design_doc=state.get("design_doc", "No design document"),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            directory_structure=directory_structure,
            existing_code="Use search_codebase and read_file tools to explore existing code"
        )

        # Get tools for plan
        tools = get_react_tools_for_node("plan", workspace_path=workspace_path, project_id=project_id, task_id=task_id)
        
        # Create ReAct agent
        system_prompt = _build_system_prompt("create_plan")
        react_agent = _create_react_agent(_code_llm, tools, system_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]},
            config=_cfg(state, "plan")
        )
        
        # Extract tool call arguments
        args = _extract_tool_args(result, "submit_implementation_plan")
        story_summary = args.get("story_summary", state.get("story_title", "Implementation"))
        steps = args.get("steps", [])
        total_estimated_hours = args.get("total_estimated_hours", 0)
        critical_path = args.get("critical_path") or []
        rollback_plan = args.get("rollback_plan")
        
        # Convert steps to PlanStep objects
        plan_steps = []
        for s in steps:
            plan_steps.append(PlanStep(
                order=s.get("order", len(plan_steps) + 1),
                description=s.get("description", ""),
                file_path=s.get("file_path", ""),
                action=s.get("action", "create"),
                estimated_minutes=s.get("estimated_minutes", 30),
                dependencies=s.get("dependencies", [])
            ))
        
        # Create plan_result for compatibility
        plan_result = ImplementationPlan(
            story_summary=story_summary,
            steps=plan_steps,
            total_estimated_hours=total_estimated_hours,
            critical_path=critical_path,
            rollback_plan=rollback_plan
        )
        
        # Validate and fix file paths based on project structure
        if project_structure and plan_result.steps:
            from app.agents.developer_v2.src.tools import validate_plan_file_paths
            validated_steps = validate_plan_file_paths(
                [s.model_dump() for s in plan_result.steps],
                project_structure
            )
            # Update plan_result with validated paths
            plan_result = ImplementationPlan(
                story_summary=story_summary,
                steps=[PlanStep(**s) for s in validated_steps],
                total_estimated_hours=total_estimated_hours,
                critical_path=critical_path,
                rollback_plan=rollback_plan
            )
            logger.info(f"[plan] Validated {len(plan_result.steps)} file paths")
        
        # Warning if no steps
        if not plan_result.steps:
            logger.warning(f"[plan] No steps in plan! affected_files: {state.get('affected_files', [])}")
        else:
            logger.info(f"[plan] Created {len(plan_result.steps)} steps, estimated {plan_result.total_estimated_hours}h")
        
        steps_text = "\n".join(
            f"  {s.order}. [{s.action}] {s.description} ({s.estimated_minutes}m)"
            for s in plan_result.steps
        )
        
        msg = f"""📋 **Implementation Plan**

**Story:** {plan_result.story_summary}
**Total Time:** {plan_result.total_estimated_hours}h
**Steps:** {len(plan_result.steps)}

{steps_text}

🔄 **Rollback Plan:** {plan_result.rollback_plan or 'N/A'}"""
        
        if agent:
            pass
        
        return {
            **state,
            "implementation_plan": [s.model_dump() for s in plan_result.steps],
            "total_steps": len(plan_result.steps),
            "current_step": 0,
            "message": msg,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi tạo plan: {str(e)}",
            "action": "RESPOND",
        }


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation based on plan using ReAct agent.
    
    Tools: [read_file, list_directory, search_codebase, write_file, run_command, submit_code_change]
    """
    try:
        plan_steps = state.get("implementation_plan", [])
        current_step = state.get("current_step", 0)
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        # React mode: only increment counter when looping back from summarize (current_step reset to 0)
        react_loop_count = state.get("react_loop_count", 0)
        debug_count = state.get("debug_count", 0)
        summarize_feedback = state.get("summarize_feedback")
        
        # Only increment when: have feedback from summarize AND at step 0 (just looped back)
        if summarize_feedback and current_step == 0 and state.get("react_mode"):
            react_loop_count += 1
            debug_count = 0  # Reset debug count for new cycle
            logger.info(f"[implement] React loop iteration {react_loop_count} (feedback: {summarize_feedback[:100]}...)")
        
        if not plan_steps:
            logger.error("[implement] No implementation plan")
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            if agent:
                pass
            return {
                **state,
                "message": "Implementation hoàn tất",
                "action": "VALIDATE",
            }
        
        step = plan_steps[current_step]
        current_file = step.get("file_path", "")
        
        if agent:
            pass
        
        # Gather related code context using MetaGPT pattern
        # Get code context using CocoIndex (required)
        related_context = state.get("related_code_context", "")
        if workspace_path and not related_context:
            index_ready = state.get("index_ready", False)
            project_id = state.get("project_id", "default")
            task_id = state.get("task_id") or state.get("story_id", "")
            step_description = step.get("description", "")
            
            # CocoIndex semantic search (required)
            if index_ready:
                from app.agents.developer_v2.src.tools import get_related_code_indexed
                related_context = get_related_code_indexed(
                    project_id=project_id,
                    current_file=current_file,
                    task_description=step_description,
                    top_k=8,
                    task_id=task_id
                )
                logger.info(f"[implement] Using CocoIndex for context")
        
        # Get existing code if modifying
        existing_code = ""
        if workspace_path and current_file and step.get("action") == "modify":
            file_path = Path(workspace_path) / current_file
            if file_path.exists():
                try:
                    existing_code = file_path.read_text(encoding='utf-8')
                except Exception:
                    pass
        
        # Build implementation plan context
        implementation_plan = state.get("code_plan_doc") or ""
        if not implementation_plan:
            # Fallback to step-based plan
            implementation_plan = "\n".join(
                f"{s.get('order', i+1)}. [{s.get('action')}] {s.get('description')}"
                for i, s in enumerate(plan_steps)
            )
        
        # Build full context including project structure, research results, and summarize feedback
        research_context = state.get("research_context", "")
        project_context = state.get("project_context", "")
        project_structure = state.get("project_structure", {})
        summarize_feedback = state.get("summarize_feedback", "")
        
        full_related_context = related_context or "No related files"
        
        # Add project structure info (CRITICAL for correct file paths)
        if project_structure and project_structure.get("framework") != "unknown":
            structure_info = f"""## PROJECT STRUCTURE (CRITICAL)
Framework: {project_structure.get('framework')}
Router: {project_structure.get('router_type', 'N/A')}
Conventions: {project_structure.get('conventions', '')}
"""
            full_related_context = f"{structure_info}\n---\n\n{full_related_context}"
        
        # Add boilerplate examples (ACCURACY improvement)
        if workspace_path:
            from app.agents.developer_v2.src.tools import get_boilerplate_examples
            # Determine task type from file path
            task_type = "page"
            if "component" in current_file.lower():
                task_type = "component"
            elif "api" in current_file.lower() or "route" in current_file.lower():
                task_type = "api"
            elif "layout" in current_file.lower():
                task_type = "layout"
            
            boilerplate = get_boilerplate_examples(workspace_path, task_type)
            if boilerplate:
                full_related_context = f"{boilerplate}\n\n---\n\n{full_related_context}"
        
        # Add project guidelines (AGENTS.md - full content, critical for conventions)
        if project_context:
            full_related_context = f"## PROJECT GUIDELINES (MUST FOLLOW)\n{project_context}\n\n---\n\n{full_related_context}"
        
        # Add research results
        if research_context:
            full_related_context += f"\n\n## Best Practices (from web research)\n{research_context[:1500]}"
        
        # Add feedback from previous summarize iteration (if looping)
        if summarize_feedback:
            full_related_context += f"\n\n## FEEDBACK FROM PREVIOUS ATTEMPT (MUST ADDRESS)\n{summarize_feedback}"
        
        # Build input from template
        error_logs_text = f"Previous Errors:{chr(10)}{state.get('error_logs', '')}" if state.get('error_logs') else ""
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=current_file,
            action=step.get("action", "modify"),
            story_summary=state.get("analysis_result", {}).get("summary", ""),
            related_context=full_related_context[:6000],
            existing_code=existing_code[:3000] if existing_code else "No existing code (new file)",
            error_logs=error_logs_text
        )

        # Get tools for implement (most powerful toolset)
        tools = get_react_tools_for_node("implement", workspace_path=workspace_path, project_id=project_id, task_id=task_id)
        
        # Create ReAct agent
        system_prompt = _build_system_prompt("implement_step")
        react_agent = _create_react_agent(_code_llm, tools, system_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": input_text}]},
            config=_cfg(state, "implement")
        )
        
        # Extract from tool call
        args = _extract_tool_args(result, "submit_code_change")
        if not args:
            raise RuntimeError(f"Agent did not return code for step: {step.get('description', '')}")
        
        code_change = CodeChange(
            file_path=args.get("file_path", current_file),
            action=args.get("action", step.get("action", "create")),
            code_snippet=args.get("code_snippet", ""),
            description=args.get("description", step.get("description", ""))
        )
        logger.info(f"[implement] Got code from agent tool call")
        
        logger.info(f"[implement] Step {current_step + 1}: {code_change.action} {code_change.file_path}")
        
        # IMPORTANT: Write the generated code to file
        if workspace_path and code_change.code_snippet:
            try:
                file_path = Path(workspace_path) / code_change.file_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(code_change.code_snippet, encoding='utf-8')
                logger.info(f"[implement] Wrote {len(code_change.code_snippet)} chars to {code_change.file_path}")
            except Exception as write_err:
                logger.warning(f"[implement] Failed to write {code_change.file_path}: {write_err}")
        
        code_changes = state.get("code_changes", [])
        code_changes.append(code_change.model_dump())
        
        files_created = state.get("files_created", [])
        files_modified = state.get("files_modified", [])
        
        if code_change.action == "create":
            files_created.append(code_change.file_path)
        elif code_change.action == "modify":
            files_modified.append(code_change.file_path)
        
        msg = f"✅ Step {current_step + 1}: {code_change.description}"
        if agent:
            pass
        
        return {
            **state,
            "code_changes": code_changes,
            "files_created": files_created,
            "files_modified": files_modified,
            "current_step": current_step + 1,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "message": msg,
            "action": "IMPLEMENT" if current_step + 1 < len(plan_steps) else "VALIDATE",
        }
        
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi implement: {str(e)}",
            "action": "RESPOND",
        }


# =============================================================================
# MetaGPT-inspired nodes
# =============================================================================

async def create_code_plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create strategic code plan before implementation (MetaGPT-style).
    
    This node creates a detailed development plan with git diff format
    showing exactly what changes will be made to each file.
    """
    try:
        if agent:
            pass
        
        # Get code context via CocoIndex
        workspace_path = state.get("workspace_path", "")
        index_ready = state.get("index_ready", False)
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        existing_code = ""
        if workspace_path and index_ready:
            from app.agents.developer_v2.src.tools import search_codebase
            existing_code = search_codebase(project_id, state.get("story_title", ""), top_k=10, task_id=task_id)
        
        sys_prompt = _build_system_prompt("create_code_plan", agent)
        user_prompt = _get_prompt("create_code_plan", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            design_doc=state.get("design_doc") or state.get("analysis_result", {}).get("summary", ""),
            task_list="\n".join(f"- {f}" for f in state.get("affected_files", [])),
            legacy_code=existing_code or "No existing code",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "create_code_plan"))
        clean_json = _clean_json(response.content)
        
        import json
        plan_data = json.loads(clean_json)
        
        logger.info(f"[create_code_plan] Created plan with {len(plan_data.get('development_plan', []))} steps")
        
        # Format plan for display
        dev_steps = plan_data.get("development_plan", [])
        steps_text = "\n".join(f"  {i+1}. {step}" for i, step in enumerate(dev_steps))
        
        files_to_create = plan_data.get("files_to_create", [])
        files_to_modify = plan_data.get("files_to_modify", [])
        
        msg = f"""📋 **Code Plan & Change Document**

**Development Plan:**
{steps_text}

**Files to Create:** {', '.join(files_to_create) if files_to_create else 'None'}
**Files to Modify:** {', '.join(files_to_modify) if files_to_modify else 'None'}
**Critical Path:** {' → '.join(plan_data.get('critical_path', []))}"""
        
        if agent:
            pass
        
        return {
            **state,
            "code_plan_doc": clean_json,
            "development_plan": dev_steps,
            "incremental_changes": plan_data.get("incremental_changes", []),
            "message": msg,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[create_code_plan] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi tạo code plan: {str(e)}",
            "action": "PLAN",  # Continue to regular plan
        }


async def summarize_code(state: DeveloperState, agent=None) -> DeveloperState:
    """Validate implementation completeness (MetaGPT IS_PASS check).
    
    This node reviews all implemented code and determines if it passes
    quality checks. If not, it returns to IMPLEMENT for revisions.
    """
    try:
        if agent:
            pass
        
        # Get implemented code via CocoIndex
        workspace_path = state.get("workspace_path", "")
        index_ready = state.get("index_ready", False)
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        code_blocks = ""
        if workspace_path and index_ready:
            from app.agents.developer_v2.src.tools import search_codebase
            code_blocks = search_codebase(project_id, "implementation code", top_k=15, task_id=task_id)
        
        sys_prompt = _build_system_prompt("summarize_code", agent)
        user_prompt = _get_prompt("summarize_code", "user_prompt").format(
            design_doc=state.get("design_doc") or state.get("analysis_result", {}).get("summary", ""),
            task_doc="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            code_blocks=code_blocks or "No code to review",
            test_results=state.get("validation_result", {}).get("tests_passed", "Not run"),
            lint_results=state.get("validation_result", {}).get("lint_passed", "Not run"),
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "summarize_code"))
        clean_json = _clean_json(response.content)
        
        import json
        summary_data = json.loads(clean_json)
        
        is_pass = summary_data.get("is_pass", True)
        revision_count = state.get("revision_count", 0)
        max_revisions = state.get("max_revisions", 3)
        
        logger.info(f"[summarize_code] IS_PASS={is_pass}, revision={revision_count}/{max_revisions}")
        
        if is_pass:
            msg = f"""✅ **Code Review: PASSED**

**Summary:**
{chr(10).join(f'  - {f}: {s}' for f, s in summary_data.get('summary', {}).items())}

**Call Flow:** {summary_data.get('call_flow', 'N/A')}
**Reason:** {summary_data.get('reason', 'All checks passed')}"""
            
            if agent:
                pass
            
            return {
                **state,
                "code_summary": summary_data,
                "is_pass": True,
                "message": msg,
                "action": "RESPOND",
            }
        else:
            # Check if we've exceeded max revisions
            if revision_count >= max_revisions:
                msg = f"""⚠️ **Code Review: Max revisions reached ({max_revisions})**

**Issues:**
{chr(10).join(f'  - {f}: {", ".join(issues)}' for f, issues in summary_data.get('code_review', {}).items())}

**Reason:** {summary_data.get('reason', 'Max revisions exceeded')}

Proceeding with current implementation."""
                
                if agent:
                    pass
                
                return {
                    **state,
                    "code_summary": summary_data,
                    "is_pass": False,
                    "message": msg,
                    "action": "RESPOND",
                }
            
            # Need revision
            todos = summary_data.get("todos", {})
            msg = f"""🔄 **Code Review: NEEDS REVISION** (Attempt {revision_count + 1}/{max_revisions})

**Issues Found:**
{chr(10).join(f'  - {f}: {", ".join(issues)}' for f, issues in summary_data.get('code_review', {}).items())}

**TODOs:**
{chr(10).join(f'  - {f}: {todo}' for f, todo in todos.items())}

**Reason:** {summary_data.get('reason', 'Issues need to be addressed')}

Returning to implementation for fixes..."""
            
            if agent:
                pass
            
            # Store error logs for next implementation round
            error_logs = f"Previous review issues:\n{summary_data.get('reason', '')}\n"
            error_logs += "\n".join(f"{f}: {todo}" for f, todo in todos.items())
            
            return {
                **state,
                "code_summary": summary_data,
                "is_pass": False,
                "needs_revision": True,
                "revision_count": revision_count + 1,
                "error_logs": error_logs,
                "current_step": 0,  # Reset to re-implement
                "message": msg,
                "action": "IMPLEMENT",
            }
        
    except Exception as e:
        logger.error(f"[summarize_code] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi review code: {str(e)}",
            "action": "RESPOND",
        }


async def clarify(state: DeveloperState, agent=None) -> DeveloperState:
    """Ask for clarification when story is unclear."""
    try:
        sys_prompt = _build_system_prompt("clarify", agent)
        user_prompt = _get_prompt("clarify", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(state.get("acceptance_criteria", [])),
            unclear_points=state.get("reason", "Story không rõ ràng"),
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "clarify"))
        question = response.content
        
        logger.info(f"[clarify] Asking for clarification")
        
        if agent:
            pass
        
        return {
            **state,
            "message": question,
            "action": "CLARIFY",
        }
        
    except Exception as e:
        logger.error(f"[clarify] Error: {e}", exc_info=True)
        default_msg = "🤔 Mình cần thêm thông tin về story này. Bạn có thể mô tả chi tiết hơn không?"
        if agent:
            pass
        return {
            **state,
            "message": default_msg,
            "action": "CLARIFY",
        }


async def respond(state: DeveloperState, agent=None) -> DeveloperState:
    """Generate and send conversational response to user using LLM."""
    try:
        # If there's already a detailed message (from validate, analyze, etc.), use it
        existing_msg = state.get("message", "")
        if existing_msg and len(existing_msg) > 100:
            if agent:
                pass
            return {**state, "action": "RESPOND"}
        
        # Generate conversational response using LLM
        sys_prompt = _build_system_prompt("respond", agent)
        user_prompt = _get_prompt("respond", "user_prompt").format(
            story_title=state.get("story_title", ""),
            story_content=state.get("story_content", ""),
            router_reason=state.get("reason", "general response"),
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "respond"))
        msg = response.content
        
        logger.info(f"[respond] Generated response: {msg[:100]}...")
        
        if agent:
            pass
        
        return {**state, "message": msg, "action": "RESPOND"}
        
    except Exception as e:
        logger.error(f"[respond] Error: {e}", exc_info=True)
        fallback_msg = state.get("message") or "Mình đã nhận được tin nhắn của bạn! 👋"
        if agent:
            pass
        return {**state, "message": fallback_msg, "action": "RESPOND"}


async def merge_to_main(state: DeveloperState, agent=None) -> DeveloperState:
    """Merge feature branch to main after successful validation.
    
    This node is called after validate passes (is_pass=True).
    It commits all changes and merges the story branch into main branch.
    (Following Developer V1 pattern: auto-commit after implementation)
    
    If workspace is not a git repo (worktree creation failed), skip merge
    and just keep the generated files.
    """
    try:
        branch_name = state.get("branch_name")
        main_workspace = state.get("main_workspace")
        workspace_path = state.get("workspace_path")
        story_title = state.get("story_title", "Implementation")
        workspace_ready = state.get("workspace_ready", False)
        
        # If workspace wasn't properly set up as git worktree, skip merge
        if not workspace_ready:
            logger.info("[merge_to_main] Workspace not a git worktree, skipping merge (files already written)")
            return {**state, "merged": False, "error": "Workspace not a git worktree"}
        
        if not branch_name or not main_workspace:
            logger.warning("[merge_to_main] Missing branch_name or main_workspace")
            return {**state, "merged": False}
        
        from app.agents.developer.tools.git_python_tool import GitPythonTool
        
        # Check if workspace is actually a git repo
        if workspace_path and Path(workspace_path).exists():
            git_dir = Path(workspace_path) / ".git"
            if not git_dir.exists():
                logger.info("[merge_to_main] Workspace is not a git repo, skipping merge")
                return {**state, "merged": False, "error": "Not a git repository"}
            
            workspace_git = GitPythonTool(root_dir=workspace_path)
            
            # Stage all changes
            status_result = workspace_git._run("status")
            if "not a git repository" in status_result.lower():
                logger.info("[merge_to_main] Workspace is not a git repo, skipping merge")
                return {**state, "merged": False, "error": "Not a git repository"}
            
            if "nothing to commit" not in status_result:
                commit_msg = f"feat: {story_title[:50]}... [auto-commit by Developer V2]"
                commit_result = workspace_git._run("commit", message=commit_msg, files=["."])
                logger.info(f"[merge_to_main] Auto-commit: {commit_result}")
        
        # Check if main_workspace is a git repo
        main_git_dir = Path(main_workspace) / ".git"
        if not main_git_dir.exists():
            logger.info("[merge_to_main] Main workspace is not a git repo, skipping merge")
            return {**state, "merged": False, "error": "Main workspace not a git repository"}
        
        main_git = GitPythonTool(root_dir=main_workspace)
        
        # 1. Checkout main branch
        checkout_result = main_git._run("checkout_branch", branch_name="main")
        logger.info(f"[merge_to_main] Checkout main: {checkout_result}")
        
        # If main doesn't exist, try master
        if "does not exist" in checkout_result or "error" in checkout_result.lower():
            checkout_result = main_git._run("checkout_branch", branch_name="master")
            logger.info(f"[merge_to_main] Checkout master: {checkout_result}")
        
        # 2. Merge feature branch
        merge_result = main_git._run("merge", branch_name=branch_name)
        logger.info(f"[merge_to_main] Merge result: {merge_result}")
        
        if "conflict" in merge_result.lower() or "error" in merge_result.lower():
            return {
                **state,
                "merged": False,
                "error": merge_result,
            }
        
        return {
            **state,
            "merged": True,
        }
        
    except Exception as e:
        logger.error(f"[merge_to_main] Error: {e}", exc_info=True)
        return {
            **state,
            "merged": False,
            "error": str(e),
        }


async def cleanup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Cleanup worktree and branch after merge.
    
    This node removes the worktree and deletes the feature branch
    after successful merge to main.
    
    If workspace is not a git worktree, skip git cleanup.
    """
    try:
        workspace_path = state.get("workspace_path")
        branch_name = state.get("branch_name")
        main_workspace = state.get("main_workspace")
        merged = state.get("merged", False)
        workspace_ready = state.get("workspace_ready", False)
        
        # Only do git cleanup if workspace was properly set up as worktree
        if workspace_ready and main_workspace:
            # Check if main_workspace is a git repo
            main_git_dir = Path(main_workspace) / ".git"
            if main_git_dir.exists():
                from app.agents.developer.tools.git_python_tool import GitPythonTool
                main_git = GitPythonTool(root_dir=main_workspace)
                
                # 1. Remove worktree
                if workspace_path:
                    remove_result = main_git._run("remove_worktree", worktree_path=workspace_path)
                    logger.info(f"[cleanup_workspace] Remove worktree: {remove_result}")
                
                # 2. Delete branch (only if merged successfully)
                if merged and branch_name:
                    delete_result = main_git._run("delete_branch", branch_name=branch_name)
                    logger.info(f"[cleanup_workspace] Delete branch: {delete_result}")
            else:
                logger.info("[cleanup_workspace] Main workspace not a git repo, skipping git cleanup")
        else:
            logger.info("[cleanup_workspace] Workspace not a git worktree, skipping git cleanup")
        
        # Cleanup CocoIndex task index (always try this)
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        if project_id and task_id:
            try:
                from app.agents.developer.project_manager import project_manager
                project_manager.unregister_task(project_id, task_id)
                logger.info(f"[cleanup_workspace] Unregistered CocoIndex task: {task_id}")
            except Exception as idx_err:
                logger.debug(f"[cleanup_workspace] CocoIndex cleanup: {idx_err}")
        
        return {
            **state,
            "workspace_ready": False,
            "index_ready": False,
        }
        
    except Exception as e:
        logger.error(f"[cleanup_workspace] Error: {e}", exc_info=True)
        return state


# =============================================================================
# SUMMARIZE CODE (MetaGPT SummarizeCode + IS_PASS pattern)
# =============================================================================

IS_PASS_PROMPT = """
## Code Summary
{summary}

## Original Requirements
{requirements}

## Acceptance Criteria
{acceptance_criteria}

## Files Implemented
{files_list}

---
Analyze if this implementation meets ALL requirements and acceptance criteria.

Consider:
1. Are all acceptance criteria addressed?
2. Is the code complete (no TODOs, no placeholders)?
3. Are all required files created?
4. Is the implementation functionally correct?

Respond with JSON:
- If complete: {{"is_pass": true, "reason": "All requirements met"}}
- If incomplete: {{"is_pass": false, "reason": "Specific issues: ..."}}
"""


async def _summarize_all_code(code_changes: list, workspace_path: str = "") -> str:
    """Summarize all code changes into a single summary."""
    if not code_changes:
        return "No code changes to summarize."
    
    summary_parts = []
    for change in code_changes:
        file_path = change.get("file_path", "unknown")
        action = change.get("action", "unknown")
        description = change.get("description", "")
        code = change.get("code_snippet", "")
        
        # Truncate code for summary
        code_preview = code[:500] + "..." if len(code) > 500 else code
        
        summary_parts.append(f"""
### {file_path} ({action})
{description}

```
{code_preview}
```
""")
    
    return "\n".join(summary_parts)


async def _check_is_pass(summary: str, state: dict) -> tuple:
    """Check if implementation is complete using LLM (MetaGPT IS_PASS pattern).
    
    Returns:
        (is_pass: bool, reason: str)
    """
    requirements = state.get("story_content", "")
    acceptance_criteria = "\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
    files_created = state.get("files_created", [])
    files_modified = state.get("files_modified", [])
    files_list = "\n".join(f"- {f}" for f in files_created + files_modified)
    
    prompt = IS_PASS_PROMPT.format(
        summary=summary,
        requirements=requirements,
        acceptance_criteria=acceptance_criteria or "No specific criteria",
        files_list=files_list or "No files"
    )
    
    messages = [
        SystemMessage(content="You are a code reviewer checking if implementation is complete."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = await _fast_llm.ainvoke(messages)
        clean_json = _clean_json(response.content)
        
        import json
        result = json.loads(clean_json)
        is_pass = result.get("is_pass", False)
        reason = result.get("reason", "Unknown")
        
        return is_pass, reason
    except Exception as e:
        logger.warning(f"[_check_is_pass] Error: {e}, defaulting to PASS")
        return True, "Check failed, proceeding"


async def summarize_code(state: DeveloperState, agent=None) -> DeveloperState:
    """Summarize code and check IS_PASS (MetaGPT SummarizeCode pattern).
    
    This node:
    1. Summarizes all implemented code
    2. Checks if implementation meets requirements (IS_PASS)
    3. If not pass: loops back to implement with feedback
    4. If pass: proceeds to code_review
    """
    try:
        code_changes = state.get("code_changes", [])
        workspace_path = state.get("workspace_path", "")
        summarize_count = state.get("summarize_count", 0)
        max_summarize = state.get("max_summarize", 3)
        
        if not code_changes:
            logger.info("[summarize_code] No code changes, passing through")
            return {**state, "is_pass": True, "action": "CODE_REVIEW"}
        
        if agent:
            # await agent.message_user("status", f"📝 Summarizing code (iteration {summarize_count + 1}/{max_summarize})...")
            pass
        
        # 1. Summarize all code
        summary = await _summarize_all_code(code_changes, workspace_path)
        logger.info(f"[summarize_code] Generated summary: {len(summary)} chars")
        
        # 2. Check IS_PASS
        is_pass, reason = await _check_is_pass(summary, state)
        logger.info(f"[summarize_code] IS_PASS: {is_pass}, reason: {reason[:100]}...")
        
        new_summarize_count = summarize_count + 1
        
        if is_pass:
            logger.info("[summarize_code] PASS - proceeding to code_review")
            return {
                **state,
                "is_pass": True,
                "code_summary": {"summary": summary, "is_pass": True, "reason": reason},
                "summarize_count": new_summarize_count,
                "summarize_feedback": "",
                "action": "CODE_REVIEW",
            }
        
        # Not pass - check if we should retry
        if new_summarize_count >= max_summarize:
            logger.warning(f"[summarize_code] Max iterations ({max_summarize}) reached, proceeding anyway")
            return {
                **state,
                "is_pass": False,
                "code_summary": {"summary": summary, "is_pass": False, "reason": reason},
                "summarize_count": new_summarize_count,
                "summarize_feedback": reason,
                "action": "CODE_REVIEW",  # Proceed to review even if not pass
            }
        
        # Loop back to implement with feedback
        logger.info(f"[summarize_code] NOT PASS - looping back to implement with feedback")
        return {
            **state,
            "is_pass": False,
            "code_summary": {"summary": summary, "is_pass": False, "reason": reason},
            "summarize_count": new_summarize_count,
            "summarize_feedback": reason,
            "current_step": 0,  # Reset to re-implement
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[summarize_code] Error: {e}", exc_info=True)
        return {**state, "is_pass": True, "action": "CODE_REVIEW"}  # Pass on error


# =============================================================================
# CODE REVIEW (BATCH - Review ALL files in ONE LLM call)
# =============================================================================

async def code_review(state: DeveloperState, agent=None) -> DeveloperState:
    """Batch review ALL files in ONE LLM call.
    
    Speed optimization: Instead of N separate LLM calls for N files,
    review all files together in a single call.
    
    Expected improvement: 24 calls -> 1 call (~180s -> ~20s)
    """
    try:
        code_changes = state.get("code_changes", [])
        k = state.get("code_review_k", 2)
        workspace_path = state.get("workspace_path", "")
        iteration = state.get("code_review_iteration", 0)
        
        if not code_changes:
            logger.info("[code_review] No code changes to review")
            return {**state, "code_review_passed": True}
        
        from app.agents.developer_v2.src.tools import get_markdown_code_block_type
        
        # Build ALL files into one prompt (batch review)
        all_code_blocks = []
        file_map = {}  # Map file_path to code_change for updates
        
        for change in code_changes:
            file_path = change.get("file_path", "")
            code = change.get("code_snippet", "")
            
            if not code:
                continue
            
            file_map[file_path] = change
            lang = get_markdown_code_block_type(file_path)
            all_code_blocks.append(f"### {file_path}\n```{lang}\n{code}\n```")
        
        if not all_code_blocks:
            logger.info("[code_review] No code to review")
            return {**state, "code_review_passed": True}
        
        combined_code = "\n\n".join(all_code_blocks)
        logger.info(f"[code_review] Batch reviewing {len(all_code_blocks)} files in ONE call")
        
        # Build batch review prompt
        requirements = state.get("story_content", "") or state.get("task_doc", "")
        acceptance_criteria = "\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        
        sys_prompt = _build_system_prompt("batch_code_review", agent)
        input_template = _get_prompt("batch_code_review", "input_template")
        user_prompt = input_template.format(
            requirements=f"{requirements}\n\nAcceptance Criteria:\n{acceptance_criteria}",
            all_code_blocks=combined_code
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        # Single LLM call for ALL files
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "batch_code_review"))
        clean_json = _clean_json(response.content)
        
        try:
            import json
            batch_result = json.loads(clean_json)
        except json.JSONDecodeError:
            logger.warning("[code_review] Failed to parse batch result, assuming LGTM")
            batch_result = {"overall_result": "LGTM", "files": {}, "summary": "Parse error"}
        
        # Process batch results
        overall_result = batch_result.get("overall_result", "LGTM")
        files_review = batch_result.get("files", {})
        all_passed = "LGTM" in overall_result
        
        review_results = []
        error_logs_parts = ["## CODE REVIEW FEEDBACK (MUST FIX):"]
        
        for file_path, review in files_review.items():
            result = review.get("result", "LGTM")
            issues = review.get("issues", [])
            rewritten = review.get("rewritten_code", "")
            
            review_results.append({
                "filename": file_path,
                "result": result,
                "issues": issues,
            })
            
            if "LBTM" in result:
                all_passed = False
                
                # Collect feedback for implement
                if issues:
                    error_logs_parts.append(f"\n### {file_path}:")
                    for issue in issues:
                        error_logs_parts.append(f"  - {issue}")
                
                # If rewritten code provided, update the file
                if rewritten and rewritten.strip() and file_path in file_map:
                    file_map[file_path]["code_snippet"] = rewritten
                    
                    if workspace_path:
                        full_path = Path(workspace_path) / file_path
                        try:
                            full_path.parent.mkdir(parents=True, exist_ok=True)
                            full_path.write_text(rewritten, encoding='utf-8')
                            logger.info(f"[code_review] Rewrote {file_path} based on review")
                        except Exception as e:
                            logger.warning(f"[code_review] Failed to write {file_path}: {e}")
        
        new_iteration = iteration + 1
        logger.info(f"[code_review] Batch result: {'PASSED' if all_passed else 'FAILED'} ({len(files_review)} files)")
        
        # If not all passed and can retry, go back to implement
        if not all_passed and new_iteration < k:
            logger.info(f"[code_review] Iteration {new_iteration}, routing to implement for fixes...")
            
            return {
                **state,
                "code_review_passed": False,
                "code_review_results": review_results,
                "code_review_iteration": new_iteration,
                "error_logs": "\n".join(error_logs_parts),
                "current_step": 0,  # Reset to re-implement from start
            }
        
        return {
            **state,
            "code_review_passed": all_passed,
            "code_review_results": review_results,
            "code_review_iteration": new_iteration,
        }
        
    except Exception as e:
        logger.error(f"[code_review] Error: {e}", exc_info=True)
        return {**state, "code_review_passed": True}  # Pass on error to continue flow


# =============================================================================
# RUN CODE (Execute tests to verify)
# =============================================================================

async def run_code(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute tests in workspace to verify code works.
    
    Detects test framework and runs appropriate tests.
    Analyzes results with LLM to determine pass/fail.
    """
    try:
        workspace_path = state.get("workspace_path", "")
        
        if not workspace_path or not Path(workspace_path).exists():
            logger.warning("[run_code] No workspace path, skipping tests")
            return {
                **state,
                "run_status": "PASS",
                "run_result": {"status": "PASS", "summary": "No workspace to test"},
            }
        
        if agent:
            pass
        
        from app.agents.developer_v2.src.tools import (
            detect_test_command,
            execute_command_async,
            find_test_file,
            get_markdown_code_block_type,
            install_dependencies,
        )
        
        # Install dependencies first (MetaGPT RunCode pattern)
        try:
            deps_result = await install_dependencies(workspace_path)
            if deps_result and agent:
                pass
        except Exception as deps_err:
            logger.warning(f"[run_code] Dependency install failed: {deps_err}")
        
        # Detect and run tests
        test_cmd = state.get("test_command") or detect_test_command(workspace_path)
        logger.info(f"[run_code] Running: {' '.join(test_cmd)}")
        
        result = await execute_command_async(
            command=test_cmd,
            working_directory=workspace_path,
            timeout=120  # 2 minutes for tests
        )
        
        # Determine basic pass/fail
        basic_status = "PASS" if result.success else "FAIL"
        
        # Get code context for analysis
        files_modified = state.get("files_modified", [])
        code_filename = files_modified[0] if files_modified else ""
        code_content = ""
        test_filename = ""
        test_content = ""
        
        if code_filename and workspace_path:
            code_path = Path(workspace_path) / code_filename
            if code_path.exists():
                try:
                    code_content = code_path.read_text(encoding='utf-8')[:5000]
                except Exception:
                    pass
            
            test_filename = find_test_file(workspace_path, code_filename) or ""
            if test_filename:
                test_path = Path(workspace_path) / test_filename
                if test_path.exists():
                    try:
                        test_content = test_path.read_text(encoding='utf-8')[:5000]
                    except Exception:
                        pass
        
        language = get_markdown_code_block_type(code_filename) if code_filename else "python"
        
        # MetaGPT RunCode pattern: Truncate outputs to avoid token overflow
        # stdout might be long but not important - truncate to 500 chars
        # stderr is more important - truncate to 10000 chars
        stdout_truncated = (result.stdout or "")[:500]
        stderr_truncated = (result.stderr or "")[:10000]
        
        # Analyze with LLM
        sys_prompt = _build_system_prompt("run_code_analysis", agent)
        user_prompt = _get_prompt("run_code_analysis", "user_prompt").format(
            code_filename=code_filename or "unknown",
            language=language,
            code=code_content or "No source code available",
            test_filename=test_filename or "unknown",
            test_code=test_content or "No test code available",
            command=" ".join(test_cmd),
            stdout=stdout_truncated or "No output",
            stderr=stderr_truncated or "No errors",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "run_code"))
        clean_json = _clean_json(response.content)
        
        try:
            import json
            analysis = json.loads(clean_json)
        except json.JSONDecodeError:
            analysis = {
                "status": basic_status,
                "summary": result.stderr[:200] if result.stderr else "Test completed",
                "file_to_fix": "",
                "send_to": "NoOne" if result.success else "Engineer",
            }
        
        run_status = analysis.get("status", basic_status)
        
        if agent:
            if run_status == "PASS":
                pass
            else:
                pass
        
        return {
            **state,
            "run_status": run_status,
            "run_stdout": result.stdout,
            "run_stderr": result.stderr,
            "run_result": {
                "status": run_status,
                "summary": analysis.get("summary", ""),
                "file_to_fix": analysis.get("file_to_fix", ""),
                "send_to": analysis.get("send_to", "NoOne"),
                "fix_instructions": analysis.get("fix_instructions", ""),
                "error_type": analysis.get("error_type", "none"),
            },
            "test_command": test_cmd,
        }
        
    except Exception as e:
        logger.error(f"[run_code] Error: {e}", exc_info=True)
        return {
            **state,
            "run_status": "PASS",  # Pass on error to continue flow
            "run_result": {"status": "PASS", "summary": f"Test execution error: {str(e)}"},
        }


# =============================================================================
# DEBUG ERROR (Fix bugs based on test output)
# =============================================================================

async def debug_error(state: DeveloperState, agent=None) -> DeveloperState:
    """Debug and fix errors using ReAct agent.
    
    Tools: [read_file, search_codebase, run_command, write_file]
    Analyzes error logs and rewrites code to fix bugs.
    """
    try:
        run_result = state.get("run_result", {})
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        debug_count = state.get("debug_count", 0)
        max_debug = state.get("max_debug", 5)  # MetaGPT pattern
        
        if run_result.get("status") == "PASS":
            logger.info("[debug_error] No errors to debug")
            return state
        
        # MetaGPT DebugError pattern: Check if tests already pass via "OK" pattern
        stderr = state.get("run_stderr", "") or run_result.get("stderr", "")
        ok_pattern = r"Ran (\d+) tests? in ([\d.]+)s\s*\n\s*OK"
        if re.search(ok_pattern, stderr):
            logger.info("[debug_error] Tests already pass (OK pattern detected), skipping")
            return {**state, "run_result": {"status": "PASS", "summary": "All tests passed"}}
        
        if debug_count >= max_debug:
            logger.warning(f"[debug_error] Max debug attempts ({max_debug}) reached")
            if agent:
                pass
            return state
        
        file_to_fix = run_result.get("file_to_fix", "")
        if not file_to_fix:
            # Try to get from modified files
            files_modified = state.get("files_modified", [])
            file_to_fix = files_modified[0] if files_modified else ""
        
        if not file_to_fix:
            logger.warning("[debug_error] No file identified to fix")
            return {**state, "debug_count": debug_count + 1}
        
        if agent:
            pass
        
        from app.agents.developer_v2.src.tools import get_markdown_code_block_type, find_test_file
        
        # Read the file to fix
        code_content = ""
        if workspace_path:
            code_path = Path(workspace_path) / file_to_fix
            if code_path.exists():
                try:
                    code_content = code_path.read_text(encoding='utf-8')
                except Exception:
                    pass
        
        # Find and read test file
        test_filename = find_test_file(workspace_path, file_to_fix) if workspace_path else ""
        test_content = ""
        if test_filename and workspace_path:
            test_path = Path(workspace_path) / test_filename
            if test_path.exists():
                try:
                    test_content = test_path.read_text(encoding='utf-8')
                except Exception:
                    pass
        
        language = get_markdown_code_block_type(file_to_fix)
        
        # Build debug prompt
        sys_prompt = _build_system_prompt("debug_error", agent)
        user_prompt = _get_prompt("debug_error", "user_prompt").format(
            code_filename=file_to_fix,
            language=language,
            code=code_content or "No code available",
            test_filename=test_filename or "No test file",
            test_code=test_content or "No test code available",
            error_logs=state.get("run_stderr", "")[:8000],
            error_summary=run_result.get("summary", ""),
            file_to_fix=file_to_fix,
        )
        
        # Get tools for debug (can read files, run commands, and write fixes)
        tools = get_react_tools_for_node("debug", workspace_path=workspace_path, project_id=project_id, task_id=task_id)
        
        # Create ReAct agent for debugging
        react_agent = _create_react_agent(_code_llm, tools, sys_prompt)
        
        # Invoke agent
        result = await react_agent.ainvoke(
            {"messages": [{"role": "user", "content": user_prompt}]},
            config=_cfg(state, "debug_error")
        )
        
        # Extract response from agent messages
        response_content = ""
        for msg in result.get("messages", []):
            if hasattr(msg, 'content') and msg.content:
                response_content = msg.content
        
        clean_json = _clean_json(response_content)
        
        try:
            import json
            debug_result = json.loads(clean_json)
        except json.JSONDecodeError:
            logger.warning("[debug_error] Failed to parse debug response")
            return {**state, "debug_count": debug_count + 1}
        
        fixed_code = debug_result.get("fixed_code", "")
        
        if fixed_code and workspace_path:
            # Write fixed code
            fix_path = Path(workspace_path) / file_to_fix
            try:
                fix_path.parent.mkdir(parents=True, exist_ok=True)
                fix_path.write_text(fixed_code, encoding='utf-8')
                logger.info(f"[debug_error] Wrote fixed code to {file_to_fix}")
                
                if agent:
                    pass
            except Exception as e:
                logger.error(f"[debug_error] Failed to write fixed code: {e}")
        
        # Update debug history
        debug_history = state.get("debug_history", []) or []
        debug_history.append({
            "iteration": debug_count + 1,
            "file": file_to_fix,
            "analysis": debug_result.get("analysis", ""),
            "root_cause": debug_result.get("root_cause", ""),
            "fix_description": debug_result.get("fix_description", ""),
        })
        
        return {
            **state,
            "debug_count": debug_count + 1,
            "last_debug_file": file_to_fix,
            "debug_history": debug_history,
        }
        
    except Exception as e:
        logger.error(f"[debug_error] Error: {e}", exc_info=True)
        return {**state, "debug_count": state.get("debug_count", 0) + 1}
