"""
Copy Boilerplate Node - DEPRECATED

DEPRECATED: Node này không còn được sử dụng.
Repository creation từ template giờ được xử lý bởi GitHub Template Repository API.

Copy boilerplate template cho new projects sử dụng external file tools.
"""

import json
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import ImplementorState
from ..tool.external_file_tools import copy_directory_from_external_tool


def copy_boilerplate(state: ImplementorState) -> ImplementorState:
    """
    Copy boilerplate template cho new project.

    Args:
        state: ImplementorState với boilerplate template info

    Returns:
        Updated ImplementorState với boilerplate copy status
    """
    try:
        # DEPRECATED: Always skip boilerplate copy
        # Repository creation from template handled by GitHub Template Repository API
        print("⏭️  Skipping boilerplate copy - using GitHub Template Repository API")
        state.current_phase = "install_dependencies"
        return state

        print(f"📋 Copying boilerplate template: {state.boilerplate_template}")

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Construct source path to boilerplate template
        # Templates are in services/ai-agent-service/app/templates/boilerplate/
        template_base = Path("app/templates/boilerplate")
        source_path = str(template_base / state.boilerplate_template)

        # Copy boilerplate template to working directory
        result = copy_directory_from_external_tool.invoke(
            {
                "source_path": source_path,
                "destination_path": ".",  # Copy to root of working directory
                "working_directory": working_dir,
                "overwrite": False,  # Don't overwrite existing files
                "exclude_patterns": [
                    ".git",
                    "__pycache__",
                    "*.pyc",
                    ".env",
                    "node_modules",
                ],
            }
        )

        # Parse result
        result_data = json.loads(result)

        if result_data.get("status") == "success":
            # Record copied files
            copied_files = result_data.get("files_copied", [])
            state.files_created.extend(copied_files)

            # Store result in tools output
            state.tools_output["boilerplate_copy"] = result_data

            # Update status
            state.current_phase = "implement_files"
            state.status = "boilerplate_copied"

            # Add message
            message = AIMessage(
                content=f"✅ Boilerplate template copied successfully\n"
                f"- Template: {state.boilerplate_template}\n"
                f"- Files copied: {len(copied_files)}\n"
                f"- Next: Implement custom files"
            )
            state.messages.append(message)

            print(f"✅ Boilerplate copied - {len(copied_files)} files")

        else:
            # Handle error
            error_msg = result_data.get("message", "Unknown error copying boilerplate")
            state.error_message = f"Boilerplate copy failed: {error_msg}"
            state.status = "error"

            # Add error message
            message = AIMessage(content=f"❌ Failed to copy boilerplate: {error_msg}")
            state.messages.append(message)

            print(f"❌ Boilerplate copy failed: {error_msg}")

        return state

    except Exception as e:
        state.error_message = f"Boilerplate copy failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Boilerplate copy error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Boilerplate copy failed: {e}")
        return state
