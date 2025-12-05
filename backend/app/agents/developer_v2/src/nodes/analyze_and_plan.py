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
from app.agents.developer_v2.src.nodes.schemas import AnalyzePlanOutput
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


def _preload_dependencies(workspace_path: str, steps: list) -> dict:
    """Pre-load dependency file contents (MetaGPT-style)."""
    dependencies_content = {}
    
    if not workspace_path or not os.path.exists(workspace_path):
        return dependencies_content
    
    # Collect all unique dependencies from steps
    all_deps = set()
    for step in steps:
        deps = step.get("dependencies", [])
        if isinstance(deps, list):
            for dep in deps:
                # Only add string paths, skip integers (step numbers)
                if isinstance(dep, str) and dep:
                    all_deps.add(dep)
                elif isinstance(dep, int):
                    # LLM sometimes outputs step numbers instead of file paths
                    # Try to resolve: find file_path from step with that order
                    for s in steps:
                        if s.get("order") == dep and s.get("file_path"):
                            all_deps.add(s["file_path"])
                            break
    
    # Also add common files that are often needed
    common_files = [
        "prisma/schema.prisma",
        "src/lib/prisma.ts",
        "src/types/index.ts",
    ]
    all_deps.update(common_files)
    
    # Pre-load each dependency
    for dep_path in all_deps:
        if not isinstance(dep_path, str):
            continue
        full_path = os.path.join(workspace_path, dep_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Limit content size to avoid token overflow
                if len(content) > 8000:
                    content = content[:8000] + "\n... (truncated)"
                dependencies_content[dep_path] = content
                logger.info(f"[analyze_and_plan] Pre-loaded: {dep_path}")
            except Exception as e:
                logger.warning(f"[analyze_and_plan] Failed to pre-load {dep_path}: {e}")
    
    return dependencies_content


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


# JSON generation prompt for retry mechanism
JSON_GENERATION_PROMPT = """You are a technical planner. Convert the exploration summary into a JSON implementation plan.

## Exploration Summary
{exploration}

## Story
Title: {story_title}
Description: {story_description}

## Required Output Format
Output ONLY valid JSON in <result> tags. No explanations before or after.

<result>
{{
  "story_summary": "Brief 1-sentence summary of what to implement",
  "logic_analysis": [
    ["file_path.ts", "'use client' if needed, component/function names, key logic"],
    ["another_file.ts", "description of what this file does"]
  ],
  "steps": [
    {{
      "order": 1,
      "description": "What to implement in this file",
      "file_path": "src/path/to/file.ts",
      "action": "create",
      "dependencies": ["path/to/dependency.ts"]
    }}
  ]
}}
</result>

RULES:
- Order: database (prisma) → API routes → components → pages
- Each step = 1 file with exact path
- action: "create" for new files, "modify" for existing
- dependencies: files that must be read as context
- For React components with hooks/events: include "'use client'" in logic_analysis

OUTPUT ONLY THE JSON. NO OTHER TEXT."""


async def _extract_json_with_retry(
    response: str,
    state: dict,
    story_title: str,
    story_description: str,
    max_retries: int = 2
) -> dict:
    """Extract JSON with structured output as PRIMARY method.
    
    Strategy:
    1. Try structured output with Pydantic (PRIMARY - 99% reliable)
    2. If fails, try direct extraction (backup - for cached responses)
    3. If still fails, fallback plan (never fails)
    """
    # PRIMARY: Structured output with Pydantic (most reliable)
    try:
        logger.info("[analyze_and_plan] Using structured output (primary)")
        
        structured_llm = code_llm.with_structured_output(AnalyzePlanOutput)
        
        structured_prompt = f"""Convert this exploration into an implementation plan.

## Story
Title: {story_title}
Description: {story_description[:500] if story_description else "No description"}

## Exploration Summary
{response[:6000]}

## Instructions
Create an implementation plan with:
1. story_summary: Brief 1-sentence summary
2. logic_analysis: [[file_path, description], ...] - HIGH-LEVEL descriptions only
3. steps: Ordered list (database → API → components → pages)
   - Each step: order, description, file_path, action (create/modify), dependencies
   - description should include:
     - WHAT: Purpose, user-facing behavior, inputs/outputs
     - DESIGN INTENT: Visual style, feel, memorable aspects (for UI components)
   - DO NOT include: specific imports, interface definitions, implementation patterns
   - Let skills handle HOW to implement

## Quality Requirements
- Focus on INTENT, not implementation details
- Describe desired user experience and visual design
- Leave technical decisions (imports, patterns, hooks) to implementation phase + skills
"""
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are a technical planner. Create structured implementation plans."),
            HumanMessage(content=structured_prompt)
        ], config=_cfg(state, "analyze_and_plan_structured"))
        
        data = result.model_dump()
        if data and data.get("steps"):
            logger.info(f"[analyze_and_plan] Structured output: {len(data['steps'])} steps")
            return data
            
    except Exception as e:
        logger.warning(f"[analyze_and_plan] Structured output failed: {e}")
    
    # BACKUP: Direct extraction (for edge cases or cached responses)
    try:
        data = extract_json_universal(response, "analyze_and_plan")
        if data and data.get("steps"):
            logger.info("[analyze_and_plan] Direct extraction backup success")
            return data
    except ValueError:
        pass
    
    # FALLBACK: Minimal plan (never fails)
    logger.error("[analyze_and_plan] All methods failed, using fallback plan")
    
    return {
        "story_summary": story_title or "Implementation task",
        "logic_analysis": [],
        "steps": [
            {
                "order": 1,
                "description": f"Implement: {story_title}",
                "file_path": "src/app/page.tsx",
                "action": "modify",
                "dependencies": []
            }
        ]
    }


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
        
        # Extract JSON from response with robust retry mechanism
        data = await _extract_json_with_retry(
            response=response,
            state=state,
            story_title=state.get("story_title", ""),
            story_description=state.get("story_description", ""),
        )
        
        # Parse results - MetaGPT style with logic_analysis
        story_summary = data.get("story_summary", "")
        steps = data.get("steps", [])
        logic_analysis = data.get("logic_analysis", [])
        
        # Filter out migration steps (use db push instead)
        steps = [s for s in steps if "migration" not in s.get("description", "").lower() 
                 and "migration" not in s.get("file_path", "").lower()]
        
        # Re-number steps after filtering
        for i, s in enumerate(steps):
            s["order"] = i + 1
        
        # Build analysis from summary
        analysis = {
            "task_type": "feature",
            "complexity": "medium" if len(steps) <= 5 else "high",
            "summary": story_summary,
        }
        
        logger.info(f"[analyze_and_plan] {len(steps)} steps, {len(logic_analysis)} logic entries")
        
        # Pre-load dependency files (MetaGPT-style - reduces tool calls in implement)
        dependencies_content = _preload_dependencies(workspace_path, steps)
        logger.info(f"[analyze_and_plan] Pre-loaded {len(dependencies_content)} dependency files")
        
        # Format message with file paths
        steps_text = []
        for i, s in enumerate(steps):
            desc = s.get('description', '')
            file_path = s.get('file_path', '')
            action = s.get('action', '')
            if file_path:
                steps_text.append(f"  {s.get('order', i+1)}. [{action}] {file_path}: {desc}")
            else:
                steps_text.append(f"  {s.get('order', i+1)}. {desc}")
        msg = f"📋 **{story_summary}**\n\n" + "\n".join(steps_text)
        
        return {
            **state,
            # Analysis results
            "analysis_result": analysis,
            "task_type": "feature",
            "complexity": analysis["complexity"],
            "affected_files": [s.get("file_path") for s in steps if s.get("file_path")],
            # Plan results - MetaGPT style
            "implementation_plan": steps,
            "logic_analysis": logic_analysis,
            "dependencies_content": dependencies_content,  # Pre-loaded!
            "total_steps": len(steps),
            "current_step": 0,
            "message": msg,
            "skill_registry": skill_registry,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[analyze_and_plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
