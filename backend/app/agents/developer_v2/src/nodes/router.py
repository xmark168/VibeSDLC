"""Router node - Route story to appropriate processing node."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import RoutingDecision
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import fast_llm

logger = logging.getLogger(__name__)


async def router(state: DeveloperState, agent=None) -> DeveloperState:
    """Route story to appropriate processing node."""
    print("[NODE] router")
    try:
        has_analysis = bool(state.get("analysis_result"))
        has_plan = bool(state.get("implementation_plan"))
        has_implementation = bool(state.get("code_changes"))
        
        story_content = state.get("story_content", "")
        is_story_task = len(story_content) > 50
        
        # FAST PATH: Skip LLM for obvious story tasks (save tokens)
        if is_story_task and not has_analysis:
            logger.info("[router] Fast path: story task without analysis -> ANALYZE")
            return {
                **state,
                "action": "ANALYZE",
                "task_type": "feature",
                "complexity": "medium",
                "message": "Bắt đầu phân tích story...",
                "reason": "Story task detected, skipping to analyze",
                "confidence": 0.9,
            }
        
        input_text = _format_input_template(
            "routing_decision",
            story_title=state.get("story_title", "Untitled"),
            story_content=story_content,
            acceptance_criteria=chr(10).join(state.get("acceptance_criteria", [])),
            has_analysis=has_analysis,
            has_plan=has_plan,
            has_implementation=has_implementation
        )

        messages = [
            SystemMessage(content=_build_system_prompt("routing_decision")),
            HumanMessage(content=input_text)
        ]
        
        structured_llm = fast_llm.with_structured_output(RoutingDecision)
        result = await structured_llm.ainvoke(messages, config=_cfg(state, "router"))
        
        action = result.action
        task_type = result.task_type
        complexity = result.complexity
        message = result.message
        reason = result.reason
        confidence = result.confidence
        
        if is_story_task:
            if action in ("RESPOND", "CLARIFY"):
                logger.info(f"[router] Story task detected, forcing ANALYZE instead of {action}")
                action = "ANALYZE"
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
