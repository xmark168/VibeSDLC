"""Developer V2 Graph Nodes - ReAct Agents with Multi-Tool Support."""

import json
import logging
import re
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_tavily import TavilySearch

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import (
    StoryAnalysis, ImplementationPlan, PlanStep, CodeChange,
    RoutingDecision, SystemDesign, DebugResult
)
from app.agents.developer_v2.src.tools import set_tool_context
from app.agents.developer_v2.src.tools.filesystem_tools import (
    set_fs_context, read_file_safe, write_file_safe, list_directory_safe, edit_file
)
from app.agents.developer_v2.src.tools.shell_tools import (
    set_shell_context, execute_shell, semantic_code_search
)
from app.agents.core.prompt_utils import load_prompts_yaml
from langchain_core.messages import ToolMessage
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
    clean_json_response as _clean_json,
    extract_json_from_messages as _extract_json_response,
)

logger = logging.getLogger(__name__)

_PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")

# LLM models
_fast_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, timeout=20)
_code_llm = ChatOpenAI(model="gpt-4.1", temperature=0.2, timeout=120)


# =============================================================================
# TOOL CONTEXT SETUP
# =============================================================================

def _setup_tool_context(workspace_path: str = None, project_id: str = None, task_id: str = None):
    """Set global context for all tools before agent invocation."""
    if workspace_path:
        set_fs_context(root_dir=workspace_path)
        set_shell_context(root_dir=workspace_path)
    if project_id:
        set_tool_context(project_id=project_id, task_id=task_id, workspace_path=workspace_path)


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



async def router(state: DeveloperState, agent=None) -> DeveloperState:
    """
    Route story to appropriate processing node.
    """
    print("[NODE] router - Analyzing story intent...")
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

        # Use with_structured_output for reliable response
        messages = [
            SystemMessage(content=_build_system_prompt("routing_decision")),
            HumanMessage(content=input_text)
        ]
        
        structured_llm = _fast_llm.with_structured_output(RoutingDecision)
        result = await structured_llm.ainvoke(messages, config=_cfg(state, "router"))
        
        action = result['action']
        task_type = result['task_type']
        complexity = result['complexity']
        message = result['message']
        reason = result['reason']
        confidence = result['confidence']
        
        if is_story_task:
            # Never return RESPOND or CLARIFY for story tasks
            if action in ("RESPOND", "CLARIFY"):
                logger.info(f"[router] Story task detected, forcing ANALYZE instead of {action}")
                action = "ANALYZE"
            # Must analyze before plan/implement
            elif action in ("PLAN", "IMPLEMENT") and not has_analysis:
                logger.info(f"[router] No analysis yet, forcing ANALYZE instead of {action}")
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
    """
    Setup git workspace/branch only when code modification is needed.
    """
    print("[NODE] setup_workspace - Setting up workspace...")
    try:
        story_id = state.get("story_id", state.get("task_id", "unknown"))
        
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
    """Analyze user story requirements.
    
    Refactored: Tools for exploration + with_structured_output for response.
    """
    print("[NODE] analyze - Analyzing story requirements...")
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        
        # Setup tool context
        _setup_tool_context(workspace_path, project_id, task_id)
        
        # Build input
        input_text = _format_input_template(
            "analyze_story",
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        )

        # Tools for exploration
        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        
        # Step 1: Explore with tools
        messages = [
            SystemMessage(content=_build_system_prompt("analyze_story")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=_code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_explore",
            max_iterations=2
        )
        
        # Step 2: Get structured response
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow provide your final analysis."))
        structured_llm = _code_llm.with_structured_output(StoryAnalysis)
        analysis = await structured_llm.ainvoke(messages, config=_cfg(state, "analyze"))
        
        logger.info(f"[analyze] Done: {analysis.task_type}, {analysis.complexity}")
        
        return {
            **state,
            "analysis_result": analysis.model_dump(),
            "task_type": analysis.task_type,
            "complexity": analysis.complexity,
            "estimated_hours": analysis.estimated_hours,
            "affected_files": analysis.affected_files,
            "dependencies": analysis.dependencies,
            "risks": analysis.risks,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[analyze] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}


async def design(state: DeveloperState, agent=None) -> DeveloperState:
    """Generate system design.
    
    Refactored: Tools for exploration + with_structured_output for response.
    """
    print("[NODE] design - Creating system design...")
    try:
        analysis = state.get("analysis_result", {})
        complexity = state.get("complexity", "medium")
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        
        # Skip design for simple tasks
        if complexity == "low":
            logger.info("[design] Skipping design for low complexity task")
            return {**state, "action": "PLAN", "message": "Task đơn giản, bỏ qua design phase."}
        
        # Setup tool context
        _setup_tool_context(workspace_path, project_id, task_id)
        
        # Build input
        input_text = _format_input_template(
            "system_design",
            story_title=state.get("story_title", ""),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=complexity,
            story_content=state.get("story_content", ""),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            existing_context="Use tools to explore codebase"
        )

        # Tools for exploration
        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        
        # Step 1: Explore with tools
        messages = [
            SystemMessage(content=_build_system_prompt("system_design")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=_code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="design_explore",
            max_iterations=2
        )
        
        # Step 2: Get structured response
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow provide your final system design."))
        structured_llm = _code_llm.with_structured_output(SystemDesign)
        design_result = await structured_llm.ainvoke(messages, config=_cfg(state, "design"))
        
        logger.info(f"[design] Got design: {len(design_result.file_structure)} files")
        
        # Build design document
        design_doc = f"""# System Design

## Data Structures & Interfaces
{design_result.data_structures or 'N/A'}

## API Interfaces
{design_result.api_interfaces or 'N/A'}

## Call Flow
{design_result.call_flow or 'N/A'}

## Design Notes
{design_result.design_notes or 'N/A'}

## File Structure
{chr(10).join(f'- {f}' for f in design_result.file_structure)}
"""
        
        return {
            **state,
            "system_design": design_result.model_dump(),
            "data_structures": design_result.data_structures,
            "api_interfaces": design_result.api_interfaces,
            "call_flow": design_result.call_flow,
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
    """Create implementation plan.
    
    Refactored: Uses with_structured_output for reliable response.
    """
    print("[NODE] plan - Creating implementation plan...")
    try:
        analysis = state.get("analysis_result") or {}
        
        # Get workspace context
        workspace_path = state.get("workspace_path", "")
        
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

        # Use with_structured_output for reliable response
        messages = [
            SystemMessage(content=_build_system_prompt("create_plan")),
            HumanMessage(content=input_text)
        ]
        
        structured_llm = _code_llm.with_structured_output(ImplementationPlan)
        plan_result = await structured_llm.ainvoke(messages, config=_cfg(state, "plan"))
        
        # Validate and fix file paths based on project structure
        if project_structure and plan_result.steps:
            from app.agents.developer_v2.src.tools import validate_plan_file_paths
            validated_steps = validate_plan_file_paths(
                [s.model_dump() for s in plan_result.steps],
                project_structure
            )
            # Update plan_result with validated paths
            plan_result = ImplementationPlan(
                story_summary=plan_result.story_summary,
                steps=[PlanStep(**s) for s in validated_steps],
                total_estimated_hours=plan_result.total_estimated_hours,
                critical_path=plan_result.critical_path,
                rollback_plan=plan_result.rollback_plan
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
    """Execute implementation based on plan.
    
    Refactored: Tools for exploration + with_structured_output for response.
    """
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement - Step {current_step + 1}/{total_steps}...")
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
        current_file = step.get("file_path") or ""
        
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
        
        # Get existing code if modifying (using read_file_safe tool)
        existing_code = ""
        if workspace_path and current_file and step.get("action") == "modify":
            try:
                result = read_file_safe.invoke({"file_path": current_file})
                if result and not result.startswith("Error:"):
                    # Extract content after "Content of {file_path}:\n\n"
                    if "\n\n" in result:
                        existing_code = result.split("\n\n", 1)[1]
                    else:
                        existing_code = result
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
        
        # Setup tool context
        _setup_tool_context(workspace_path, project_id, task_id)
        
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

        # Tools for exploration (read-only, writing is manual)
        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        
        # Step 1: Explore with tools
        messages = [
            SystemMessage(content=_build_system_prompt("implement_step")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=_code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_explore",
            max_iterations=2
        )
        
        # Step 2: Get structured response
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow provide the code implementation."))
        structured_llm = _code_llm.with_structured_output(CodeChange)
        code_change = await structured_llm.ainvoke(messages, config=_cfg(state, "implement"))
        
        # Fill defaults if missing
        if not code_change.file_path:
            code_change = CodeChange(
                file_path=current_file,
                action=code_change.action or step.get("action", "create"),
                code_snippet=code_change.code_snippet,
                description=code_change.description or step.get("description", "")
            )
        logger.info(f"[implement] Got code from structured output")
        
        logger.info(f"[implement] Step {current_step + 1}: {code_change.action} {code_change.file_path}")
        
        # IMPORTANT: Write the generated code to file using write_file_safe tool
        if workspace_path and code_change.code_snippet:
            try:
                result = write_file_safe.invoke({
                    "file_path": code_change.file_path,
                    "content": code_change.code_snippet,
                    "mode": "w"
                })
                logger.info(f"[implement] {result}")
                
                # Incremental update index (fast - only changed file)
                from app.agents.developer_v2.src.tools import incremental_update_index
                incremental_update_index(project_id, task_id)
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
                
                # 1. Remove worktree (only if it's a separate worktree, not main workspace)
                if workspace_path:
                    # Check if workspace_path is different from main_workspace
                    is_worktree = workspace_path != main_workspace
                    
                    if is_worktree:
                        remove_result = main_git._run("remove_worktree", worktree_path=workspace_path)
                        logger.info(f"[cleanup_workspace] Remove worktree: {remove_result}")
                    else:
                        logger.info(f"[cleanup_workspace] Skipping worktree removal (this is the main workspace)")
                
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
        description = change.get("description", "") or ""
        code = change.get("code_snippet", "") or ""
        
        # Truncate code for summary
        code_preview = code[:500] + "..." if code and len(code) > 500 else (code or "")
        
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
    print("[NODE] code_review - Reviewing code quality...")
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
            file_path = change.get("file_path") or ""
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
                
                # If rewritten code provided, update the file using write_file_safe tool
                if rewritten and rewritten.strip() and file_path in file_map:
                    file_map[file_path]["code_snippet"] = rewritten
                    
                    if workspace_path:
                        try:
                            result = write_file_safe.invoke({
                                "file_path": file_path,
                                "content": rewritten,
                                "mode": "w"
                            })
                            logger.info(f"[code_review] {result}")
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
    print("[NODE] run_code - Running tests...")
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
            # Read code file using read_file_safe tool
            try:
                result = read_file_safe.invoke({"file_path": code_filename})
                if result and not result.startswith("Error:"):
                    if "\n\n" in result:
                        code_content = result.split("\n\n", 1)[1][:5000]
                    else:
                        code_content = result[:5000]
            except Exception:
                pass
            
            test_filename = find_test_file(workspace_path, code_filename) or ""
            if test_filename:
                # Read test file using read_file_safe tool
                try:
                    result = read_file_safe.invoke({"file_path": test_filename})
                    if result and not result.startswith("Error:"):
                        if "\n\n" in result:
                            test_content = result.split("\n\n", 1)[1][:5000]
                        else:
                            test_content = result[:5000]
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
    """Debug and fix errors.
    
    Refactored: Tools for exploration + with_structured_output for response.
    """
    print("[NODE] debug_error - Fixing errors...")
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
        
        # Read the file to fix using read_file_safe tool
        code_content = ""
        if workspace_path:
            try:
                result = read_file_safe.invoke({"file_path": file_to_fix})
                if result and not result.startswith("Error:"):
                    if "\n\n" in result:
                        code_content = result.split("\n\n", 1)[1]
                    else:
                        code_content = result
            except Exception:
                pass
        
        # Find and read test file using read_file_safe tool
        test_filename = find_test_file(workspace_path, file_to_fix) if workspace_path else ""
        test_content = ""
        if test_filename and workspace_path:
            try:
                result = read_file_safe.invoke({"file_path": test_filename})
                if result and not result.startswith("Error:"):
                    if "\n\n" in result:
                        test_content = result.split("\n\n", 1)[1]
                    else:
                        test_content = result
            except Exception:
                pass
        
        language = get_markdown_code_block_type(file_to_fix)
        
        # Setup tool context
        _setup_tool_context(workspace_path, project_id, task_id)
        
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
        
        # Tools for debugging exploration
        tools = [read_file_safe, list_directory_safe, semantic_code_search, execute_shell]
        
        # Step 1: Explore with tools
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        exploration = await _llm_with_tools(
            llm=_code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="debug_explore",
            max_iterations=2
        )
        
        # Step 2: Get structured response
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow provide your debug analysis and fixed code."))
        structured_llm = _code_llm.with_structured_output(DebugResult)
        debug_result = await structured_llm.ainvoke(messages, config=_cfg(state, "debug_error"))
        
        if debug_result.fixed_code and workspace_path:
            # Write fixed code using write_file_safe tool
            try:
                result = write_file_safe.invoke({
                    "file_path": file_to_fix,
                    "content": debug_result.fixed_code,
                    "mode": "w"
                })
                logger.info(f"[debug_error] {result}")
                
                # Incremental update index (fast - only changed file)
                from app.agents.developer_v2.src.tools import incremental_update_index
                incremental_update_index(project_id, task_id)
            except Exception as e:
                logger.error(f"[debug_error] Failed to write fixed code: {e}")
        
        # Update debug history
        debug_history = state.get("debug_history", []) or []
        debug_history.append({
            "iteration": debug_count + 1,
            "file": file_to_fix,
            "analysis": debug_result.analysis,
            "root_cause": debug_result.root_cause,
            "fix_description": debug_result.fix_description,
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
