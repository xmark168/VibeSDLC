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


async def router(state: DeveloperState, agent=None) -> DeveloperState:
    """Route story to appropriate processing node."""
    try:
        has_analysis = bool(state.get("analysis_result"))
        has_plan = bool(state.get("implementation_plan"))
        has_implementation = bool(state.get("code_changes"))
        
        sys_prompt = _build_system_prompt("routing_decision", agent)
        user_prompt = _get_prompt("routing_decision", "user_prompt").format(
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
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
        
        logger.info(f"[router] Decision: action={decision.action}, type={decision.task_type}, complexity={decision.complexity}")
        
        return {
            **state,
            "action": decision.action,
            "task_type": decision.task_type,
            "complexity": decision.complexity,
            "message": decision.message,
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


async def analyze(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze user story to understand scope and requirements."""
    try:
        if agent:
            await agent.message_user("status", f"🔍 Đang phân tích story: {state.get('story_title', 'Story')}...")
        
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
            await agent.message_user("response", msg)
        
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


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Create implementation plan from analysis."""
    try:
        analysis = state.get("analysis_result", {})
        
        if agent:
            await agent.message_user("status", "📝 Đang tạo implementation plan...")
        
        sys_prompt = _build_system_prompt("create_plan", agent)
        user_prompt = _get_prompt("create_plan", "user_prompt").format(
            analysis_summary=analysis.get("summary", ""),
            task_type=state.get("task_type", "feature"),
            complexity=state.get("complexity", "medium"),
            affected_files=", ".join(state.get("affected_files", [])),
            acceptance_criteria="\n".join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
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
            await agent.message_user("response", msg)
        
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
    """Execute implementation based on plan."""
    try:
        plan_steps = state.get("implementation_plan", [])
        current_step = state.get("current_step", 0)
        
        if not plan_steps:
            return {
                **state,
                "message": "❌ Không có implementation plan",
                "action": "PLAN",
            }
        
        if current_step >= len(plan_steps):
            if agent:
                await agent.message_user("response", "✅ Implementation hoàn tất! Chuyển sang validation...")
            return {
                **state,
                "message": "Implementation hoàn tất",
                "action": "VALIDATE",
            }
        
        step = plan_steps[current_step]
        
        if agent:
            await agent.message_user("status", f"⚙️ Step {current_step + 1}/{len(plan_steps)}: {step.get('description', '')}")
        
        sys_prompt = _build_system_prompt("implement_step", agent)
        user_prompt = _get_prompt("implement_step", "user_prompt").format(
            step_number=current_step + 1,
            total_steps=len(plan_steps),
            step_description=step.get("description", ""),
            file_path=step.get("file_path", ""),
            action=step.get("action", "modify"),
            story_summary=state.get("analysis_result", {}).get("summary", ""),
            completed_steps=current_step,
            existing_code="",
        )
        
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await _code_llm.ainvoke(messages, config=_cfg(state, "implement"))
        clean_json = _clean_json(response.content)
        code_change = CodeChange.model_validate_json(clean_json)
        
        logger.info(f"[implement] Step {current_step + 1}: {code_change.action} {code_change.file_path}")
        
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
            await agent.message_user("response", msg)
        
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
            await agent.message_user("status", "🧪 Đang validate implementation...")
        
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
            await agent.message_user("response", msg)
        
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
            await agent.message_user("response", question)
        
        return {
            **state,
            "message": question,
            "action": "CLARIFY",
        }
        
    except Exception as e:
        logger.error(f"[clarify] Error: {e}", exc_info=True)
        default_msg = "🤔 Mình cần thêm thông tin về story này. Bạn có thể mô tả chi tiết hơn không?"
        if agent:
            await agent.message_user("response", default_msg)
        return {
            **state,
            "message": default_msg,
            "action": "CLARIFY",
        }


async def respond(state: DeveloperState, agent=None) -> DeveloperState:
    """Send final response to user."""
    msg = state.get("message", "Task completed.")
    
    if agent and msg:
        await agent.message_user("response", msg)
    
    return {**state, "action": "RESPOND"}
