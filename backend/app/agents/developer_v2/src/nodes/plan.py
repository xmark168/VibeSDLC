"""Analyze and Plan node - Combined analysis and planning with tool exploration."""
import os
import re
import logging
import glob as glob_module
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    flush_langfuse,
    execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.nodes._llm import code_llm, exploration_llm, fast_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context
from app.agents.developer_v2.src.nodes.schemas import SimplePlanOutput
from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills import get_project_structure, get_plan_prompts
from app.agents.developer_v2.src.tools.filesystem_tools import (
    read_file_safe, list_directory_safe, glob, grep_files
)

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
    
    # Always read core files (expanded for better context)
    core_files = [
        ("package.json", 500),
        ("prisma/schema.prisma", 3000),
        ("src/app/layout.tsx", 2000),
        ("src/lib/prisma.ts", 1000),
        ("src/types/index.ts", 1500),
        ("src/app/actions/index.ts", 1000),
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
    
    # Find related files based on keywords (expanded)
    for keyword in keywords[:8]:
        pattern = os.path.join(workspace_path, "src", "**", f"*{keyword}*")
        try:
            matches = glob_module.glob(pattern, recursive=True)
            for match in matches[:3]:
                if os.path.isfile(match):
                    rel_path = os.path.relpath(match, workspace_path)
                    with open(match, 'r', encoding='utf-8') as f:
                        content = f.read()[:1500]
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
        "src/app/layout.tsx",  # See what components are already rendered
        "src/types/index.ts",
        "src/lib/prisma.ts",
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


def _auto_assign_skills(file_path: str) -> list:
    """Auto-assign skills based on file path."""
    if not file_path:
        return []
    
    fp = file_path.lower()
    skills = []
    
    # Database
    if "schema.prisma" in fp:
        skills.append("database-model")
    elif "seed.ts" in fp:
        skills.append("database-seed")
    # API routes
    elif "/api/" in fp or "route.ts" in fp:
        skills.append("api-route")
    # Server actions
    elif "/actions/" in fp or "action.ts" in fp:
        skills.append("server-action")
    # Auth
    elif "auth" in fp:
        skills.append("authentication")
    # Frontend
    elif fp.endswith(".tsx"):
        if "/components/" in fp:
            skills.extend(["frontend-component", "frontend-design"])
        elif "/app/" in fp:
            skills.append("frontend-design")  # Pages
    # Types
    elif "/types/" in fp or fp.endswith(".d.ts"):
        skills.append("typescript-types")
    
    return skills


def _auto_detect_dependencies(file_path: str, all_steps: list = None) -> list:
    """Auto-detect dependencies based on file path and other steps in plan.
    
    Key patterns:
    - Section components depend on Card/Item components
    - Pages depend on components in same domain
    - API routes depend on schema and lib
    """
    if not file_path:
        return []
    
    fp = file_path.lower()
    deps = []
    
    # All files might need schema
    if "/api/" in fp or "/actions/" in fp or "seed.ts" in fp:
        deps.append("prisma/schema.prisma")
    
    # Components/pages might need types
    if fp.endswith(".tsx"):
        deps.append("src/types/index.ts")
    
    # API routes might need lib
    if "/api/" in fp:
        deps.append("src/lib/prisma.ts")
    
    # === NEW: Component cross-dependencies ===
    if all_steps and fp.endswith(".tsx"):
        filename = file_path.split("/")[-1].replace(".tsx", "").lower()
        
        # Section components depend on Card/Item components
        # e.g., CategoriesSection.tsx depends on CategoryCard.tsx
        if "section" in filename:
            # Extract domain: "categoriessection" -> "categor" (prefix)
            domain = filename.replace("section", "").replace("s", "")[:6]
            
            for step in all_steps:
                other_fp = step.get("file_path", "").lower()
                other_name = other_fp.split("/")[-1].replace(".tsx", "")
                
                # Find related Card/Item components
                if other_fp != fp.lower() and other_fp.endswith(".tsx"):
                    if ("card" in other_name or "item" in other_name) and domain in other_name:
                        deps.append(step.get("file_path", ""))
        
        # Pages depend on Section components
        if "page.tsx" in fp:
            folder = "/".join(file_path.split("/")[:-1]).lower()
            
            for step in all_steps:
                other_fp = step.get("file_path", "").lower()
                
                # Section components in same domain
                if other_fp != fp.lower() and "section" in other_fp and other_fp.endswith(".tsx"):
                    deps.append(step.get("file_path", ""))
                
                # Card components (for pages that directly use cards)
                if other_fp != fp.lower() and "card" in other_fp and other_fp.endswith(".tsx"):
                    deps.append(step.get("file_path", ""))
    
    return list(set(deps))  # Remove duplicates


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

    response = await fast_llm.ainvoke([
        SystemMessage(content="You are a technical summarizer. Be concise."),
        HumanMessage(content=summary_prompt)
    ], config=_cfg(state, "summarize_exploration"))
    flush_langfuse(state)  # Real-time update
    
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
    """Extract plan using simplified structured output (~250 tokens vs ~1000).
    
    Optimized: Only outputs steps (file_path, action, task).
    Post-process adds: order, skills, dependencies.
    """
    try:
        logger.info("[analyze_and_plan] Using optimized structured output")
        
        structured_llm = fast_llm.with_structured_output(SimplePlanOutput)
        
        structured_prompt = f"""Convert this exploration into an implementation plan.

## Story
Title: {story_title}
Description: {story_description[:500] if story_description else "No description"}

## Exploration Summary
{response[:6000]}

## Instructions
Create steps: Ordered list (database → API → components → pages)
- Each step: file_path, action (create/modify), task, dependencies
- task: WHAT to implement (1-2 sentences)
- dependencies: Files this step needs as context (e.g., schema.prisma, types/index.ts, parent components)

## Dependency Rules (IMPORTANT)
- API routes need: prisma/schema.prisma, src/lib/prisma.ts
- Components need: src/types/index.ts
- Section components need: related Card/Item components (e.g., BooksSection needs BookCard.tsx)
- Pages need: components they will import

## Order (for parallel execution)
Layer 1: prisma/schema.prisma (database)
Layer 2: prisma/seed.ts
Layer 3: src/types/*.ts
Layer 4: src/lib/*.ts
Layer 5: src/app/api/**/route.ts (can run parallel)
Layer 6: src/app/actions/*.ts
Layer 7: src/components/*Card.tsx, *Item.tsx (can run parallel)
Layer 8: src/components/*Section.tsx (can run parallel)
Layer 9: src/app/**/page.tsx

Steps in same layer CAN run in parallel if they don't depend on each other.
"""
        
        result = await structured_llm.ainvoke([
            SystemMessage(content="You are a technical planner. Create structured implementation plans."),
            HumanMessage(content=structured_prompt)
        ], config=_cfg(state, "analyze_and_plan_structured"))
        flush_langfuse(state)  # Real-time update
        
        data = result.model_dump()
        if data and data.get("steps"):
            logger.info(f"[analyze_and_plan] Got {len(data['steps'])} steps")
            return data
            
    except Exception as e:
        logger.warning(f"[analyze_and_plan] Structured output failed: {e}")
    
    # FALLBACK: Minimal plan (never fails)
    logger.error("[analyze_and_plan] Fallback plan")
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


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Combined analyze + plan with tool exploration phase."""
    logger.info("[NODE] analyze_and_plan")
    
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
            glob,        # glob pattern search
            grep_files,  # text search in files
        ]
        
        # Single-phase: explore + analyze + plan in one call
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=input_text)
        ]
        
        response = await _llm_with_tools(
            llm=exploration_llm,  # Fast model (Haiku) for exploration
            tools=tools,
            messages=messages,
            state=state,
            name="analyze_and_plan",
            max_iterations=5  # Sonnet needs fewer iterations with better prefetch
        )
        
        # Truncate if too long (no summarize LLM call needed)
        if len(response) > 6000:
            response = response[:6000]
        
        # Extract plan using optimized structured output
        data = await _extract_json_with_retry(
            response=response,
            state=state,
            story_title=state.get("story_title", ""),
            story_description=state.get("story_description", ""),
        )
        
        # Get steps from simplified output
        steps = data.get("steps", [])
        story_summary = state.get("story_title", "Implementation task")
        
        # Filter out migration steps
        steps = [s for s in steps if "migration" not in s.get("task", "").lower() 
                 and "migration" not in s.get("file_path", "").lower()]
        
        # Filter out existing boilerplate files (LLM sometimes ignores NEVER rules)
        BOILERPLATE_FILES = {
            "src/lib/prisma.ts",
            "src/lib/utils.ts",
            "src/auth.ts",
        }
        original_count = len(steps)
        steps = [s for s in steps if s.get("file_path", "").replace("\\", "/") not in BOILERPLATE_FILES]
        if len(steps) < original_count:
            removed = original_count - len(steps)
            logger.info(f"[analyze_and_plan] Filtered out {removed} boilerplate file(s)")
        
        # Post-process: add order, skills, description, auto-detect dependencies
        for i, step in enumerate(steps):
            step["order"] = i + 1
            step["description"] = step.get("task", "")  # For backward compatibility
            step["skills"] = _auto_assign_skills(step.get("file_path", ""))
            
            # Ensure dependencies is a list (from LLM output)
            if not isinstance(step.get("dependencies"), list):
                step["dependencies"] = []
            
            # Auto-detect dependencies and merge with LLM-provided deps
            llm_deps = step.get("dependencies", [])
            auto_deps = _auto_detect_dependencies(step.get("file_path", ""), steps)
            step["dependencies"] = list(set(llm_deps + auto_deps))
        
        # Auto-add seed step when database models are created (if LLM didn't already add one)
        has_schema_step = any(
            s.get("file_path", "").endswith("schema.prisma")
            for s in steps
        )
        has_seed_step = any(
            "seed.ts" in s.get("file_path", "").lower()
            for s in steps
        )
        
        if has_schema_step and not has_seed_step:
            seed_file = Path(workspace_path) / "prisma" / "seed.ts" if workspace_path else None
            seed_exists = seed_file and seed_file.exists()
            
            schema_idx = next(
                (i for i, s in enumerate(steps) if s.get("file_path", "").endswith("schema.prisma")),
                0
            )
            seed_step = {
                "order": schema_idx + 2,
                "task": "Create seed data for new database models",
                "description": "Seed database with sample data for testing and development",
                "file_path": "prisma/seed.ts",
                "action": "modify" if seed_exists else "create",
                "skills": ["database-seed"],
                "dependencies": ["prisma/schema.prisma"]
            }
            # Insert after schema step (schema_idx + 1)
            steps.insert(schema_idx + 1, seed_step)
            logger.info("[analyze_and_plan] Auto-added seed step after schema")
        
        # Re-number after modifications
        for i, s in enumerate(steps):
            s["order"] = i + 1
        
        # Build analysis from summary
        analysis = {
            "task_type": "feature",
            "complexity": "medium" if len(steps) <= 5 else "high",
            "summary": story_summary,
        }
        
        logger.info(f"[analyze_and_plan] {len(steps)} steps")
        
        # Pre-load dependency files
        dependencies_content = _preload_dependencies(workspace_path, steps)
        logger.info(f"[analyze_and_plan] Pre-loaded {len(dependencies_content)} files")
        
        # Calculate parallel layers
        from app.agents.developer_v2.src.nodes.parallel_utils import (
            group_steps_by_layer,
            should_use_parallel,
        )
        
        layers = group_steps_by_layer(steps)
        can_parallel = should_use_parallel(steps)
        
        # Format message with parallel info
        steps_text = []
        for layer_num in sorted(layers.keys()):
            layer_steps = layers[layer_num]
            mode = "PARALLEL" if len(layer_steps) > 1 else ""
            for s in layer_steps:
                order = s.get('order', '?')
                action = s.get('action', '')
                file_path = s.get('file_path', '')
                parallel_tag = f" [{mode}]" if mode else ""
                steps_text.append(f"  {order}. [{action}] {file_path}{parallel_tag}")
        
        msg = f"📋 **{story_summary}**\n\n" + "\n".join(steps_text)
        if can_parallel:
            msg += f"\n\n🔀 Parallel execution: {len(layers)} layers"
        
        return {
            **state,
            "analysis_result": analysis,
            "task_type": "feature",
            "complexity": analysis["complexity"],
            "affected_files": [s.get("file_path") for s in steps if s.get("file_path")],
            "implementation_plan": steps,
            "dependencies_content": dependencies_content,
            "total_steps": len(steps),
            "current_step": 0,
            "message": msg,
            "skill_registry": skill_registry,
            "parallel_layers": {float(k): [s.get("file_path") for s in v] for k, v in layers.items()},
            "can_parallel": can_parallel,
            "action": "IMPLEMENT",
        }
        
    except Exception as e:
        logger.error(f"[analyze_and_plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
