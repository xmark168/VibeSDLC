"""Implement node - Execute implementation step by step."""
import logging
import os
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import CodeChange
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, write_file_safe, list_directory_safe
from app.agents.developer_v2.src.tools.shell_tools import semantic_code_search
from app.agents.developer_v2.src.tools import get_related_code_indexed, get_boilerplate_examples
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context, build_static_context

logger = logging.getLogger(__name__)


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step by step."""
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    print(f"[NODE] implement {current_step + 1}/{total_steps}")
    try:
        plan_steps = state.get("implementation_plan", [])
        current_step = state.get("current_step", 0)
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        
        react_loop_count = state.get("react_loop_count", 0)
        debug_count = state.get("debug_count", 0)
        summarize_feedback = state.get("summarize_feedback")
        run_status = state.get("run_status")
        
        if state.get("react_mode") and run_status == "FAIL":
            current_step = 0
            react_loop_count += 1
            debug_count = 0
            logger.info(f"[implement] React loop {react_loop_count} (from run_code FAIL, restarting from step 0)")
        elif state.get("react_mode") and current_step == 0 and summarize_feedback:
            react_loop_count += 1
            debug_count = 0
            logger.info(f"[implement] React loop {react_loop_count} (from summarize: {summarize_feedback[:100]}...)")
        
        if not plan_steps:
            logger.error("[implement] No implementation plan")
            return {**state, "error": "No implementation plan", "action": "RESPOND"}
        
        if current_step >= len(plan_steps):
            return {
                **state,
                "message": "Implementation hoàn tất",
                "action": "VALIDATE",
            }
        
        step = plan_steps[current_step]
        current_file = step.get("file_path") or ""
        
        # Gather related code context using CocoIndex
        related_context = state.get("related_code_context", "")
        if workspace_path and not related_context:
            index_ready = state.get("index_ready", False)
            step_description = step.get("description", "")
            
            if index_ready:
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
            try:
                result = read_file_safe.invoke({"file_path": current_file})
                if result and not result.startswith("Error:"):
                    if "\n\n" in result:
                        existing_code = result.split("\n\n", 1)[1]
                    else:
                        existing_code = result
            except Exception:
                pass
        
        implementation_plan = state.get("code_plan_doc") or ""
        if not implementation_plan:
            implementation_plan = "\n".join(
                f"{s.get('order', i+1)}. [{s.get('action')}] {s.get('description')}"
                for i, s in enumerate(plan_steps)
            )
        
        # Build context (pass current_file for smart section extraction)
        static_context = build_static_context(state, current_file)
        
        if workspace_path:
            task_type = "page"
            if "component" in current_file.lower():
                task_type = "component"
            elif "api" in current_file.lower() or "route" in current_file.lower():
                task_type = "api"
            elif "layout" in current_file.lower():
                task_type = "layout"
            
            boilerplate = get_boilerplate_examples(workspace_path, task_type)
            if boilerplate:
                static_context = f"{static_context}\n\n---\n\n{boilerplate}" if static_context else boilerplate
        
        dynamic_parts = []
        
        if related_context:
            dynamic_parts.append(f"## RELATED CODE\n{related_context}")
        
        research_context = state.get("research_context", "")
        if research_context:
            dynamic_parts.append(f"## Best Practices (from web research)\n{research_context[:1500]}")
        
        summarize_feedback = state.get("summarize_feedback", "")
        if summarize_feedback:
            dynamic_parts.append(f"## FEEDBACK FROM PREVIOUS ATTEMPT (MUST ADDRESS)\n{summarize_feedback}")
        
        dynamic_context = "\n\n---\n\n".join(dynamic_parts) if dynamic_parts else "No additional context"
        full_related_context = f"{static_context}\n\n{'='*60}\n\n{dynamic_context}" if static_context else dynamic_context
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        error_logs_text = f"Previous Errors:{chr(10)}{state.get('error_logs', '')}" if state.get('error_logs') else ""
        input_text = _format_input_template(
            "implement_step",
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=current_file,
            action=step.get("action", "modify"),
            story_summary=state.get("analysis_result", {}).get("summary", ""),
            related_context=full_related_context[:8000],
            existing_code=existing_code if existing_code else "No existing code (new file)",
            error_logs=error_logs_text
        )

        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        
        messages = [
            SystemMessage(content=_build_system_prompt("implement_step")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="implement_explore",
            max_iterations=2
        )
        
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:5000]}\n\nNow provide the code implementation."))
        structured_llm = code_llm.with_structured_output(CodeChange)
        code_change = await structured_llm.ainvoke(messages, config=_cfg(state, "implement"))
        
        if not code_change.file_path:
            code_change = CodeChange(
                file_path=current_file,
                action=code_change.action or step.get("action", "create"),
                code_snippet=code_change.code_snippet,
                description=code_change.description or step.get("description", "")
            )
        
        if code_change.file_path:
            code_change.file_path = code_change.file_path.replace("/", os.sep)
        
        logger.info(f"[implement] Got code from structured output")
        logger.info(f"[implement] Step {current_step + 1}: {code_change.action} {code_change.file_path}")
        
        if workspace_path and code_change.code_snippet and code_change.file_path:
            try:
                if code_change.action == "create":
                    # Create new file
                    result = write_file_safe.invoke({
                        "file_path": code_change.file_path,
                        "content": code_change.code_snippet,
                        "mode": "w"
                    })
                elif code_change.action == "modify":
                    if code_change.line_start:
                        # Line-based modify
                        existing = read_file_safe.invoke({"file_path": code_change.file_path})
                        if existing and not existing.startswith("Error:"):
                            # Remove metadata prefix
                            if "\n\n" in existing:
                                existing = existing.split("\n\n", 1)[1]
                            
                            lines = existing.split('\n')
                            total_lines = len(lines)
                            
                            if code_change.line_start > total_lines:
                                # Append at end
                                result = write_file_safe.invoke({
                                    "file_path": code_change.file_path,
                                    "content": code_change.code_snippet,
                                    "mode": "a"
                                })
                            else:
                                # Replace lines
                                start = code_change.line_start - 1
                                end = code_change.line_end if code_change.line_end else code_change.line_start
                                new_lines = lines[:start] + code_change.code_snippet.split('\n') + lines[end:]
                                result = write_file_safe.invoke({
                                    "file_path": code_change.file_path,
                                    "content": '\n'.join(new_lines),
                                    "mode": "w"
                                })
                        else:
                            # File doesn't exist, create it
                            result = write_file_safe.invoke({
                                "file_path": code_change.file_path,
                                "content": code_change.code_snippet,
                                "mode": "w"
                            })
                    else:
                        # No line numbers, write whole file
                        result = write_file_safe.invoke({
                            "file_path": code_change.file_path,
                            "content": code_change.code_snippet,
                            "mode": "w"
                        })
                else:
                    # Default: write whole file
                    result = write_file_safe.invoke({
                        "file_path": code_change.file_path,
                        "content": code_change.code_snippet,
                        "mode": "w"
                    })
                logger.info(f"[implement] {result}")
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
        
        return {
            **state,
            "code_changes": code_changes,
            "files_created": files_created,
            "files_modified": files_modified,
            "current_step": current_step + 1,
            "react_loop_count": react_loop_count,
            "debug_count": debug_count,
            "run_status": None,
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
