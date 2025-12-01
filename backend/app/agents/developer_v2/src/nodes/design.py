"""Design node - Create technical design and save to workspace."""
import logging
from langchain_core.messages import HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.tools.filesystem_tools import write_file_safe
from app.agents.developer_v2.src.utils.llm_utils import get_langfuse_config as _cfg
from app.agents.developer_v2.src.nodes._llm import code_llm
from app.agents.developer_v2.src.nodes._helpers import setup_tool_context

logger = logging.getLogger(__name__)


async def design(state: DeveloperState, agent=None) -> DeveloperState:
    """Create technical design based on analysis."""
    print("[NODE] design")
    
    try:
        workspace_path = state.get("workspace_path", "")
        project_id = state.get("project_id")
        task_id = state.get("task_id") or state.get("story_id")
        
        setup_tool_context(workspace_path, project_id, task_id)
        
        analysis = state.get("analysis_result", {})
        story_title = state.get("story_title", "")
        story_content = state.get("story_content", "")
        acceptance_criteria = state.get("acceptance_criteria", [])
        
        prompt = f"""Create a technical design for this story.

## Story: {story_title}
{story_content}

## Acceptance Criteria
{chr(10).join(f'- {ac}' for ac in acceptance_criteria) if acceptance_criteria else 'None specified'}

## Analysis
- Task Type: {analysis.get('task_type', 'feature')}
- Complexity: {analysis.get('complexity', 'medium')}
- Affected Files: {', '.join(analysis.get('affected_files', [])) or 'TBD'}
- Suggested Approach: {analysis.get('suggested_approach', '')}

Create a concise technical design covering:
1. **Architecture Overview** - High-level approach
2. **Components** - Files/modules to create or modify
3. **Data Flow** - How data moves through the system
4. **API Design** - Endpoints if applicable
5. **Dependencies** - External packages or internal modules needed

Output as Markdown."""

        response = await code_llm.ainvoke(
            [HumanMessage(content=prompt)],
            config=_cfg(state, "design")
        )
        design_doc = response.content
        
        logger.info(f"[design] Generated design: {len(design_doc)} chars")
        
        # Save to workspace file
        if workspace_path:
            design_file = "docs/design.md"
            try:
                content = f"# Technical Design: {story_title}\n\n{design_doc}"
                result = write_file_safe.invoke({
                    "file_path": design_file,
                    "content": content,
                    "mode": "w"
                })
                logger.info(f"[design] {result}")
            except Exception as e:
                logger.warning(f"[design] Failed to save design file: {e}")
        
        return {
            **state,
            "design_doc": design_doc,
            "action": "PLAN",
        }
        
    except Exception as e:
        logger.error(f"[design] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
