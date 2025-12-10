"""Analyze and Plan node - Zero-shot planning with FileRepository."""
import os
import re
import logging
import glob as glob_module
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.utils.json_utils import extract_json_universal
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg, flush_langfuse, execute_llm_with_tools as _llm_with_tools,
)
from app.agents.developer_v2.src.nodes._llm import code_llm, exploration_llm, fast_llm
from app.agents.developer_v2.src.tools import set_tool_context
from app.agents.developer_v2.src.schemas import SimplePlanOutput
from app.agents.developer_v2.src.skills.registry import SkillRegistry
from app.agents.developer_v2.src.skills import get_project_structure, get_plan_prompts
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, glob, grep_files

logger = logging.getLogger(__name__)

BOILERPLATE_FILES = {"src/lib/prisma.ts", "src/lib/utils.ts", "src/auth.ts"}


class FileRepository:
    """Pre-computed workspace context for zero-shot planning."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.files = {}
        self.file_tree = []
        self.components = {}
        self.api_routes = []
        self._scan()
    
    def _scan(self):
        if not self.workspace_path or not os.path.exists(self.workspace_path):
            return
        exclude_dirs = {'node_modules', '.next', '.git', '__pycache__', '.prisma'}
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f.endswith(('.ts', '.tsx', '.prisma', '.json', '.md')):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.workspace_path).replace('\\', '/')
                    self.file_tree.append(rel_path)
                    if self._is_important(rel_path):
                        self.files[rel_path] = self._read_file(full_path)
                    if '/components/' in rel_path and rel_path.endswith('.tsx') and '/ui/' not in rel_path:
                        name = os.path.basename(rel_path).replace('.tsx', '')
                        self.components[name] = '@/' + rel_path.replace('.tsx', '')
                    if '/api/' in rel_path and rel_path.endswith('route.ts'):
                        self.api_routes.append(rel_path)
    
    def _is_important(self, path: str) -> bool:
        return any(path.endswith(p) for p in ['prisma/schema.prisma', 'src/types/index.ts', 'package.json', 'src/app/layout.tsx', 'src/lib/prisma.ts'])
    
    def _read_file(self, full_path: str) -> str:
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
    
    def to_context(self) -> str:
        parts = ["## Project Files (COMPLETE)", "```", "\n".join(sorted(self.file_tree)), "```"]
        schema = self.files.get('prisma/schema.prisma', '')
        parts.extend(["\n## prisma/schema.prisma", "```prisma", schema if len(schema) > 100 else "// Empty", "```"])
        types = self.files.get('src/types/index.ts', '')
        if len(types) > 100:
            parts.extend(["\n## src/types/index.ts", "```typescript", types[:2500], "```"])
        if self.components:
            parts.append("\n## Component Imports")
            for name, path in sorted(self.components.items()):
                parts.append(f"- {name} → `import {{ {name} }} from '{path}'`")
        if self.api_routes:
            parts.append("\n## API Routes")
            parts.extend(f"- {r}" for r in sorted(self.api_routes))
        return "\n".join(parts)


def _extract_keywords(text: str) -> list:
    stopwords = {'the', 'a', 'an', 'is', 'are', 'can', 'will', 'should', 'must', 'user', 'users', 'when', 'then', 'given', 'and', 'or', 'to', 'from', 'with', 'for', 'on', 'in', 'at', 'by', 'of', 'that', 'this', 'be', 'want', 'see', 'click', 'display', 'show', 'create', 'update', 'delete'}
    words = re.findall(r'[a-z]+', text.lower())
    seen = set()
    return [w for w in words if len(w) > 3 and w not in stopwords and not (w in seen or seen.add(w))][:10]


def _smart_prefetch(workspace_path: str, story_title: str, requirements: list) -> str:
    if not workspace_path or not os.path.exists(workspace_path):
        return ""
    parts = []
    core_files = [("package.json", 500), ("prisma/schema.prisma", 3000), ("src/app/layout.tsx", 2000), ("src/lib/prisma.ts", 1000), ("src/types/index.ts", 1500), ("src/app/actions/index.ts", 1000), ("tsconfig.json", 300)]
    for file_path, max_len in core_files:
        full_path = os.path.join(workspace_path, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    parts.append(f"### {file_path}\n```\n{f.read()[:max_len]}\n```")
            except:
                pass
    text = f"{story_title} {' '.join(requirements or [])}".lower()
    for kw in _extract_keywords(text)[:8]:
        try:
            for match in glob_module.glob(os.path.join(workspace_path, "src", "**", f"*{kw}*"), recursive=True)[:3]:
                if os.path.isfile(match):
                    with open(match, 'r', encoding='utf-8') as f:
                        parts.append(f"### {os.path.relpath(match, workspace_path)}\n```\n{f.read()[:1500]}\n```")
        except:
            pass
    for d in ["src/app/api", "src/components", "src/lib", "src/app"]:
        dp = os.path.join(workspace_path, d)
        if os.path.exists(dp):
            try:
                parts.append(f"### {d}/\n{', '.join(os.listdir(dp)[:15])}")
            except:
                pass
    return "\n\n".join(parts)


def _preload_dependencies(workspace_path: str, steps: list) -> dict:
    deps_content = {}
    if not workspace_path or not os.path.exists(workspace_path):
        return deps_content
    all_deps = set()
    for step in steps:
        for dep in step.get("dependencies", []):
            if isinstance(dep, str) and dep:
                all_deps.add(dep)
            elif isinstance(dep, int):
                for s in steps:
                    if s.get("order") == dep and s.get("file_path"):
                        all_deps.add(s["file_path"])
                        break
    all_deps.update(["prisma/schema.prisma", "src/app/layout.tsx", "src/types/index.ts", "src/lib/prisma.ts"])
    for dep in all_deps:
        if not isinstance(dep, str):
            continue
        fp = os.path.join(workspace_path, dep)
        if os.path.exists(fp) and os.path.isfile(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                deps_content[dep] = content[:8000] + "\n... (truncated)" if len(content) > 8000 else content
            except:
                pass
    return deps_content


def _auto_assign_skills(file_path: str) -> list:
    if not file_path:
        return []
    fp = file_path.lower()
    if "schema.prisma" in fp:
        return ["database-model"]
    if "seed.ts" in fp:
        return ["database-seed"]
    if "/api/" in fp or "route.ts" in fp:
        return ["api-route"]
    if "/actions/" in fp:
        return ["server-action"]
    if "auth" in fp:
        return ["authentication"]
    if fp.endswith(".tsx"):
        if "/components/" in fp:
            return ["frontend-component", "frontend-design"]
        if "/app/" in fp:
            return ["frontend-design"]
    return []


def _auto_detect_dependencies(file_path: str, all_steps: list = None) -> list:
    if not file_path:
        return []
    fp = file_path.lower()
    deps = []
    if "/api/" in fp or "/actions/" in fp or "seed.ts" in fp:
        deps.append("prisma/schema.prisma")
    if fp.endswith(".tsx"):
        deps.append("src/types/index.ts")
    if "/api/" in fp:
        deps.append("src/lib/prisma.ts")
    if all_steps and fp.endswith(".tsx"):
        filename = file_path.split("/")[-1].replace(".tsx", "").lower()
        if "section" in filename:
            domain = filename.replace("section", "").replace("s", "")[:6]
            for step in all_steps:
                other = step.get("file_path", "").lower()
                other_name = other.split("/")[-1].replace(".tsx", "")
                if other != fp and other.endswith(".tsx") and ("card" in other_name or "item" in other_name) and domain in other_name:
                    deps.append(step.get("file_path", ""))
        if "page.tsx" in fp:
            for step in all_steps:
                other = step.get("file_path", "").lower()
                if other != fp and other.endswith(".tsx") and ("section" in other or "card" in other):
                    deps.append(step.get("file_path", ""))
    return list(set(deps))


def _auto_fix_dependencies(steps: list) -> list:
    comp_paths = [s["file_path"] for s in steps if "/components/" in s.get("file_path", "")]
    api_routes = [s["file_path"] for s in steps if "/api/" in s.get("file_path", "")]
    for step in steps:
        fp = step.get("file_path", "")
        deps = step.get("dependencies", []) if isinstance(step.get("dependencies"), list) else []
        if "page.tsx" in fp:
            deps.extend(c for c in comp_paths if c not in deps)
        if "/components/" in fp:
            name = fp.split("/")[-1].replace(".tsx", "")
            if any(kw in name for kw in ["Section", "List", "Grid", "Carousel"]) and not any(kw in name for kw in ["Form", "Input", "Button", "Dialog", "Modal", "Card", "Item"]):
                if not any("/api/" in d for d in deps) and api_routes:
                    deps.append(api_routes[0])
        step["dependencies"] = list(set(deps))
    return steps


async def _extract_json_with_retry(response: str, state: dict, story_title: str, story_description: str, max_retries: int = 2) -> dict:
    try:
        structured_llm = fast_llm.with_structured_output(SimplePlanOutput)
        prompt = f"""Convert exploration into implementation plan.

## Story
Title: {story_title}
Description: {story_description[:500] if story_description else ""}

## Exploration
{response[:6000]}

Create steps (database → API → components → pages).
Each step: file_path, action, task, dependencies."""

        result = await structured_llm.ainvoke([
            SystemMessage(content="Create structured implementation plans."),
            HumanMessage(content=prompt)
        ], config=_cfg(state, "plan_structured"))
        flush_langfuse(state)
        data = result.model_dump()
        if data and data.get("steps"):
            return data
    except Exception as e:
        logger.warning(f"[plan] Structured output failed: {e}")
    return {"story_summary": story_title or "Task", "steps": [{"order": 1, "description": f"Implement: {story_title}", "file_path": "src/app/page.tsx", "action": "modify", "dependencies": []}]}


async def plan(state: DeveloperState, agent=None) -> DeveloperState:
    """Zero-shot planning with FileRepository."""
    logger.debug("[NODE] plan")
    workspace_path = state.get("workspace_path", "")
    tech_stack = state.get("tech_stack", "nextjs")
    set_tool_context(root_dir=workspace_path, project_id=state.get("project_id", ""), task_id=state.get("task_id") or state.get("story_id", ""))
    
    # Notify user planning started
    if agent:
        try:
            from uuid import UUID
            story_id = state.get("story_id", "")
            if story_id:
                story_uuid = UUID(story_id) if isinstance(story_id, str) else story_id
                await agent.message_story(story_uuid, "📋 Đang phân tích và lên kế hoạch...", message_type="progress")
        except Exception:
            pass
    
    try:
        repo = FileRepository(workspace_path)
        context = repo.to_context()
        logger.debug(f"[plan] FileRepository: {len(repo.file_tree)} files")
        
        plan_prompts = get_plan_prompts(tech_stack)
        system_prompt = plan_prompts.get('zero_shot_system', plan_prompts.get('system_prompt', ''))
        
        req_text = chr(10).join(f"- {r}" for r in state.get("story_requirements", []))
        ac_text = chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        
        input_text = f"""## Project Context
{context}

## Story
**Title**: {state.get('story_title', '')}
**Description**: {state.get('story_description', '')[:800]}
**Requirements**: {req_text}
**Acceptance**: {ac_text}

Create implementation plan. Output JSON steps directly."""

        structured_llm = fast_llm.with_structured_output(SimplePlanOutput)
        result = await structured_llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=input_text)], config=_cfg(state, "plan_zero_shot"))
        flush_langfuse(state)
        
        steps = result.model_dump().get("steps", [])
        logger.debug(f"[plan] Got {len(steps)} steps")
        
        if not steps:
            return await _plan_with_exploration(state, agent)
        
        # Post-process
        steps = [s for s in steps if s.get("file_path", "") not in BOILERPLATE_FILES]
        steps = _auto_fix_dependencies(steps)
        
        for i, step in enumerate(steps):
            step["order"] = i + 1
            step["description"] = step.get("task", "")
            step["skills"] = _auto_assign_skills(step.get("file_path", ""))
            llm_deps = step.get("dependencies", []) if isinstance(step.get("dependencies"), list) else []
            step["dependencies"] = list(set(llm_deps + _auto_detect_dependencies(step.get("file_path", ""), steps)))
        
        # Auto-add seed
        has_schema = any(s.get("file_path", "").endswith("schema.prisma") for s in steps)
        has_seed = any("seed.ts" in s.get("file_path", "").lower() for s in steps)
        if has_schema and not has_seed:
            seed_exists = workspace_path and (Path(workspace_path) / "prisma" / "seed.ts").exists()
            idx = next((i for i, s in enumerate(steps) if s.get("file_path", "").endswith("schema.prisma")), 0)
            steps.insert(idx + 1, {"order": idx + 2, "task": "Seed data", "description": "Seed database", "file_path": "prisma/seed.ts", "action": "modify" if seed_exists else "create", "skills": ["database-seed"], "dependencies": ["prisma/schema.prisma"]})
        
        for i, s in enumerate(steps):
            s["order"] = i + 1
        
        skill_registry = SkillRegistry.load(tech_stack)
        deps_content = _preload_dependencies(workspace_path, steps)
        
        from app.agents.developer_v2.src.nodes.parallel_utils import group_steps_by_layer, should_use_parallel
        layers = group_steps_by_layer(steps)
        can_parallel = should_use_parallel(steps)
        
        # Notify user with plan details
        if agent and steps:
            try:
                from uuid import UUID
                story_id = state.get("story_id", "")
                if story_id:
                    story_uuid = UUID(story_id) if isinstance(story_id, str) else story_id
                    step_list = "\n".join([f"  {i+1}. {s.get('file_path', '')} ({s.get('action', 'modify')})" for i, s in enumerate(steps)])
                    await agent.message_story(
                        story_uuid,
                        f"📝 Kế hoạch ({len(steps)} bước):\n{step_list}",
                        message_type="update"
                    )
            except Exception:
                pass
        
        return {**state, "implementation_plan": steps, "total_steps": len(steps), "dependencies_content": deps_content, "current_step": 0, "skill_registry": skill_registry, "parallel_layers": {float(k): [s.get("file_path") for s in v] for k, v in layers.items()}, "can_parallel": can_parallel, "action": "IMPLEMENT", "message": f"Plan: {len(steps)} steps ({len(layers)} layers)" + (" [PARALLEL]" if can_parallel else "")}
    except Exception as e:
        logger.warning(f"[plan] Zero-shot failed: {e}")
        return await _plan_with_exploration(state, agent)


async def _plan_with_exploration(state: DeveloperState, agent=None) -> DeveloperState:
    """Fallback with tool exploration."""
    logger.debug("[NODE] plan_with_exploration")
    try:
        workspace_path = state.get("workspace_path", "")
        tech_stack = state.get("tech_stack", "nextjs")
        set_tool_context(root_dir=workspace_path, project_id=state.get("project_id", ""), task_id=state.get("task_id") or state.get("story_id", ""))
        
        project_context = _smart_prefetch(workspace_path, state.get("story_title", ""), state.get("story_requirements", []))
        plan_prompts = get_plan_prompts(tech_stack)
        skill_registry = SkillRegistry.load(tech_stack)
        
        system_prompt = f"""{plan_prompts['system_prompt']}
<workflow>
1. EXPLORE: Use tools (3-5 calls max)
2. OUTPUT: JSON in <result> tags
</workflow>
<project_structure>{get_project_structure(tech_stack)}</project_structure>"""

        req_text = chr(10).join(f"- {r}" for r in state.get("story_requirements", []))
        ac_text = chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        input_text = plan_prompts["input_template"].format(story_id=state.get("story_id", ""), epic=state.get("epic", ""), story_title=state.get("story_title", ""), story_description=state.get("story_description", ""), story_requirements=req_text, acceptance_criteria=ac_text, project_context=project_context)
        
        response = await _llm_with_tools(llm=exploration_llm, tools=[read_file_safe, list_directory_safe, glob, grep_files], messages=[SystemMessage(content=system_prompt), HumanMessage(content=input_text)], state=state, name="plan_exploration", max_iterations=5)
        
        data = await _extract_json_with_retry(response[:6000], state, state.get("story_title", ""), state.get("story_description", ""))
        steps = data.get("steps", [])
        
        steps = [s for s in steps if "migration" not in s.get("task", "").lower() and s.get("file_path", "") not in BOILERPLATE_FILES]
        steps = _auto_fix_dependencies(steps)
        
        for i, step in enumerate(steps):
            step["order"] = i + 1
            step["description"] = step.get("task", "")
            step["skills"] = _auto_assign_skills(step.get("file_path", ""))
            llm_deps = step.get("dependencies", []) if isinstance(step.get("dependencies"), list) else []
            step["dependencies"] = list(set(llm_deps + _auto_detect_dependencies(step.get("file_path", ""), steps)))
        
        has_schema = any(s.get("file_path", "").endswith("schema.prisma") for s in steps)
        has_seed = any("seed.ts" in s.get("file_path", "").lower() for s in steps)
        if has_schema and not has_seed:
            seed_exists = workspace_path and (Path(workspace_path) / "prisma" / "seed.ts").exists()
            idx = next((i for i, s in enumerate(steps) if s.get("file_path", "").endswith("schema.prisma")), 0)
            steps.insert(idx + 1, {"order": idx + 2, "task": "Seed data", "file_path": "prisma/seed.ts", "action": "modify" if seed_exists else "create", "skills": ["database-seed"], "dependencies": ["prisma/schema.prisma"]})
        
        for i, s in enumerate(steps):
            s["order"] = i + 1
        
        deps_content = _preload_dependencies(workspace_path, steps)
        from app.agents.developer_v2.src.nodes.parallel_utils import group_steps_by_layer, should_use_parallel
        layers = group_steps_by_layer(steps)
        
        return {**state, "task_type": "feature", "complexity": "medium" if len(steps) <= 5 else "high", "implementation_plan": steps, "dependencies_content": deps_content, "total_steps": len(steps), "current_step": 0, "skill_registry": skill_registry, "parallel_layers": {float(k): [s.get("file_path") for s in v] for k, v in layers.items()}, "can_parallel": should_use_parallel(steps), "action": "IMPLEMENT"}
    except Exception as e:
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
