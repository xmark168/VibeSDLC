"""Design node - Create technical design and save to workspace."""
import logging
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.developer_v2.src.state import DeveloperState
from app.agents.developer_v2.src.schemas import SystemDesign
from app.agents.developer_v2.src.tools.filesystem_tools import read_file_safe, list_directory_safe, write_file_safe
from app.agents.developer_v2.src.tools.shell_tools import semantic_code_search
from app.agents.developer_v2.src.utils.llm_utils import (
    get_langfuse_config as _cfg,
    execute_llm_with_tools as _llm_with_tools,
)
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

First, explore the codebase to understand existing patterns using the tools.
Then create a concise technical design with:
1. data_structures: Class/interface definitions in mermaid classDiagram format
2. api_interfaces: API endpoints and methods
3. call_flow: Sequence diagram in mermaid sequenceDiagram format
4. design_notes: Important design decisions
5. file_structure: List of files to create or modify"""

        # Exploration phase - gather context from codebase
        tools = [read_file_safe, list_directory_safe, semantic_code_search]
        
        messages = [
            SystemMessage(content="You are a software architect. Use the tools to explore the codebase and understand existing patterns before creating the design."),
            HumanMessage(content=prompt)
        ]
        
        exploration = await _llm_with_tools(
            llm=code_llm,
            tools=tools,
            messages=messages,
            state=state,
            name="design_explore",
            max_iterations=2
        )
        
        # Structured output phase
        messages.append(HumanMessage(content=f"Context gathered:\n{exploration[:3000]}\n\nNow create the technical design."))
        structured_llm = code_llm.with_structured_output(SystemDesign)
        design_result = await structured_llm.ainvoke(messages, config=_cfg(state, "design"))
        
        design_doc = f"""## Data Structures
{design_result.data_structures or 'N/A'}

## API Interfaces
{design_result.api_interfaces or 'N/A'}

## Call Flow
{design_result.call_flow or 'N/A'}

## Design Notes
{design_result.design_notes or 'N/A'}

## Files
{chr(10).join(f'- {f}' for f in design_result.file_structure) if design_result.file_structure else 'TBD'}"""
        
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
