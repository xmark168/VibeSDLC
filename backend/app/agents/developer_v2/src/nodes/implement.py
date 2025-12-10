"""Implement node - Direct file output without tools."""
import json
import logging
import os
import re
import subprocess
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import ImplementOutput
from app.agents.developer_v2.src.tools.filesystem_tools import get_modified_files, reset_modified_files, _modified_files
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.utils.prompt_utils import format_input_template as _format_input_template, build_system_prompt as _build_system_prompt
from app.agents.developer_v2.src.utils.token_utils import truncate_to_tokens
from app.agents.developer_v2.src.nodes._llm import code_llm, get_llm_for_skills
from app.agents.developer_v2.src.skills import SkillRegistry, get_project_structure
from app.agents.developer_v2.src.config import MAX_CONCURRENT, MAX_DEBUG_REVIEWS

logger = logging.getLogger(__name__)


def _build_modified_files_context(files_modified: list) -> str:
    return "\n".join(f"- {f}" for f in files_modified) if files_modified else "None"


def _build_dependencies_context(dependencies_content: dict, step_dependencies: list, workspace_path: str = "", exclude_file: str = "") -> str:
    parts = []
    loaded = set()
    for dep in (step_dependencies or []):
        if not isinstance(dep, str) or dep == exclude_file:
            continue
        content = dependencies_content.get(dep)
        if not content and workspace_path:
            fp = os.path.join(workspace_path, dep)
            if os.path.exists(fp):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    pass
        if content:
            parts.append(f"### {dep}\n```\n{content[:5000]}\n```")
            loaded.add(dep)
    for dep in ["prisma/schema.prisma"]:
        if dep not in loaded and dep != exclude_file:
            if workspace_path and os.path.exists(os.path.join(workspace_path, dep)):
                try:
                    with open(os.path.join(workspace_path, dep), 'r', encoding='utf-8') as f:
                        parts.append(f"### {dep}\n```\n{f.read()}\n```")
                except:
                    pass
            elif dep in dependencies_content:
                parts.append(f"### {dep}\n```\n{dependencies_content[dep]}\n```")
    return f"<pre_loaded_context>\n{chr(10).join(parts)}\n</pre_loaded_context>" if parts else ""


def _build_debug_summary(state: dict) -> str:
    debug_count, review_count = state.get("debug_count", 0), state.get("review_count", 0)
    if debug_count == 0 and review_count == 0:
        return ""
    parts = ["## Debug Summary"]
    if debug_count > 0:
        parts.append(f"- Debug: {debug_count}, React: {state.get('react_loop_count', 0)}")
    if review_count > 0:
        parts.append(f"- Review: {review_count}")
        if state.get("review_feedback"):
            parts.append(f"- Feedback:\n```\n{state.get('review_feedback')[:500]}\n```")
    if state.get("error"):
        parts.append(f"- Error: {state.get('error')[:300]}")
    parts.append("\nDon't repeat mistakes.")
    return "\n".join(parts)


def _parse_implement_output(content: str) -> Optional[ImplementOutput]:
    if not content:
        return None
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    try:
        return ImplementOutput(**json.loads(match.group(1) if match else content.strip()))
    except:
        return None


def _preload_skills(registry: SkillRegistry, skill_ids: list[str], include_bundled: bool = True) -> str:
    if not skill_ids:
        return ""
    parts = []
    for sid in skill_ids:
        skill = registry.get_skill(sid)
        if not skill:
            continue
        content = skill.load_content()
        if not content:
            continue
        if include_bundled:
            for bf in skill.list_bundled_files():
                bf_content = skill.load_bundled_file(bf)
                if bf_content:
                    content += f"\n\n### Reference: {bf}\n{bf_content}"
        parts.append(f"## Skill: {sid}\n{content}")
    return "\n\n---\n\n".join(parts)


async def implement(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute implementation step with preloaded skills."""
    reset_modified_files()
    current_step, total_steps = state.get("current_step", 0), state.get("total_steps", 0)
    logger.debug(f"[NODE] implement {current_step + 1}/{total_steps}")
    
    debug_count = state.get("debug_count", 0)
    is_debug = state.get("task_type") == "bug_fix" or debug_count > 0
    prev_step = state.get("_last_implement_step", -1)
    review_count = state.get("review_count", 0) if is_debug else (0 if current_step != prev_step else state.get("review_count", 0))
    
    if is_debug and review_count >= MAX_DEBUG_REVIEWS:
        return {**state, "review_count": review_count, "action": "VALIDATE"}
    
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        tech_stack = state.get("tech_stack", "nextjs")
        react_loop = state.get("react_loop_count", 0)
        
        if state.get("react_mode") and state.get("run_status") == "FAIL":
            current_step = 0
            react_loop += 1
        
        if not plan_steps:
            return {**state, "error": "No plan", "action": "RESPOND"}
        if current_step >= len(plan_steps):
            return {**state, "message": "Done", "action": "VALIDATE"}
        
        step = plan_steps[current_step]
        task = step.get("task", step.get("description", ""))
        file_path = step.get("file_path", "")
        action = step.get("action", "")
        step_deps = step.get("dependencies", [])
        step_skills = step.get("skills", [])
        
        # Notify user - starting step
        if agent and file_path:
            try:
                from uuid import UUID
                story_id = state.get("story_id", "")
                if story_id:
                    story_uuid = UUID(story_id) if isinstance(story_id, str) else story_id
                    task_short = task[:80] + "..." if len(task) > 80 else task
                    await agent.message_story(
                        story_uuid,
                        f"⚙️ [{current_step + 1}/{len(plan_steps)}] {action.upper()} `{file_path}`\n   → {task_short}",
                        message_type="progress"
                    )
            except Exception:
                pass
        
        if "frontend-design" in step_skills and "frontend-component" not in step_skills:
            step_skills = step_skills + ["frontend-component"]
        
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        skills_content = _preload_skills(skill_registry, step_skills)
        
        deps_context = _build_dependencies_context(state.get("dependencies_content", {}), step_deps, workspace_path, file_path)
        context_parts = [deps_context] if deps_context else []
        
        feedback = ""
        if state.get("review_feedback"):
            feedback += f"<review_feedback>\n{state.get('review_feedback')}\n</review_feedback>"
        if state.get('run_stderr'):
            feedback += f"\n<errors>\n{state.get('run_stderr')[:2000]}\n</errors>"
        debug_summary = _build_debug_summary(state)
        if debug_summary:
            feedback += f"\n\n{debug_summary}"
        
        if is_debug and "debugging" not in step_skills:
            debug_content = _preload_skills(skill_registry, ["debugging"])
            if debug_content:
                skills_content = f"{skills_content}\n\n---\n\n{debug_content}" if skills_content else debug_content
        
        legacy_code = "None (new file)"
        if action == "modify" and file_path:
            fp = os.path.join(workspace_path, file_path)
            if os.path.exists(fp):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        legacy_code = f.read()
                except:
                    pass
        
        input_text = _format_input_template("implement_step", step_number=current_step + 1, total_steps=len(plan_steps), task_description=f"[{action.upper()}] {file_path}\n{task}" if file_path else task, modified_files=_build_modified_files_context(state.get("files_modified", [])), related_context=truncate_to_tokens("\n\n".join(context_parts), 4000), feedback_section=feedback, logic_analysis="", legacy_code=legacy_code, debug_logs=state.get("error", "")[:2000] if state.get("error") else "")
        
        system_prompt = _build_system_prompt("implement_step", skills_content=skills_content)
        response = await get_llm_for_skills(step_skills).ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=input_text)], config=_cfg(state, "implement_code"))
        
        output = _parse_implement_output(response.content or "")
        if output and file_path:
            fp = os.path.join(workspace_path, file_path)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(output.content)
            _modified_files.add(file_path)
            logger.debug(f"[implement] {action.upper()} {file_path}")
        elif not output and response.content and file_path:
            match = re.search(r'```(?:typescript|tsx|javascript|jsx|python|prisma)?\s*([\s\S]*?)\s*```', response.content)
            if match:
                fp = os.path.join(workspace_path, file_path)
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                with open(fp, 'w', encoding='utf-8') as f:
                    f.write(match.group(1))
                _modified_files.add(file_path)
        
        new_modified = get_modified_files()
        if any(f.replace("\\", "/").endswith("schema.prisma") for f in new_modified):
            try:
                subprocess.run("pnpm exec prisma generate", cwd=workspace_path, shell=True, capture_output=True, timeout=60)
                subprocess.run("pnpm exec prisma db push --accept-data-loss", cwd=workspace_path, shell=True, capture_output=True, timeout=60)
                seed_file = Path(workspace_path) / "prisma" / "seed.ts"
                if seed_file.exists():
                    subprocess.run("pnpm exec ts-node prisma/seed.ts", cwd=workspace_path, shell=True, capture_output=True, timeout=60)
            except:
                pass
        
        all_modified = list(set(state.get("files_modified", []) + new_modified))
        deps = state.get("dependencies_content", {})
        for f in new_modified:
            norm = f.replace("\\", "/")
            if norm in deps or norm in ["prisma/schema.prisma", "src/types/index.ts"]:
                fp = os.path.join(workspace_path, norm)
                if os.path.exists(fp):
                    try:
                        with open(fp, "r", encoding="utf-8") as fl:
                            deps[norm] = fl.read()
                    except:
                        pass
        
        complexity = state.get("complexity", "medium")
        next_step = current_step + 1 if complexity == "low" else current_step
        
        return {**state, "current_step": next_step, "_last_implement_step": current_step, "react_loop_count": react_loop, "debug_count": debug_count, "review_count": review_count, "run_status": None, "skill_registry": skill_registry, "files_modified": all_modified, "dependencies_content": deps, "action": "IMPLEMENT" if next_step < len(plan_steps) else "VALIDATE"}
    except Exception as e:
        logger.error(f"[implement] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}


from app.agents.developer_v2.src.nodes.parallel_utils import group_steps_by_layer, run_layer_parallel, should_use_parallel, MAX_CONCURRENT


async def _implement_single_step(step: Dict, state: DeveloperState, skill_registry: SkillRegistry, workspace_path: str, deps_content: Dict, created_components: Dict[str, str] = None) -> Dict:
    file_path = step.get("file_path", "")
    task = step.get("task", step.get("description", ""))
    action = step.get("action", "")
    step_skills = step.get("skills", [])
    
    try:
        if "frontend-design" in step_skills and "frontend-component" not in step_skills:
            step_skills = step_skills + ["frontend-component"]
        
        skills_content = _preload_skills(skill_registry, step_skills)
        context_parts = []
        deps_ctx = _build_dependencies_context(deps_content, step.get("dependencies", []), workspace_path, file_path)
        if deps_ctx:
            context_parts.append(deps_ctx)
        if created_components:
            hints = ["## Component Imports"]
            for name, path in sorted(created_components.items()):
                hints.append(f"- {name}: `import {{ {name} }} from '{path}'`")
            context_parts.append("\n".join(hints))
        
        legacy = ""
        if action == "modify" and file_path:
            fp = os.path.join(workspace_path, file_path)
            if os.path.exists(fp):
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        legacy = f.read()
                except:
                    pass
        
        input_text = _format_input_template("implement_step", step_number=step.get("order", 1), total_steps=state.get("total_steps", 1), task_description=f"[{action.upper()}] {file_path}\n{task}" if file_path else task, modified_files="", related_context="\n\n".join(context_parts), feedback_section="", logic_analysis="", legacy_code=legacy, debug_logs="")
        
        response = await get_llm_for_skills(step_skills).ainvoke([SystemMessage(content=_build_system_prompt("implement_step", skills_content=skills_content)), HumanMessage(content=input_text)], config=_cfg(state, f"impl_{file_path}"))
        output = _parse_implement_output(response.content or "")
        
        if output and file_path:
            fp = os.path.join(workspace_path, file_path)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(output.content)
            return {"file_path": file_path, "success": True, "modified_files": [file_path]}
        return {"file_path": file_path, "success": False, "error": "No output"}
    except Exception as e:
        return {"file_path": file_path, "success": False, "error": str(e)}


async def implement_parallel(state: DeveloperState, agent=None) -> DeveloperState:
    """Execute steps in parallel by layer."""
    logger.debug("[NODE] implement_parallel")
    try:
        plan_steps = state.get("implementation_plan", [])
        workspace_path = state.get("workspace_path", "")
        tech_stack = state.get("tech_stack", "nextjs")
        
        if not plan_steps:
            return {**state, "error": "No plan", "action": "RESPOND"}
        
        skill_registry = state.get("skill_registry") or SkillRegistry.load(tech_stack)
        deps_content = dict(state.get("dependencies_content", {}))
        layers = group_steps_by_layer(plan_steps)
        
        all_modified, all_errors = [], []
        created_components = {}
        for step in plan_steps:
            fp = step.get("file_path", "")
            if "/components/" in fp and fp.endswith(".tsx"):
                created_components[os.path.basename(fp).replace(".tsx", "")] = "@/" + fp.replace(".tsx", "")
        
        for layer_num in sorted(layers.keys()):
            layer_steps = layers[layer_num]
            is_parallel = len(layer_steps) > 1 and layer_num >= 5
            
            # Notify user - layer starting
            if agent:
                try:
                    from uuid import UUID
                    story_id = state.get("story_id", "")
                    if story_id:
                        story_uuid = UUID(story_id) if isinstance(story_id, str) else story_id
                        files_list = ", ".join([s.get("file_path", "").split("/")[-1] for s in layer_steps[:3]])
                        more = f" +{len(layer_steps)-3}" if len(layer_steps) > 3 else ""
                        await agent.message_story(
                            story_uuid,
                            f"⚙️ Layer {layer_num}/{len(layers)}: {files_list}{more}",
                            message_type="progress"
                        )
                except Exception:
                    pass
            
            if is_parallel:
                results = await run_layer_parallel(layer_steps, lambda s, c=created_components: _implement_single_step(s, state, skill_registry, workspace_path, deps_content, c), state, MAX_CONCURRENT)
            else:
                results = [await _implement_single_step(s, state, skill_registry, workspace_path, deps_content, created_components) for s in layer_steps]
            
            for r in results:
                if r.get("success"):
                    all_modified.extend(r.get("modified_files", []))
                elif r.get("error"):
                    all_errors.append(f"{r.get('file_path')}: {r.get('error')}")
            
            if layer_num == 1 and any("schema.prisma" in str(r.get("file_path", "")) for r in results):
                try:
                    subprocess.run("pnpm exec prisma generate", cwd=workspace_path, shell=True, capture_output=True, timeout=60)
                    subprocess.run("pnpm exec prisma db push --accept-data-loss", cwd=workspace_path, shell=True, capture_output=True, timeout=60)
                    sp = os.path.join(workspace_path, "prisma/schema.prisma")
                    if os.path.exists(sp):
                        with open(sp, 'r', encoding='utf-8') as f:
                            deps_content["prisma/schema.prisma"] = f.read()
                except:
                    pass
            elif layer_num == 2 and any("seed.ts" in str(r.get("file_path", "")) for r in results):
                seed = os.path.join(workspace_path, "prisma/seed.ts")
                if os.path.exists(seed):
                    try:
                        result = subprocess.run("pnpm exec ts-node prisma/seed.ts", cwd=workspace_path, shell=True, capture_output=True, text=True, timeout=60)
                        if result.returncode == 0:
                            Path(workspace_path, ".seed_cache").write_text(hashlib.md5(Path(seed).read_bytes()).hexdigest())
                    except:
                        pass
            elif layer_num == 3:
                tp = os.path.join(workspace_path, "src/types/index.ts")
                if os.path.exists(tp):
                    with open(tp, 'r', encoding='utf-8') as f:
                        deps_content["src/types/index.ts"] = f.read()
            elif layer_num >= 5:
                for r in results:
                    fp = r.get("file_path", "")
                    if fp and fp.endswith(".tsx"):
                        full = os.path.join(workspace_path, fp)
                        if os.path.exists(full):
                            try:
                                with open(full, 'r', encoding='utf-8') as f:
                                    deps_content[fp] = f.read()
                                if "/components/" in fp:
                                    created_components[os.path.basename(fp).replace(".tsx", "")] = "@/" + fp.replace(".tsx", "")
                            except:
                                pass
        
        return {**state, "current_step": len(plan_steps), "total_steps": len(plan_steps), "files_modified": list(set(all_modified)), "dependencies_content": deps_content, "parallel_errors": all_errors if all_errors else None, "message": f"Implemented {len(all_modified)} files ({len(layers)} layers)", "action": "VALIDATE"}
    except Exception as e:
        logger.error(f"[implement_parallel] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
