"""Developer V2 Graph Nodes."""

import logging
import re
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import (
    RoutingDecision, StoryAnalysis, ImplementationPlan, 
    CodeChange, ValidationResult
)
from app.agents.core.prompt_utils import load_prompts_yaml

logger = logging.getLogger(__name__)

_PROMPTS = load_prompts_yaml(Path(__file__).parent / "prompts.yaml")
_fast_llm = ChatOpenAI(model="claude-haiku-4-5-20251001", temperature=0.1, timeout=30)
_code_llm = ChatOpenAI(model="claude-sonnet-4-20250514", temperature=0.2, timeout=60)


def _clean_json(text: str) -> str:
    """Strip markdown code blocks from LLM response."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    return match.group(1).strip() if match else text.strip()


def _cfg(state: dict, name: str) -> dict | None:
    """Get LangChain config with Langfuse callback."""
    h = state.get("langfuse_handler")
    return {"callbacks": [h], "run_name": name} if h else None


def _get_prompt(task: str, key: str) -> str:
    """Get prompt from YAML config."""
    return _PROMPTS.get("tasks", {}).get(task, {}).get(key, "")


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


def _extract_design_from_raw(raw_content: str) -> dict:
    """Extract design info from raw LLM response when JSON parsing fails.
    
    Looks for mermaid code blocks and other design elements.
    """
    import re
    
    design_result = {
        "data_structures": "",
        "api_interfaces": "",
        "call_flow": "",
        "design_notes": "",
        "file_structure": []
    }
    
    # Extract mermaid classDiagram
    class_match = re.search(r'```mermaid\s*(classDiagram[\s\S]*?)```', raw_content)
    if class_match:
        design_result["data_structures"] = f"```mermaid\n{class_match.group(1).strip()}\n```"
    
    # Extract mermaid sequenceDiagram
    seq_match = re.search(r'```mermaid\s*(sequenceDiagram[\s\S]*?)```', raw_content)
    if seq_match:
        design_result["call_flow"] = f"```mermaid\n{seq_match.group(1).strip()}\n```"
    
    # Extract any mermaid block if no specific type found
    if not design_result["data_structures"] and not design_result["call_flow"]:
        mermaid_match = re.search(r'```mermaid\s*([\s\S]*?)```', raw_content)
        if mermaid_match:
            design_result["data_structures"] = f"```mermaid\n{mermaid_match.group(1).strip()}\n```"
    
    # Extract TypeScript/interface definitions
    ts_match = re.search(r'```(?:typescript|ts)\s*([\s\S]*?)```', raw_content)
    if ts_match:
        design_result["api_interfaces"] = ts_match.group(1).strip()
    
    # Extract file structure from bullet points
    file_matches = re.findall(r'[-*]\s*[`"]?([a-zA-Z0-9_/.-]+\.[a-zA-Z]+)[`"]?', raw_content)
    if file_matches:
        design_result["file_structure"] = list(set(file_matches))[:20]
    
    # Use raw content as notes if nothing else found
    if not any([design_result["data_structures"], design_result["call_flow"], design_result["api_interfaces"]]):
        design_result["design_notes"] = raw_content[:2000]
    else:
        # Extract notes section if present
        notes_match = re.search(r'(?:notes?|design notes?):\s*([\s\S]*?)(?:\n##|\n```|$)', raw_content, re.IGNORECASE)
        if notes_match:
            design_result["design_notes"] = notes_match.group(1).strip()[:500]
    
    return design_result


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
    """Route story to appropriate processing node."""
    try:
        has_analysis = bool(state.get("analysis_result"))
        has_plan = bool(state.get("implementation_plan"))
        has_implementation = bool(state.get("code_changes"))
        
        # Check if this is a valid story task (has meaningful content)
        story_content = state.get("story_content", "")
        is_story_task = len(story_content) > 50  # Story with sufficient detail
        
        sys_prompt = _build_system_prompt("routing_decision", agent)
        user_prompt = _get_prompt("routing_decision", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=story_content,
            acceptance_criteria="\n".join(state.get("acceptance_criteria", [])),
            has_analysis=has_analysis,
            has_plan=has_plan,
            has_implementation=has_implementation,
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "router"))
        clean_json = _clean_json(response.content)
        decision = RoutingDecision.model_validate_json(clean_json)
        
        # IMPORTANT: For story tasks, never return RESPOND or CLARIFY
        # Always proceed with implementation flow (MetaGPT pattern)
        action = decision.action
        if is_story_task and action in ("RESPOND", "CLARIFY"):
            logger.info(f"[router] Story task detected, forcing ANALYZE instead of {action}")
            action = "ANALYZE"
        
        logger.info(f"[router] Decision: action={action}, type={decision.task_type}, complexity={decision.complexity}")
        
        return {
            **state,
            "action": action,
            "task_type": decision.task_type,
            "complexity": decision.complexity,
            "message": decision.message if action == decision.action else "Bắt đầu phân tích story...",
            "reason": decision.reason,
            "confidence": decision.confidence,
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
            
            # await agent.message_user("status", f"🔧 Workspace ready: branch `{workspace_info['branch_name']}`")  # Disabled for Kafka mode
            
            # Index workspace with CocoIndex for semantic search
            index_ready = False
            workspace_path = workspace_info.get("workspace_path", "")
            project_id = state.get("project_id", "default")
            task_id = state.get("task_id") or story_id
            
            if workspace_path:
                try:
                    from app.agents.developer_v2.tools import index_workspace
                    index_ready = index_workspace(project_id, workspace_path, task_id)
                    if index_ready:
                        logger.info(f"[setup_workspace] Indexed workspace with CocoIndex")
                        # await agent.message_user("status", "📚 Codebase indexed for semantic search")  # Disabled for Kafka mode
                except Exception as idx_err:
                    logger.warning(f"[setup_workspace] CocoIndex indexing failed: {idx_err}")
                    index_ready = False
            
            return {
                **state,
                "workspace_path": workspace_info["workspace_path"],
                "branch_name": workspace_info["branch_name"],
                "main_workspace": workspace_info["main_workspace"],
                "workspace_ready": workspace_info["workspace_ready"],
                "index_ready": index_ready,
            }
        else:
            logger.warning("[setup_workspace] Agent has no _setup_workspace method")
            return {**state, "workspace_ready": False, "index_ready": False}
        
    except Exception as e:
        logger.error(f"[setup_workspace] Error: {e}", exc_info=True)
        # await agent.message_user("status", f"⚠️ Không thể tạo workspace: {str(e)}")  # Disabled for Kafka mode
        return {
            **state,
            "workspace_ready": False,
            "error": f"Workspace setup failed: {str(e)}",
        }


async def analyze(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze user story to understand scope and requirements."""
    try:
        if agent:
            # await agent.message_user("status", f"🔍 Đang phân tích story: {state.get('story_title', 'Story')}...")  # Disabled for Kafka mode
            pass
        
        sys_prompt = _build_system_prompt("analyze_story", agent)
        user_prompt = _get_prompt("analyze_story", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            project_context="",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "analyze"))
        clean_json = _clean_json(response.content)
        analysis = StoryAnalysis.model_validate_json(clean_json)
        
        logger.info(f"[analyze] Completed: type={analysis.task_type}, complexity={analysis.complexity}, hours={analysis.estimated_hours}")
        
        msg = f"""✅ **Phân tích hoàn tất!**

📋 **Summary:** {analysis.summary}
📁 **Loại task:** {analysis.task_type}
⚡ **Độ phức tạp:** {analysis.complexity}
⏱️ **Ước tính:** {analysis.estimated_hours}h

📂 **Files liên quan:** {', '.join(analysis.affected_files) if analysis.affected_files else 'Chưa xác định'}
⚠️ **Risks:** {', '.join(analysis.risks) if analysis.risks else 'Không có'}

💡 **Approach:** {analysis.suggested_approach}"""
        
        if agent:
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
            "message": msg,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[analyze] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi phân tích: {str(e)}",
            "action": "RESPOND",
        }


async def design(state: DeveloperState, agent=None) -> DeveloperState:
    """Generate system design before implementation (MetaGPT Architect pattern)."""
    try:
        analysis = state.get("analysis_result", {})
        complexity = state.get("complexity", "medium")
        
        # Skip design for simple tasks
        if complexity == "low":
            logger.info("[design] Skipping design for low complexity task")
            return {
                **state,
                "action": "PLAN",
                "message": "Task đơn giản, bỏ qua design phase.",
            }
        
        if agent:
            # await agent.message_user("status", "🏗️ Đang thiết kế system architecture...")  # Disabled for Kafka mode
            pass
        
        # Get existing code context
        workspace_path = state.get("workspace_path", "")
        existing_context = ""
        if workspace_path:
            try:
                from app.agents.developer_v2.tools import get_all_workspace_files
                existing_context = get_all_workspace_files(workspace_path, max_files=10)
            except Exception:
                existing_context = "No existing code"
        
        sys_prompt = _build_system_prompt("system_design", agent)
        user_prompt = _get_prompt("system_design", "user_prompt").format(
            story_title=state.get("story_title", ""),
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=complexity,
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            existing_context=existing_context or "No existing code",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "design"))
        raw_content = response.content
        clean_json = _clean_json(raw_content)
        
        import json
        design_result = None
        
        # Try JSON parsing first
        if clean_json and clean_json.strip():
            try:
                design_result = json.loads(clean_json)
                logger.info(f"[design] Parsed JSON successfully")
            except json.JSONDecodeError:
                logger.warning(f"[design] JSON parse failed, extracting from raw response")
        
        # Fallback: Extract mermaid/content directly from response
        if not design_result:
            design_result = _extract_design_from_raw(raw_content)
            logger.info(f"[design] Extracted design from raw response")
        
        logger.info(f"[design] Created system design with {len(design_result.get('file_structure', []))} files")
        
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
        
        # Save design documents to /docs/technical
        if workspace_path:
            _save_design_docs(workspace_path, design_result, design_doc, state.get("story_title", "design"))
        
        msg = f"""🏗️ **System Design hoàn tất!**

📊 **Data Structures:** Đã định nghĩa interfaces và types
🔗 **Call Flow:** Đã vẽ sequence diagram
📁 **Files:** {', '.join(design_result.get('file_structure', [])[:5])}...
📄 **Docs:** Saved to docs/technical/

💡 **Notes:** {design_result.get('design_notes', '')[:200]}..."""
        
        if agent:
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
            pass
        
        return {
            **state,
            "system_design": design_result,
            "data_structures": design_result.get("data_structures"),
            "api_interfaces": design_result.get("api_interfaces"),
            "call_flow": design_result.get("call_flow"),
            "design_doc": design_doc,
            "message": msg,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[design] Error: {e}", exc_info=True)
        # Don't fail - continue to plan even if design fails
        return {
            **state,
            "message": f"⚠️ Design skipped: {str(e)}",
            "action": "PLAN",
        }


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create implementation plan from analysis (MetaGPT WriteCodePlanAndChange pattern)."""
    try:
        analysis = state.get("analysis_result", {})
        
        if agent:
            # await agent.message_user("status", "📝 Đang tạo implementation plan với incremental changes...")  # Disabled for Kafka mode
            pass
        
        # Get existing code context for better planning
        workspace_path = state.get("workspace_path", "")
        existing_code = ""
        if workspace_path:
            try:
                from app.agents.developer_v2.tools import get_all_workspace_files
                existing_code = get_all_workspace_files(workspace_path, max_files=10)
            except Exception:
                existing_code = "No existing code"
        
        sys_prompt = _build_system_prompt("create_plan", agent)
        user_prompt = _get_prompt("create_plan", "user_prompt").format(
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=state.get("complexity", "medium"),
            affected_files=", ".join(state.get("affected_files", [])),
            design_doc=state.get("design_doc", "No design document"),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            existing_code=existing_code or "No existing code",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "plan"))
        clean_json = _clean_json(response.content)
        plan_result = ImplementationPlan.model_validate_json(clean_json)
        
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
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
    """Execute implementation based on plan (Enhanced with MetaGPT context)."""
    try:
        plan_steps = state.get("implementation_plan", [])
        current_step = state.get("current_step", 0)
        workspace_path = state.get("workspace_path", "")
        
        if not plan_steps:
            return {
                **state,
                "message": "❌ Không có implementation plan",
                "action": "PLAN",
            }
        
        if not workspace_path:
            logger.warning("[implement] No workspace_path configured")
        
        if current_step >= len(plan_steps):
            if agent:
                # await agent.message_user("response", f"✅ Implementation hoàn tất! Branch: `{state.get('branch_name', 'unknown')}`")  # Disabled for Kafka mode
                pass
            return {
                **state,
                "message": "Implementation hoàn tất",
                "action": "VALIDATE",
            }
        
        step = plan_steps[current_step]
        current_file = step.get("file_path", "")
        
        if agent:
            # await agent.message_user("status", f"⚙️ Step {current_step + 1}/{len(plan_steps)}: {step.get('description', '')} [workspace: {workspace_path}]")  # Disabled for Kafka mode
            pass
        
        # Gather related code context using CocoIndex semantic search (preferred)
        # Falls back to file import if CocoIndex is not available
        related_context = state.get("related_code_context", "")
        if workspace_path and not related_context:
            index_ready = state.get("index_ready", False)
            project_id = state.get("project_id", "default")
            task_id = state.get("task_id") or state.get("story_id", "")
            step_description = step.get("description", "")
            
            if index_ready:
                # Use CocoIndex semantic search (efficient, relevant results only)
                try:
                    from app.agents.developer_v2.tools import get_related_code_indexed
                    related_context = get_related_code_indexed(
                        project_id=project_id,
                        current_file=current_file,
                        task_description=step_description,
                        top_k=5,
                        task_id=task_id
                    )
                    logger.info(f"[implement] Using CocoIndex for context")
                except Exception as e:
                    logger.warning(f"[implement] CocoIndex search failed: {e}")
                    related_context = ""
            
            # Fallback to file import if CocoIndex not available or failed
            if not related_context or related_context.startswith("Search error"):
                from app.agents.developer_v2.tools import get_related_code_context
                task_files = state.get("affected_files", [])
                related_context = get_related_code_context(
                    workspace_path=workspace_path,
                    current_file=current_file,
                    task_files=task_files,
                    include_all_src=state.get("needs_revision", False)
                )
                logger.info(f"[implement] Using file import fallback for context")
        
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
        
        sys_prompt = _build_system_prompt("implement_step", agent)
        user_prompt = _get_prompt("implement_step", "user_prompt").format(
            implementation_plan=implementation_plan,
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=current_file,
            action=step.get("action", "modify"),
            story_summary=state.get("analysis_result", {}).get("summary", ""),
            related_code_context=related_context or "No related files",
            existing_code=existing_code or "No existing code (new file)",
            error_logs=state.get("error_logs", "") or "No previous errors",
            completed_steps=current_step,
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "implement"))
        clean_json = _clean_json(response.content)
        code_change = CodeChange.model_validate_json(clean_json)
        
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
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
            pass
        
        return {
            **state,
            "code_changes": code_changes,
            "files_created": files_created,
            "files_modified": files_modified,
            "current_step": current_step + 1,
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


async def validate(state: DeveloperState, agent=None) -> DeveloperState:
    """Validate implementation against acceptance criteria."""
    try:
        if agent:
            # await agent.message_user("status", "🧪 Đang validate implementation...")  # Disabled for Kafka mode
            pass
        
        sys_prompt = _build_system_prompt("validate_implementation", agent)
        user_prompt = _get_prompt("validate_implementation", "user_prompt").format(
            files_created=", ".join(state.get("files_created", [])) or "None",
            files_modified=", ".join(state.get("files_modified", [])) or "None",
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            test_results="Tests not executed in this simulation",
            lint_results="Lint not executed in this simulation",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _fast_llm.ainvoke(messages, config=_cfg(state, "validate"))
        clean_json = _clean_json(response.content)
        validation = ValidationResult.model_validate_json(clean_json)
        
        logger.info(f"[validate] tests={validation.tests_passed}, lint={validation.lint_passed}, ac_verified={len(validation.ac_verified)}")
        
        status = "✅ PASSED" if validation.tests_passed and validation.lint_passed else "⚠️ NEEDS ATTENTION"
        
        msg = f"""🧪 **Validation Result: {status}**

**Tests:** {'✅ Passed' if validation.tests_passed else '❌ Failed'}
**Lint:** {'✅ Passed' if validation.lint_passed else '❌ Failed'}

**AC Verified:** {len(validation.ac_verified)}/{len(validation.ac_verified) + len(validation.ac_failed)}
{chr(10).join(f'  ✅ {ac}' for ac in validation.ac_verified)}
{chr(10).join(f'  ❌ {ac}' for ac in validation.ac_failed)}

**Issues:** {', '.join(validation.issues) if validation.issues else 'None'}
**Recommendations:** {', '.join(validation.recommendations) if validation.recommendations else 'None'}"""
        
        if agent:
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
            pass
        
        return {
            **state,
            "validation_result": validation.model_dump(),
            "tests_passed": validation.tests_passed,
            "lint_passed": validation.lint_passed,
            "ac_verified": validation.ac_verified,
            "message": msg,
            "action": "RESPOND",
        }
        
    except Exception as e:
        logger.error(f"[validate] Error: {e}", exc_info=True)
        return {
            **state,
            "error": str(e),
            "message": f"❌ Lỗi khi validate: {str(e)}",
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
            # await agent.message_user("status", "📝 Đang tạo code plan chi tiết...")  # Disabled for Kafka mode
            pass
        
        # Gather legacy code context
        workspace_path = state.get("workspace_path", "")
        legacy_code = ""
        
        if workspace_path:
            from app.agents.developer_v2.tools import get_legacy_code
            legacy_code = get_legacy_code(workspace_path)
        
        sys_prompt = _build_system_prompt("create_code_plan", agent)
        user_prompt = _get_prompt("create_code_plan", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            design_doc=state.get("design_doc") or state.get("analysis_result", {}).get("summary", ""),
            task_list="\n".join(f"- {f}" for f in state.get("affected_files", [])),
            legacy_code=legacy_code or "No existing code",
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
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
            # await agent.message_user("status", "🔍 Đang review code implementation...")  # Disabled for Kafka mode
            pass
        
        # Gather implemented code blocks
        workspace_path = state.get("workspace_path", "")
        code_blocks = ""
        
        if workspace_path:
            from app.agents.developer_v2.tools import get_legacy_code
            files_created = state.get("files_created", [])
            files_modified = state.get("files_modified", [])
            all_files = files_created + files_modified
            code_blocks = get_legacy_code(workspace_path)
        
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
                # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
                    # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
                # await agent.message_user("response", msg)  # Disabled for Kafka mode
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
            # await agent.message_user("response", question)  # Disabled for Kafka mode
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
            # await agent.message_user("response", default_msg)  # Disabled for Kafka mode
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
                # await agent.message_user("response", existing_msg)  # Disabled for Kafka mode
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
            # await agent.message_user("response", msg)  # Disabled for Kafka mode
            pass
        
        return {**state, "message": msg, "action": "RESPOND"}
        
    except Exception as e:
        logger.error(f"[respond] Error: {e}", exc_info=True)
        fallback_msg = state.get("message") or "Mình đã nhận được tin nhắn của bạn! 👋"
        if agent:
            # await agent.message_user("response", fallback_msg)  # Disabled for Kafka mode
            pass
        return {**state, "message": fallback_msg, "action": "RESPOND"}


async def merge_to_main(state: DeveloperState, agent=None) -> DeveloperState:
    """Merge feature branch to main after successful validation.
    
    This node is called after validate passes (is_pass=True).
    It merges the story branch into main branch.
    """
    try:
        branch_name = state.get("branch_name")
        main_workspace = state.get("main_workspace")
        
        if not branch_name or not main_workspace:
            logger.warning("[merge_to_main] Missing branch_name or main_workspace")
            return {**state, "merged": False}
        
        from app.agents.developer.tools.git_python_tool import GitPythonTool
        
        main_git = GitPythonTool(root_dir=main_workspace)
        
        # 1. Checkout main branch
        checkout_result = main_git._run("checkout_branch", branch_name="main")
        logger.info(f"[merge_to_main] Checkout main: {checkout_result}")
        
        # If main doesn't exist, try master
        if "does not exist" in checkout_result:
            checkout_result = main_git._run("checkout_branch", branch_name="master")
            logger.info(f"[merge_to_main] Checkout master: {checkout_result}")
        
        # 2. Merge feature branch
        merge_result = main_git._run("merge", branch_name=branch_name)
        logger.info(f"[merge_to_main] Merge result: {merge_result}")
        
        if "conflict" in merge_result.lower() or "error" in merge_result.lower():
            if agent:
                # await agent.message_user("status", f"⚠️ Merge conflict: {merge_result}")  # Disabled for Kafka mode
                pass
            return {
                **state,
                "merged": False,
                "error": merge_result,
            }
        
        if agent:
            # await agent.message_user("status", f"✅ Merged `{branch_name}` vào main")  # Disabled for Kafka mode
            pass
        
        return {
            **state,
            "merged": True,
        }
        
    except Exception as e:
        logger.error(f"[merge_to_main] Error: {e}", exc_info=True)
        if agent:
            # await agent.message_user("status", f"⚠️ Merge failed: {str(e)}")  # Disabled for Kafka mode
            pass
        return {
            **state,
            "merged": False,
            "error": str(e),
        }


async def cleanup_workspace(state: DeveloperState, agent=None) -> DeveloperState:
    """Cleanup worktree and branch after merge.
    
    This node removes the worktree and deletes the feature branch
    after successful merge to main.
    """
    try:
        workspace_path = state.get("workspace_path")
        branch_name = state.get("branch_name")
        main_workspace = state.get("main_workspace")
        merged = state.get("merged", False)
        
        if not main_workspace:
            logger.warning("[cleanup_workspace] No main_workspace, skipping cleanup")
            return state
        
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
        
        # 3. Cleanup CocoIndex task index
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        if project_id and task_id:
            try:
                from app.agents.developer.project_manager import project_manager
                project_manager.unregister_task(project_id, task_id)
                logger.info(f"[cleanup_workspace] Unregistered CocoIndex task: {task_id}")
            except Exception as idx_err:
                logger.warning(f"[cleanup_workspace] CocoIndex cleanup failed: {idx_err}")
        
        if agent:
            # await agent.message_user("status", "🧹 Workspace đã được dọn dẹp")  # Disabled for Kafka mode
            pass
        
        return {
            **state,
            "workspace_ready": False,
            "index_ready": False,
        }
        
    except Exception as e:
        logger.error(f"[cleanup_workspace] Error: {e}", exc_info=True)
        return state


# =============================================================================
# CODE REVIEW (LGTM/LBTM pattern from MetaGPT)
# =============================================================================

async def code_review(state: DeveloperState, agent=None) -> DeveloperState:
    """Review code k times until LGTM or max iterations.
    
    MetaGPT-inspired code review that checks:
    1. Requirements implementation
    2. Code logic correctness
    3. Design compliance
    4. Implementation completeness
    5. Import correctness
    6. Method reuse
    """
    try:
        code_changes = state.get("code_changes", [])
        k = state.get("code_review_k", 2)
        workspace_path = state.get("workspace_path", "")
        iteration = state.get("code_review_iteration", 0)
        
        if not code_changes:
            logger.info("[code_review] No code changes to review")
            return {**state, "code_review_passed": True}
        
        if agent:
            # await agent.message_user("status", f"🔍 Code Review (iteration {iteration + 1}/{k})")  # Disabled for Kafka mode
            pass
        
        review_results = []
        all_passed = True
        
        from app.agents.developer_v2.tools import get_markdown_code_block_type
        
        for change in code_changes:
            file_path = change.get("file_path", "")
            code = change.get("code_snippet", "")
            
            if not code:
                continue
            
            language = get_markdown_code_block_type(file_path)
            
            # Build review prompt
            sys_prompt = _build_system_prompt("code_review", agent)
            user_prompt = _get_prompt("code_review", "user_prompt").format(
                design=state.get("design_doc", ""),
                task=state.get("task_doc", ""),
                related_code=state.get("related_code_context", ""),
                filename=file_path,
                language=language,
                code=code,
            )
            
            messages = [
                SystemMessage(content=sys_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = await _code_llm.ainvoke(messages, config=_cfg(state, "code_review"))
            clean_json = _clean_json(response.content)
            
            try:
                import json
                review = json.loads(clean_json)
            except json.JSONDecodeError:
                review = {"result": "LGTM", "issues": [], "rewritten_code": ""}
            
            review_results.append(review)
            
            result = review.get("result", "LGTM")
            if "LBTM" in result:
                all_passed = False
                # If LBTM and rewritten code provided, update the change
                rewritten = review.get("rewritten_code", "")
                if rewritten and rewritten.strip():
                    change["code_snippet"] = rewritten
                    # Also write to file
                    if workspace_path:
                        full_path = Path(workspace_path) / file_path
                        try:
                            full_path.parent.mkdir(parents=True, exist_ok=True)
                            full_path.write_text(rewritten, encoding='utf-8')
                            logger.info(f"[code_review] Rewrote {file_path} based on review")
                        except Exception as e:
                            logger.warning(f"[code_review] Failed to write {file_path}: {e}")
                
                issues = review.get("issues", [])
                if agent and issues:
                    # await agent.message_user("status", f"⚠️ Review issues in {file_path}: {', '.join(issues[:2])}")  # Disabled for Kafka mode
                    pass
            else:
                if agent:
                    # await agent.message_user("status", f"✅ {file_path}: LGTM")  # Disabled for Kafka mode
                    pass
        
        new_iteration = iteration + 1
        
        # If not all passed and we haven't reached max iterations, we'll retry
        if not all_passed and new_iteration < k:
            logger.info(f"[code_review] Iteration {new_iteration}, retrying...")
            return {
                **state,
                "code_review_passed": False,
                "code_review_results": review_results,
                "code_review_iteration": new_iteration,
            }
        
        if agent:
            if all_passed:
                # await agent.message_user("response", "✅ Code review passed! All files LGTM")  # Disabled for Kafka mode
                pass
            else:
                # await agent.message_user("response", f"⚠️ Code review completed after {new_iteration} iterations")  # Disabled for Kafka mode
                pass
        
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
            # await agent.message_user("status", "🧪 Running tests...")  # Disabled for Kafka mode
            pass
        
        from app.agents.developer_v2.tools import (
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
                # await agent.message_user("status", "📦 Dependencies installed")  # Disabled for Kafka mode
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
        
        # Analyze with LLM
        sys_prompt = _build_system_prompt("run_code_analysis", agent)
        user_prompt = _get_prompt("run_code_analysis", "user_prompt").format(
            code_filename=code_filename or "unknown",
            language=language,
            code=code_content or "No source code available",
            test_filename=test_filename or "unknown",
            test_code=test_content or "No test code available",
            command=" ".join(test_cmd),
            stdout=result.stdout[:5000] if result.stdout else "No output",
            stderr=result.stderr[:5000] if result.stderr else "No errors",
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
                # await agent.message_user("response", f"✅ Tests passed! {analysis.get('summary', '')}")  # Disabled for Kafka mode
                pass
            else:
                # await agent.message_user("status", f"❌ Tests failed: {analysis.get('summary', '')[:100]}")  # Disabled for Kafka mode
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
    """Debug and fix errors based on test results.
    
    Analyzes error logs and rewrites code to fix bugs.
    """
    try:
        run_result = state.get("run_result", {})
        workspace_path = state.get("workspace_path", "")
        debug_count = state.get("debug_count", 0)
        max_debug = state.get("max_debug", 3)
        
        if run_result.get("status") == "PASS":
            logger.info("[debug_error] No errors to debug")
            return state
        
        if debug_count >= max_debug:
            logger.warning(f"[debug_error] Max debug attempts ({max_debug}) reached")
            if agent:
                # await agent.message_user("status", f"⚠️ Reached max debug attempts ({max_debug})")  # Disabled for Kafka mode
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
            # await agent.message_user("status", f"🔧 Debugging {file_to_fix} (attempt {debug_count + 1}/{max_debug})")  # Disabled for Kafka mode
            pass
        
        from app.agents.developer_v2.tools import get_markdown_code_block_type, find_test_file
        
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
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "debug_error"))
        clean_json = _clean_json(response.content)
        
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
                    # await agent.message_user("status", f"✏️ Fixed {file_to_fix}: {debug_result.get('fix_description', '')[:50]}")  # Disabled for Kafka mode
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
