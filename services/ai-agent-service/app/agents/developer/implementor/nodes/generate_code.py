"""
Generate Code Node

Generate actual code content cho files_to_create và files_to_modify sử dụng LLM.
"""

import json
import os
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import read_file_tool

# Helper function to extract actual content from read_file_tool output


def _extract_actual_content(formatted_content: str) -> str:
    """
    Extract actual file content from read_file_tool output (cat -n format).

    Args:
        formatted_content: Content with line numbers from read_file_tool

    Returns:
        Actual file content without line numbers
    """
    lines = formatted_content.splitlines()
    actual_lines = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            actual_lines.append("")
            continue

        # Extract content after line number and tab
        # Format: "     1\tclass UserService:"
        if "\t" in line:
            actual_content = line.split("\t", 1)[1]
            actual_lines.append(actual_content)
        else:
            # Fallback for lines without tab
            actual_lines.append(line)

    return "\n".join(actual_lines)


def _has_line_numbers(content: str) -> bool:
    """
    Check if content has line numbers (cat -n format).

    Args:
        content: Content to check

    Returns:
        True if content appears to have line numbers
    """
    lines = content.splitlines()
    line_number_count = 0

    for line in lines[:10]:  # Check first 10 lines
        if line.strip():
            # Check if line starts with spaces followed by number and tab
            # Format: "     1\tclass UserService:"
            stripped = line.lstrip()
            if stripped and "\t" in line:
                before_tab = line.split("\t")[0]
                if before_tab.strip().isdigit():
                    line_number_count += 1

    # If more than 50% of non-empty lines have line numbers, consider it formatted
    return line_number_count >= 3


def generate_code(state: ImplementorState) -> ImplementorState:
    """
    Generate actual code content cho tất cả files trong implementation plan.

    Args:
        state: ImplementorState với files_to_create và files_to_modify

    Returns:
        Updated ImplementorState với populated file content
    """
    try:
        print("🤖 Generating code content...")

        # Import prompts

        # Initialize LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        # Determine working directory
        working_dir = state.codebase_path or "."

        # Prepare context
        task_context = _prepare_task_context(state)
        codebase_context = _prepare_codebase_context(state, working_dir)

        # Generate code for files to create
        files_generated = 0
        files_failed = 0

        for file_change in state.files_to_create:
            try:
                print(f"  📝 Generating: {file_change.file_path}")

                generated_content = _generate_new_file_content(
                    llm, file_change, task_context, codebase_context, working_dir
                )

                if generated_content:
                    file_change.content = generated_content
                    files_generated += 1
                    print(f"    ✅ Generated {len(generated_content)} chars")
                else:
                    files_failed += 1
                    print("    ❌ Failed to generate content")

            except Exception as e:
                files_failed += 1
                print(f"    ❌ Error generating {file_change.file_path}: {e}")

        # Generate code for files to modify
        for file_change in state.files_to_modify:
            try:
                print(f"  ✏️  Modifying: {file_change.file_path}")

                generated_content = _generate_file_modification(
                    llm,
                    file_change,
                    task_context,
                    codebase_context,
                    working_dir,
                    state.tech_stack,
                )

                if generated_content:
                    file_change.content = generated_content
                    files_generated += 1
                    print("    ✅ Generated modification")
                else:
                    files_failed += 1
                    print("    ❌ Failed to generate modification")

            except Exception as e:
                files_failed += 1
                print(f"    ❌ Error modifying {file_change.file_path}: {e}")

        # Update state
        state.tools_output["code_generation"] = {
            "files_generated": files_generated,
            "files_failed": files_failed,
            "total_files": len(state.files_to_create) + len(state.files_to_modify),
        }

        # Determine status
        if files_failed == 0:
            state.status = "code_generated"
            state.current_phase = "implement_files"
        elif files_generated > 0:
            state.status = "code_partially_generated"
            state.current_phase = "implement_files"
            state.error_message = f"Failed to generate {files_failed} files"
        else:
            state.status = "error"
            state.error_message = "Failed to generate any code content"

        # Add message
        message = AIMessage(
            content=f"🤖 Code generation completed\n"
            f"- Files generated: {files_generated}\n"
            f"- Files failed: {files_failed}\n"
            f"- Success rate: {files_generated / (files_generated + files_failed) * 100:.1f}%\n"
            f"- Next: Implement files"
        )
        state.messages.append(message)

        print(
            f"✅ Code generation completed - {files_generated} files generated, {files_failed} failed"
        )

        return state

    except Exception as e:
        state.error_message = f"Code generation failed: {str(e)}"
        state.status = "error"

        message = AIMessage(content=f"❌ Code generation error: {str(e)}")
        state.messages.append(message)

        print(f"❌ Code generation failed: {e}")
        return state


def _select_prompt_based_on_tech_stack(tech_stack: str, prompt_type: str) -> str:
    """
    Select appropriate prompt based on tech stack and prompt type.

    Args:
        tech_stack: Technology stack (e.g., "fastapi", "react", "nextjs")
        prompt_type: Type of prompt ("creation" or "modification")

    Returns:
        Selected prompt string
    """
    if not tech_stack:
        # Fallback to generic prompts
        if prompt_type == "creation":
            from ..utils.prompts import GENERIC_FILE_CREATION_PROMPT

            return GENERIC_FILE_CREATION_PROMPT
        else:
            from ..utils.prompts import GENERIC_FILE_MODIFICATION_PROMPT

            return GENERIC_FILE_MODIFICATION_PROMPT

    tech_stack_lower = tech_stack.lower()

    # Backend tech stacks
    backend_stacks = [
        "fastapi",
        "django",
        "express",
        "nodejs",
        "python",
        "flask",
        "rails",
        "spring",
        "laravel",
        "asp.net",
    ]

    # Frontend tech stacks
    frontend_stacks = [
        "react",
        "nextjs",
        "next.js",
        "vue",
        "react-vite",
        "angular",
        "svelte",
        "nuxt",
        "gatsby",
        "vite",
    ]

    # Determine if backend or frontend
    is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
    is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)

    if is_backend:
        if prompt_type == "creation":
            from ..utils.prompts import BACKEND_FILE_CREATION_PROMPT

            return BACKEND_FILE_CREATION_PROMPT
        else:
            from ..utils.prompts import BACKEND_FILE_MODIFICATION_PROMPT

            return BACKEND_FILE_MODIFICATION_PROMPT
    elif is_frontend:
        if prompt_type == "creation":
            from ..utils.prompts import FRONTEND_FILE_CREATION_PROMPT

            return FRONTEND_FILE_CREATION_PROMPT
        else:
            from ..utils.prompts import FRONTEND_FILE_MODIFICATION_PROMPT

            return FRONTEND_FILE_MODIFICATION_PROMPT
    else:
        # Fallback to generic prompts for unknown tech stacks
        if prompt_type == "creation":
            from ..utils.prompts import GENERIC_FILE_CREATION_PROMPT

            return GENERIC_FILE_CREATION_PROMPT
        else:
            from ..utils.prompts import GENERIC_FILE_MODIFICATION_PROMPT

            return GENERIC_FILE_MODIFICATION_PROMPT


def _prepare_task_context(state: ImplementorState) -> str:
    """Prepare comprehensive task context for code generation from nested plan."""
    context = f"Task: {state.task_description}\n"
    context += f"Tech Stack: {state.tech_stack}\n"

    # Note: Always working with existing project in sandbox
    context += "Project Type: Existing project (in sandbox)\n"

    # Extract rich context from nested implementation plan
    plan = state.implementation_plan

    # Add requirements context if available
    if "requirements" in plan:
        requirements = plan["requirements"]

        if "functional_requirements" in requirements:
            func_reqs = "\n".join(
                f"- {req}" for req in requirements["functional_requirements"]
            )
            context += f"\nFunctional Requirements:\n{func_reqs}\n"

        if "technical_specs" in requirements:
            tech_specs = requirements["technical_specs"]
            if isinstance(tech_specs, dict):
                specs_text = "\n".join(f"- {k}: {v}" for k, v in tech_specs.items())
                context += f"\nTechnical Specifications:\n{specs_text}\n"

        if "constraints" in requirements:
            constraints = requirements["constraints"]
            if isinstance(constraints, list):
                constraints_text = "\n".join(
                    f"- {constraint}" for constraint in constraints
                )
                context += f"\nConstraints:\n{constraints_text}\n"

    # Add implementation approach if available
    if "implementation" in plan:
        implementation = plan["implementation"]

        if "approach" in implementation:
            approach = implementation["approach"]
            if isinstance(approach, dict):
                if "strategy" in approach:
                    context += f"\nImplementation Strategy:\n{approach['strategy']}\n"
                if "pattern" in approach:
                    context += f"\nCode Patterns:\n{approach['pattern']}\n"

    return context


def _prepare_codebase_context(state: ImplementorState, working_dir: str) -> str:
    """Prepare codebase context for code generation."""
    context = f"Working Directory: {working_dir}\n"
    context += f"Base Branch: {state.base_branch}\n"
    context += f"Feature Branch: {state.feature_branch}\n"

    # Add information about existing files
    if state.files_created:
        context += f"Files already created: {', '.join(state.files_created[:5])}\n"

    return context


def _generate_new_file_content(
    llm: ChatOpenAI,
    file_change: FileChange,
    task_context: str,
    codebase_context: str,
    working_dir: str,
) -> str | None:
    """Generate content for a new file using template and context information."""
    try:
        file_path = file_change.file_path
        file_ext = Path(file_path).suffix

        # Extract template information from file_change description
        # Description may contain template reference from nested plan
        template_info = ""
        if hasattr(file_change, "description") and file_change.description:
            # Look for template references in description
            if "template" in file_change.description.lower():
                template_info = file_change.description
            elif "pattern" in file_change.description.lower():
                template_info = file_change.description

        # Build enhanced context with template information
        enhanced_context = task_context
        if template_info:
            enhanced_context += f"\nTemplate/Pattern Reference:\n{template_info}\n"

        # Look for similar files as templates based on file extension
        template_file = None
        if file_ext == ".py":
            # Look for similar Python files
            similar_patterns = [
                "app/services/",
                "app/models/",
                "app/api/",
                "src/",
                "lib/",
            ]
            for pattern in similar_patterns:
                if pattern in file_path:
                    template_file = f"Similar files in {pattern}"
                    break
        elif file_ext in [".js", ".ts"]:
            # Look for similar JavaScript/TypeScript files
            similar_patterns = [
                "src/",
                "lib/",
                "components/",
                "services/",
                "controllers/",
                "routes/",
            ]
            for pattern in similar_patterns:
                if pattern in file_path:
                    template_file = f"Similar files in {pattern}"
                    break

        # Select appropriate prompt based on tech stack
        tech_stack = (
            task_context.split("\n")[1].replace("Tech Stack: ", "")
            if "\n" in task_context
            else "Unknown"
        )
        selected_prompt = _select_prompt_based_on_tech_stack(tech_stack, "creation")

        # Format prompt
        prompt = selected_prompt.format(
            implementation_plan=task_context,
            file_path=file_path,
            file_specs=file_change.description or "New file implementation",
            tech_stack=tech_stack,
            project_type="existing_project",
        )

        # Call LLM
        response = llm.invoke(prompt)
        raw_response = response.content.strip()

        # Clean LLM response to extract pure code
        generated_code = _clean_llm_response(raw_response)

        # Basic validation
        if generated_code and _validate_generated_code(generated_code, file_ext):
            return generated_code
        else:
            print(f"    ⚠️ Generated code failed validation for {file_path}")
            return None

    except Exception as e:
        print(f"    ❌ Error generating new file content: {e}")
        return None


def _generate_file_modification(
    llm: ChatOpenAI,
    file_change: FileChange,
    task_context: str,
    codebase_context: str,
    working_dir: str,
    tech_stack: str = "Unknown",
) -> str | None:
    """Generate modification for an existing file."""
    try:
        # Read existing file content
        existing_content = ""
        try:
            read_result = read_file_tool.invoke(
                {
                    "file_path": file_change.file_path,
                    "working_directory": working_dir,
                }
            )
            if "File not found" not in read_result:
                # ✅ Extract actual content to remove line numbers before passing to LLM
                existing_content = _extract_actual_content(read_result)
        except:
            pass

        # Select appropriate prompt based on tech stack
        selected_prompt = _select_prompt_based_on_tech_stack(tech_stack, "modification")

        # Format prompt
        prompt = selected_prompt.format(
            current_content=existing_content or "File not found - will be created",
            modification_specs=file_change.description or "File modification",
            change_type=file_change.change_type,
            target_element=f"{file_change.target_class or ''}.{file_change.target_function or ''}".strip(
                "."
            ),
            tech_stack=tech_stack,
        )

        # Call LLM
        response = llm.invoke(prompt)
        raw_response = response.content.strip()

        # Clean LLM response to extract pure code
        generated_code = _clean_llm_response(raw_response)

        # Basic validation
        file_ext = Path(file_change.file_path).suffix
        if generated_code and _validate_generated_code(generated_code, file_ext):
            return generated_code
        else:
            print(
                f"    ⚠️ Generated modification failed validation for {file_change.file_path}"
            )
            return None

    except Exception as e:
        print(f"    ❌ Error generating file modification: {e}")
        return None


def _clean_llm_response(raw_response: str) -> str:
    """
    Clean LLM response to extract pure code content.
    Removes markdown formatting, explanations, line numbers, and other non-code text.
    """
    if not raw_response:
        return ""

    # First check if response contains line numbers (cat -n format)
    # If so, extract actual content first
    if _has_line_numbers(raw_response):
        raw_response = _extract_actual_content(raw_response)

    # Remove common explanation patterns
    lines = raw_response.splitlines()
    cleaned_lines = []
    in_code_block = False
    code_block_started = False

    for line in lines:
        # Skip explanation lines before code
        if not code_block_started and any(
            phrase in line.lower()
            for phrase in [
                "here's",
                "here is",
                "implementation",
                "complete",
                "meets the",
                "requirements",
                "this implementation",
                "the following",
            ]
        ):
            continue

        # Detect code block start
        if line.strip().startswith("```"):
            if not in_code_block:
                in_code_block = True
                code_block_started = True
                continue
            else:
                # End of code block
                break

        # If we're in a code block, collect the line
        if in_code_block:
            cleaned_lines.append(line)
        # If no code blocks detected, assume entire response is code
        elif not code_block_started:
            # Skip obvious explanation lines
            if not any(
                phrase in line.lower()
                for phrase in [
                    "here's",
                    "here is",
                    "implementation",
                    "complete",
                    "meets the",
                    "requirements",
                    "this implementation",
                    "the following",
                    "```",
                ]
            ):
                cleaned_lines.append(line)

    # Join and clean up
    cleaned_code = "\n".join(cleaned_lines).strip()

    # If we got nothing, try to extract from the original response
    if not cleaned_code and raw_response:
        # Look for Python code patterns
        if (
            "def " in raw_response
            or "class " in raw_response
            or "import " in raw_response
        ):
            # Try to extract everything after the first import/def/class
            for line in lines:
                if any(
                    pattern in line
                    for pattern in ["import ", "from ", "def ", "class ", "@"]
                ):
                    start_idx = lines.index(line)
                    cleaned_code = "\n".join(lines[start_idx:]).strip()
                    break

    return cleaned_code


def _validate_generated_code(code: str, file_ext: str) -> bool:
    """Basic validation of generated code."""
    if not code or len(code.strip()) < 10:
        return False

    # Basic syntax checks based on file type
    if file_ext == ".py":
        # Check for basic Python syntax indicators
        return (
            any(keyword in code for keyword in ["def ", "class ", "import ", "from "])
            or "=" in code
        )
    elif file_ext in [".js", ".ts", ".jsx", ".tsx"]:
        # Check for basic JavaScript/TypeScript syntax
        return (
            any(
                keyword in code
                for keyword in [
                    "function",
                    "const ",
                    "let ",
                    "var ",
                    "class ",
                    "import ",
                    "export ",
                ]
            )
            or "{" in code
        )
    elif file_ext in [".json"]:
        # Try to parse JSON
        try:
            json.loads(code)
            return True
        except:
            return False

    # For other file types, just check it's not empty
    return len(code.strip()) > 0
