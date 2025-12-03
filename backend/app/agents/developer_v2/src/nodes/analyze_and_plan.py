"""Analyze and Plan node - Combined analysis and planning with tool exploration."""
import os
import re
import logging
import glob as glob_module
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


def _extract_keywords(text: str) -> list:
    """Extract meaningful keywords from story text."""
    stopwords = {'the', 'a', 'an', 'is', 'are', 'can', 'will', 'should', 'must',
                 'user', 'users', 'when', 'then', 'given', 'and', 'or', 'to', 'from',
                 'with', 'for', 'on', 'in', 'at', 'by', 'of', 'that', 'this', 'be',
                 'want', 'see', 'click', 'display', 'show', 'create', 'update', 'delete'}
    
    words = re.findall(r'[a-z]+', text.lower())
    
    keywords = []
    seen = set()
    for word in words:
        if len(word) > 3 and word not in stopwords and word not in seen:
            keywords.append(word)
            seen.add(word)
    
    return keywords[:10]


def _smart_prefetch(workspace_path: str, story_title: str, requirements: list) -> str:
    """Prefetch relevant files based on story content."""
    if not workspace_path or not os.path.exists(workspace_path):
        return ""
    
    context_parts = []
    
    # Always read core files
    core_files = [
        ("package.json", 500),
        ("prisma/schema.prisma", 2000),
        ("src/app/layout.tsx", 500),
        ("tsconfig.json", 300),
    ]
    
    for file_path, max_len in core_files:
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()[:max_len]
                context_parts.append(f"### {file_path}\n```\n{content}\n```")
            except Exception:
                pass
    
    # Extract keywords from story
    req_text = ' '.join(requirements) if requirements else ''
    text = f"{story_title} {req_text}".lower()
    keywords = _extract_keywords(text)
    
    # Find related files based on keywords
    for keyword in keywords[:5]:
        pattern = os.path.join(workspace_path, "src", "**", f"*{keyword}*")
        try:
            matches = glob_module.glob(pattern, recursive=True)
            for match in matches[:2]:
                if os.path.isfile(match):
                    rel_path = os.path.relpath(match, workspace_path)
                    with open(match, 'r', encoding='utf-8') as f:
                        content = f.read()[:1000]
                    context_parts.append(f"### {rel_path}\n```\n{content}\n```")
        except Exception:
            pass
    
    # List key directories
    for dir_name in ["src/app/api", "src/components", "src/lib", "src/app"]:
        dir_path = os.path.join(workspace_path, dir_name)
        if os.path.exists(dir_path):
            try:
                items = os.listdir(dir_path)[:15]
                context_parts.append(f"### {dir_name}/\n{', '.join(items)}")
            except Exception:
                pass
    
    return "\n\n".join(context_parts)


async def _summarize_if_needed(exploration: str, state: dict) -> str:
    """Summarize exploration if too long, otherwise return as-is."""
    MAX_CHARS = 8000
    
    if len(exploration) <= MAX_CHARS:
        return exploration
    
    logger.info(f"[analyze_and_plan] Summarizing exploration ({len(exploration)} chars)")
    
    summary_prompt = f"""Summarize this codebase exploration concisely:

{exploration[:15000]}

Output a bullet-point summary focusing on:
- Existing database models
- Relevant components/files found  
- Patterns to follow
- Key insights for implementation"""

    response = await code_llm.ainvoke([
        SystemMessage(content="You are a technical summarizer. Be concise."),
        HumanMessage(content=summary_prompt)
    ], config=_cfg(state, "summarize_exploration"))
    
    return f"## Exploration Summary\n{response.content}"


async def analyze_and_plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Combined analyze + plan with tool exploration phase."""
    print("[NODE] analyze_and_plan")
    
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id", "default")
        task_id = state.get("task_id") or state.get("story_id", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        # Smart prefetch based on story content
        project_context = _smart_prefetch(
            workspace_path,
            state.get("story_title", ""),
            state.get("story_requirements", [])
        )
        project_structure = get_project_structure(tech_stack)
        
        # Load skill registry (for later use in implement)
        skill_registry = SkillRegistry.load(tech_stack)
        
        # Load prompts from plan_prompts.yaml
        plan_prompts = get_plan_prompts(tech_stack)
        
        # Single-phase system prompt with clear workflow
        system_prompt = f"""{plan_prompts['system_prompt']}

<workflow>
1. EXPLORE: Use tools to understand codebase (3-5 tool calls max)
2. ANALYZE: Summarize what you found
3. OUTPUT: JSON in <result> tags

CRITICAL: After exploration, you MUST output <result> JSON. Do not stop at exploration.
</workflow>

<project_structure>
{project_structure}
</project_structure>"""
        
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
        
        # Single-phase: explore + analyze + plan in one call
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        response = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_and_plan",
            max_iterations=8  # Enough for explore + output
        )
        
        # Summarize if response is too long
        response = await _summarize_if_needed(response, state)
        
        # Extract JSON from response
        try:
            data = extract_json_universal(response, "analyze_and_plan")
        except ValueError as e:
            # Retry with explicit JSON request
            logger.warning(f"[analyze_and_plan] JSON extraction failed, retrying: {e}")
            
            retry_messages = [
                SystemMessage(content="Output ONLY a JSON implementation plan in <result> tags. No explanations."),
                HumanMessage(content=f"""Convert this exploration into a JSON plan:

{response[:4000]}

<result>
{{"story_summary": "...", "steps": [{{"order": 1, "description": "..."}}]}}
</result>""")
            ]
            
            retry_response = await code_llm.ainvoke(retry_messages, config=_cfg(state, "analyze_and_plan_retry"))
            data = extract_json_universal(retry_response.content, "analyze_and_plan")
        
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
