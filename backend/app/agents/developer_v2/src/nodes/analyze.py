"""Analyze node - Analyze story to understand scope and complexity."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import StoryAnalysis
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.tools.filesystem_tools import list_directory_safe, glob, grep_files
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.utils.prompt_utils import (
    format_input_template as _format_input_template,
    build_system_prompt as _build_system_prompt,
)
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context

logger = logging.getLogger(__name__)


async def analyze(state: DeveloperState, agent=None) -> DeveloperState:
    """Analyze story to understand scope, complexity, and affected files."""
    logger.info("[NODE] analyze")
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        agents_md = state.get("agents_md", "")
        project_context = state.get("project_context", "")
        
        # Format requirements and acceptance criteria
        requirements = state.get("story_requirements", [])
        req_text = chr(10).join(f"- {r}" for r in requirements)
        ac_text = chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        
        input_text = _format_input_template(
            "analyze_story",
            story_id=state.get("story_id", ""),
            epic=state.get("epic", ""),
            story_title=state.get("story_title", "Untitled"),
            story_description=state.get("story_description", ""),
            story_requirements=req_text,
            acceptance_criteria=ac_text,
            agents_md_summary=agents_md[:3000] if agents_md else "",
            project_context=project_context[:2000] if project_context else "",
        )

        tools = [read_file_safe, list_directory_safe, glob, grep_files]
        
        messages = [
            SystemMessage(content=_build_system_prompt("analyze_story")),
            HumanMessage(content=input_text)
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_explore",
            max_iterations=2
        )
        
        json_schema = '''Respond with JSON wrapped in result tags:
<result>
{"task_type": "feature|bugfix|refactor|enhancement|documentation", "complexity": "low|medium|high", "estimated_hours": <number>, "summary": "<string>", "affected_files": ["<path>"], "dependencies": ["<string>"], "risks": ["<string>"], "suggested_approach": "<string>"}
</result>'''
        
        messages.append(HumanMessage(content=f"Context:\n{exploration[:4000]}\n\n{json_schema}"))
        response = await code_llm.ainvoke(messages, config=_cfg(state, "analyze"))
        data = extract_json_universal(response.content, "analyze_node")
        analysis = StoryAnalysis(**data)
        
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
