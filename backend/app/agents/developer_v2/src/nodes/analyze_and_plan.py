"""Analyze and Plan node - Combined analysis and planning with tool exploration."""
import os
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context
from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills import get_project_structure, get_plan_prompts
from app.agents.developer_v2.src.tools.filesystem_tools import (
    read_file_safe, list_directory_safe, glob, grep_files
)
from app.agents.developer_v2.src.tools.cocoindex_tools import search_codebase_tool

logger = logging.getLogger(__name__)


def _prefetch_context(workspace_path: str) -> str:
    """Pre-fetch project context without LLM calls."""
    if not workspace_path or not os.path.exists(workspace_path):
        return ""
    
    context_parts = []
    
    # Core files to always read
    core_files = [
        ("package.json", 500),
        ("prisma/schema.prisma", 1000),
        ("src/app/layout.tsx", 300),
    ]
    
    for file_path, max_len in core_files:
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:max_len]
                context_parts.append(f"# {file_path}\n{content}")
            except Exception:
                pass
    
    # List key directories
    for dir_name in ["src/app/api", "src/components", "src/lib"]:
        dir_path = os.path.join(workspace_path, dir_name)
        if os.path.exists(dir_path):
            try:
                files = os.listdir(dir_path)[:10]
                context_parts.append(f"# {dir_name}/\n{', '.join(files)}")
            except Exception:
                pass
    
    return "\n\n".join(context_parts)


async def analyze_and_plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Combined analyze + plan with tool exploration phase."""
    print("[NODE] analyze_and_plan")
    
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Pre-fetch context (quick, no LLM)
        project_context = _prefetch_context(workspace_path)
        project_structure = get_project_structure(tech_stack)
        
        # Load skill registry (for later use in implement)
        skill_registry = SkillRegistry.load(tech_stack)
        
        # Load prompts from plan_prompts.yaml
        plan_prompts = get_plan_prompts(tech_stack)
        system_prompt = f"{plan_prompts['system_prompt']}\n\n<project_structure>\n{project_structure}\n</project_structure>"
        
        # Format input from template
        requirements = state.get("story_requirements", [])
        req_text = chr(10).join(f"- {r}" for r in requirements)
        
        acceptance_criteria = state.get("acceptance_criteria", [])
        ac_text = chr(10).join(f"- {ac}" for ac in acceptance_criteria)
        
        input_text = plan_prompts["input_template"].format(
            story_id=state.get("story_id", ""),
            epic=state.get("epic", ""),
            story_title=state.get("story_title", "Untitled"),
            story_description=state.get("story_description", ""),
            story_requirements=req_text,
            acceptance_criteria=ac_text,
            project_context=project_context,
        )
        
        # Tools for exploration
        tools = [
            read_file_safe,
            list_directory_safe,
            glob,                # glob pattern search
            grep_files,          # text search in files
            search_codebase_tool,  # semantic search
        ]
        
        # Phase 1: Tool exploration
        explore_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text + "\n\nExplore the codebase to understand existing structure before planning.")
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=explore_messages,
            state=state,
            name="analyze_explore",
            max_iterations=12
        )
        
        # Phase 2: Generate plan with exploration context
        plan_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{input_text}\n\n<exploration_context>\n{exploration[:6000]}\n</exploration_context>\n\nNow create the implementation plan based on your exploration.")
        ]
        
        response = await code_llm.ainvoke(plan_messages, config=_cfg(state, "analyze_and_plan"))
        data = extract_json_universal(response.content, "analyze_and_plan")
        
        # Parse results - use LLM's native format (steps)
        story_summary = data.get("story_summary", "")
        steps = data.get("steps", [])
        
        # Build analysis from summary
        analysis = {
            "task_type": "feature",
            "complexity": "medium" if len(steps) <= 5 else "high",
            "summary": story_summary,
        }
        
        logger.info(f"[analyze_and_plan] {len(steps)} steps")
        
        # Format message
        steps_text = "\n".join(f"  {s.get('order', i+1)}. {s.get('description', '')}" for i, s in enumerate(steps))
        msg = f"📋 **{story_summary}**\n\n{steps_text}"
        
        return {
            **state,
            # Analysis results
            "analysis_result": analysis,
            "task_type": "feature",
            "complexity": analysis["complexity"],
            "affected_files": [s.get("file_path") for s in steps if s.get("file_path")],
            # Plan results - use steps directly
            "implementation_plan": steps,
            "total_steps": len(steps),
            "current_step": 0,
            "message": msg,
            "skill_registry": skill_registry,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[analyze_and_plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
