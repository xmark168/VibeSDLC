"""Analyze node - Analyze story + research best practices."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_tavily import TavilySearch

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import StoryAnalysis
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, search_files
from app.agents.developer_v2.src.tools.shell_tools import execute_shell, semantic_code_search
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
    """Analyze story + research best practices (merged node)."""
    print("[NODE] analyze")
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Get AGENTS.md and project context for analysis (loaded in setup_workspace)
        agents_md = state.get("agents_md", "")
        project_context = state.get("project_context", "")
        
        input_text = _format_input_template(
            "analyze_story",
            story_title=state.get("story_title", "Untitled"),
            story_content=state.get("story_content", ""),
            acceptance_criteria=chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", [])),
            agents_md_summary=agents_md[:3000] if agents_md else "No AGENTS.md found",
            project_context=project_context[:2000] if project_context else "No project context",
        )

        tools = [read_file_safe, list_directory_safe, semantic_code_search, execute_shell, search_files]
        
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
            max_iterations=3
        )
        
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:5000]}\n\nNow provide your final analysis."))
        structured_llm = code_llm.with_structured_output(StoryAnalysis)
        analysis = await structured_llm.ainvoke(messages, config=_cfg(state, "analyze"))
        
        logger.info(f"[analyze] Done: {analysis.task_type}, {analysis.complexity}")
        
        # Research best practices (for medium/high complexity)
        research_context = ""
        if analysis.complexity in ["medium", "high"]:
            try:
                project_config = state.get("project_config", {})
                tech_stack = project_config.get("tech_stack", {})
                services = tech_stack.get("service", []) if isinstance(tech_stack, dict) else []
                
                framework = "Next.js"
                if services:
                    svc = services[0]
                    if svc.get("runtime") == "python":
                        framework = "FastAPI"
                
                story_title = state.get("story_title", "")
                keywords = story_title.lower().replace("implement", "").replace("create", "").strip()
                query = f"{framework} {keywords} best practices 2024"
                
                tavily_tool = TavilySearch(max_results=3)
                logger.info(f"[analyze] Research: {query}")
                result = tavily_tool.invoke(query)
                if result:
                    research_context = f"### Best Practices\n{result[:1500]}"
                    logger.info(f"[analyze] Research found: {len(research_context)} chars")
            except Exception as e:
                logger.warning(f"[analyze] Research failed: {e}")
        
        return {
            **state,
            "analysis_result": analysis.model_dump(),
            "task_type": analysis.task_type,
            "complexity": analysis.complexity,
            "estimated_hours": analysis.estimated_hours,
            "affected_files": analysis.affected_files,
            "dependencies": analysis.dependencies,
            "risks": analysis.risks,
            "research_context": research_context,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[analyze] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
