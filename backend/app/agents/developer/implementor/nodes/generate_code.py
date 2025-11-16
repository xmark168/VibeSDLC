"""
Generate Code Node

Generate actual code content cho files_to_create và files_to_modify sử dụng LLM.
"""

import json
import os
from pathlib import Path

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import read_file_tool

# Helper function to extract actual content from read_file_tool output


def _validate_old_code_size(llm_response: str, existing_content: str) -> dict:
    """
    Validate that OLD_CODE in LLM response is not too large (prevents full file replacement).

    Args:
        llm_response: Raw LLM response containing MODIFICATION blocks
        existing_content: Current file content

    Returns:
        Dict with 'valid' (bool) and 'reason' (str) keys
    """
    import re

    # Extract all OLD_CODE blocks
    old_code_blocks = re.findall(
        r"OLD_CODE:\s*```\w*\n(.*?)\n```", llm_response, re.DOTALL
    )

    if not old_code_blocks:
        return {"valid": True, "reason": "No OLD_CODE blocks found"}

    existing_size = len(existing_content)

    for i, old_code in enumerate(old_code_blocks):
        old_code_size = len(old_code.strip())

        # Calculate percentage of file being replaced
        replacement_ratio = old_code_size / existing_size if existing_size > 0 else 0

        # ⚠️ If OLD_CODE is more than 30% of file, it's likely full replacement
        if replacement_ratio > 0.3:
            return {
                "valid": False,
                "reason": f"OLD_CODE block #{i + 1} is {replacement_ratio * 100:.1f}% of file ({old_code_size}/{existing_size} chars). Max allowed: 30%",
            }

        # ⚠️ Also check if OLD_CODE contains too many lines (>50 lines is suspicious)
        old_code_lines = len(old_code.strip().split("\n"))
        if old_code_lines > 50:
            return {
                "valid": False,
                "reason": f"OLD_CODE block #{i + 1} has {old_code_lines} lines (max: 50). Use smaller, targeted modifications",
            }

    return {"valid": True, "reason": "OLD_CODE size validation passed"}


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


def generate_code(
    state: ImplementorState, config: RunnableConfig = None
) -> ImplementorState:
    """
    Generate actual code content cho tất cả files trong implementation plan.

    Args:
        state: ImplementorState với files_to_create và files_to_modify
        config: RunnableConfig with callbacks for LangFuse tracing

    Returns:
        Updated ImplementorState với populated file content
    """
    try:
        print("🤖 Generating code content...")

        # Initialize LLM (callbacks are automatically injected by LangGraph)
        llm = ChatOpenAI(
            model="gpt-4o",
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

                # Prepare codebase context with dependency info for this specific file
                file_specific_context = _prepare_codebase_context(
                    state, working_dir, file_change.file_path
                )

                generated_content = _generate_new_file_content(
                    llm, file_change, task_context, file_specific_context, working_dir
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

                # Prepare codebase context with dependency info for this specific file
                file_specific_context = _prepare_codebase_context(
                    state, working_dir, file_change.file_path
                )

                generated_content = _generate_file_modification(
                    llm,
                    file_change,
                    task_context,
                    file_specific_context,
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


def _prepare_codebase_context(
    state: ImplementorState, working_dir: str, file_path: str = ""
) -> str:
    """
    Prepare codebase context for code generation with dependency information.

    Args:
        state: ImplementorState with files_created
        working_dir: Working directory
        file_path: Current file path to identify dependencies

    Returns:
        Enhanced context string with dependency information
    """
    context = f"Working Directory: {working_dir}\n"
    context += f"Base Branch: {state.base_branch}\n"
    context += f"Feature Branch: {state.feature_branch}\n"

    # Add information about existing files
    if state.files_created:
        context += f"Files already created: {', '.join(state.files_created[:5])}\n"

    # ✅ NEW: Add dependency files API summary for API contract coordination
    if file_path:
        dependency_files = _identify_dependency_files(
            file_path, state.files_created, working_dir
        )
        if dependency_files:
            context += "\n" + "=" * 80 + "\n"
            context += "📚 DEPENDENCY FILES - API SUMMARY (API CONTRACT REFERENCE)\n"
            context += "=" * 80 + "\n\n"
            context += "⚠️ CRITICAL: Use EXACT method names, return types, and signatures from these files.\n"
            context += "Note: Implementation details are truncated for brevity. Focus on method signatures.\n\n"

            for dep_file in dependency_files:
                # Use smart truncation function
                dep_summary = _extract_dependency_api_summary(dep_file, working_dir)
                if dep_summary:
                    context += f"📄 File: {dep_file}\n"
                    context += f"```javascript\n{dep_summary}\n```\n\n"

            context += "=" * 80 + "\n\n"

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

        # SOLUTION 1: Append dependency context with strong reminder if available
        if codebase_context and "DEPENDENCY FILES" in codebase_context:
            prompt = f"""{prompt}

{codebase_context}

⚠️ ⚠️ ⚠️ CRITICAL REMINDER - READ CAREFULLY ⚠️ ⚠️ ⚠️

You MUST use the EXACT method names, signatures, and return types from the DEPENDENCY FILES shown above.

BEFORE writing any code that calls a dependency method:
1. Scroll up and find the dependency file in the "📚 DEPENDENCY FILES" section
2. Locate the EXACT method name in that file
3. Check the method's parameters and return type
4. Use the EXACT method name - do NOT invent, assume, or guess method names
5. Match the EXACT return type - if it returns {{user, token}}, destructure both properties

COMMON MISTAKES TO AVOID:
❌ Using 'validateUser' when dependency has 'loginUser'
❌ Using 'create' when dependency has 'createUser'
❌ Ignoring return type structure (e.g., not destructuring {{user, token}})
❌ Passing wrong parameter format (e.g., object when it expects individual params)

Double-check EVERY method call against the dependency API summary above before generating code.
If you're unsure about a method name, look it up in the dependency files - do NOT guess!
"""

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
        print(
            f"    🔍 DEBUG: Starting _generate_file_modification for {file_change.file_path}"
        )
        print(f"    🔍 DEBUG: Change type: {file_change.change_type}")
        print(f"    🔍 DEBUG: Tech stack: {tech_stack}")

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
        print("    🔍 DEBUG: Selecting prompt based on tech stack...")
        selected_prompt = _select_prompt_based_on_tech_stack(tech_stack, "modification")
        print("    🔍 DEBUG: Prompt selection completed")

        # Determine language based on file extension
        file_ext = Path(file_change.file_path).suffix
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
        }
        language = language_map.get(file_ext, "text")

        # Debug: Log current file content being passed to LLM
        print(
            f"    🔍 DEBUG: Current file content length: {len(existing_content)} chars"
        )
        if existing_content:
            print(f"    🔍 DEBUG: First 200 chars: {existing_content[:200]}...")
            print(f"    🔍 DEBUG: Last 200 chars: ...{existing_content[-200:]}")
            # Check for key patterns to verify file state
            if "/register" in existing_content:
                print("    🔍 DEBUG: Register endpoint found in current content")
            if "/login" in existing_content:
                print("    🔍 DEBUG: Login endpoint found in current content")
        else:
            print("    🔍 DEBUG: No existing content found")

        # Enhanced prompt formatting với sequential task context
        current_content_display = existing_content or "File not found - will be created"

        # Add sequential task context if file has existing content
        if existing_content and len(existing_content.strip()) > 0:
            lines = existing_content.split("\n")
            current_content_display = f"""
📋 FILE ANALYSIS:
- Total lines: {len(lines)}
- File size: {len(existing_content)} characters
- Contains existing code from previous tasks

{existing_content}

🎯 REMEMBER: This file already has functionality. ADD to it, don't replace it!
"""

        # Format prompt
        print("    🔍 DEBUG: Formatting prompt...")
        print(f"    🔍 DEBUG: Prompt template length: {len(selected_prompt)} chars")
        try:
            prompt = selected_prompt.format(
                current_content=current_content_display,
                modification_specs=file_change.description or "File modification",
                change_type=file_change.change_type,
                target_element=f"{file_change.target_class or ''}.{file_change.target_function or ''}".strip(
                    "."
                ),
                tech_stack=tech_stack,
                file_path=file_change.file_path,  # Add missing file_path parameter
                language=language,  # Add missing language parameter
            )
            print("    🔍 DEBUG: Prompt formatting completed")
            print(f"    🔍 DEBUG: Final prompt length: {len(prompt)} chars")
        except Exception as format_error:
            print(f"    ❌ DEBUG: Error in prompt formatting: {format_error}")
            raise

        # SOLUTION 1: Append dependency context with strong reminder if available
        if codebase_context and "DEPENDENCY FILES" in codebase_context:
            prompt = f"""{prompt}

{codebase_context}

⚠️ ⚠️ ⚠️ CRITICAL REMINDER - READ CAREFULLY ⚠️ ⚠️ ⚠️

You MUST use the EXACT method names, signatures, and return types from the DEPENDENCY FILES shown above.

BEFORE writing any code that calls a dependency method:
1. Scroll up and find the dependency file in the "📚 DEPENDENCY FILES" section
2. Locate the EXACT method name in that file
3. Check the method's parameters and return type
4. Use the EXACT method name - do NOT invent, assume, or guess method names
5. Match the EXACT return type - if it returns {{user, token}}, destructure both properties

COMMON MISTAKES TO AVOID:
❌ Using 'validateUser' when dependency has 'loginUser'
❌ Using 'create' when dependency has 'createUser'
❌ Ignoring return type structure (e.g., not destructuring {{user, token}})
❌ Passing wrong parameter format (e.g., object when it expects individual params)

Double-check EVERY method call against the dependency API summary above before generating code.
If you're unsure about a method name, look it up in the dependency files - do NOT guess!
"""
            print("    🔍 DEBUG: Appended dependency context with critical reminder")

        # Call LLM
        print("    🔍 DEBUG: Calling LLM...")
        try:
            response = llm.invoke(prompt)
            print("    🔍 DEBUG: LLM call completed")
            raw_response = response.content.strip()
            print(
                f"    🔍 DEBUG: Raw response extracted, length: {len(raw_response)} chars"
            )
        except Exception as llm_error:
            print(f"    ❌ DEBUG: Error in LLM call: {llm_error}")
            raise

        # Debug: Log LLM response
        print(f"    🔍 DEBUG: LLM response length: {len(raw_response)} chars")
        print(f"    🔍 DEBUG: LLM response first 500 chars: {repr(raw_response[:500])}")
        print(f"    🔍 DEBUG: LLM response last 200 chars: {repr(raw_response[-200:])}")

        # Check for error patterns in LLM response
        if "error" in raw_response.lower() or "failed" in raw_response.lower():
            print("    ⚠️ DEBUG: LLM response contains error keywords")

        # Check for specific error string
        if "existing register logic" in raw_response:
            print("    🎯 DEBUG: LLM response contains 'existing register logic'")
            print(f"    🔍 DEBUG: Full response: {repr(raw_response)}")

        # Check if LLM response is actually an error message
        if (
            raw_response.strip() == "\n  // existing register logic\n"
            or raw_response.strip() == "// existing register logic"
        ):
            print("    🚨 DEBUG: LLM response IS the error string!")
            print("    💡 DEBUG: LLM generated error message instead of code")
            raise Exception(raw_response.strip())

        if "MODIFICATION #" in raw_response:
            print("    🔍 DEBUG: Structured modifications format detected")
        else:
            print("    🔍 DEBUG: Non-structured format detected")

        # ✅ NEW APPROACH: Full-file regeneration
        # LLM should return complete file content, not OLD_CODE/NEW_CODE blocks
        print("    ✅ Using full-file regeneration approach")

        # Clean the response to extract pure code
        cleaned_response = _clean_llm_response(raw_response)

        if not cleaned_response or len(cleaned_response.strip()) == 0:
            print("    ❌ LLM response is empty after cleaning")
            return None

        # Validate that response looks like complete file content
        if existing_content:
            # Check if response preserves key elements from existing file
            existing_lines = existing_content.split("\n")
            response_lines = cleaned_response.split("\n")

            # Basic validation: new file should have reasonable length
            if len(response_lines) < len(existing_lines) * 0.5:
                print(
                    f"    ⚠️ Warning: Generated file ({len(response_lines)} lines) is significantly shorter than original ({len(existing_lines)} lines)"
                )
                print(
                    "    💡 This might indicate LLM didn't preserve all existing code"
                )
                # Don't reject, but log warning

            print(
                f"    ✅ Generated complete file: {len(response_lines)} lines (original: {len(existing_lines)} lines)"
            )
        else:
            print(
                f"    ✅ Generated new file: {len(cleaned_response.split(chr(10)))} lines"
            )

        # Return the complete file content
        return cleaned_response

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


# ============================================================================
# DEPENDENCY ANALYSIS HELPER FUNCTIONS
# Copied from execute_step.py for API contract consistency
# ============================================================================


def _identify_dependency_files(
    current_file: str, created_files: list, working_dir: str = None
) -> list:
    """
    Identify which previously created files are dependencies of current file.

    Strategy:
    1. Read current file content (if it exists)
    2. Parse import/require statements to extract dependency paths
    3. Match dependency paths with files in created_files
    4. Fallback to layered architecture pattern if file doesn't exist yet

    Args:
        current_file: File being generated
        created_files: List of files already created
        working_dir: Working directory to read file from

    Returns:
        List of dependency file paths
    """
    dependencies = []

    # Normalize path separators
    current_file = current_file.replace("\\", "/")
    created_files = [f.replace("\\", "/") for f in created_files]

    # Try to read current file and parse imports
    if working_dir:
        try:
            file_content = _read_file_for_imports(current_file, working_dir)
            if file_content:
                # Parse imports/requires from file content
                import_paths = _parse_import_statements(file_content)

                # Match import paths with created files
                for import_path in import_paths:
                    matched_files = _match_import_to_created_files(
                        import_path, current_file, created_files
                    )
                    dependencies.extend(matched_files)

                # Remove duplicates
                dependencies = list(set(dependencies))

                if dependencies:
                    return dependencies
        except Exception:
            # Fallback to pattern-based detection if parsing fails
            pass

    # FALLBACK: Use layered architecture pattern if file doesn't exist yet
    # or if import parsing failed
    dependencies = _identify_dependencies_by_pattern(current_file, created_files)

    return dependencies


def _read_file_for_imports(file_path: str, working_dir: str) -> str | None:
    """
    Read file content to parse imports. Returns None if file doesn't exist.

    Args:
        file_path: Path to file
        working_dir: Working directory

    Returns:
        File content or None
    """
    try:
        read_result = read_file_tool.invoke(
            {"file_path": file_path, "working_directory": working_dir}
        )

        if "File not found" in read_result or "does not exist" in read_result:
            return None

        # Extract actual content
        return _extract_actual_content(read_result)
    except Exception:
        return None


def _parse_import_statements(content: str) -> list:
    """
    Parse import/require statements from JavaScript/TypeScript file content.

    Extracts paths from:
    - require('path')
    - require("path")
    - import ... from 'path'
    - import ... from "path"

    Args:
        content: File content

    Returns:
        List of import paths
    """
    import re

    import_paths = []

    # Pattern 1: require('path') or require("path")
    require_pattern = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
    require_matches = re.findall(require_pattern, content)
    import_paths.extend(require_matches)

    # Pattern 2: import ... from 'path' or import ... from "path"
    import_pattern = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
    import_matches = re.findall(import_pattern, content)
    import_paths.extend(import_matches)

    # Pattern 3: import 'path' or import "path" (side-effect imports)
    import_side_effect_pattern = r"import\s+['\"]([^'\"]+)['\"]"
    import_side_effect_matches = re.findall(import_side_effect_pattern, content)
    import_paths.extend(import_side_effect_matches)

    return import_paths


def _match_import_to_created_files(
    import_path: str, current_file: str, created_files: list
) -> list:
    """
    Match an import path to files in created_files list.

    Handles relative imports like:
    - '../services/authService'
    - './helpers/validator'
    - '../../utils/formatter'

    Args:
        import_path: Import path from require/import statement
        current_file: Current file path
        created_files: List of created files

    Returns:
        List of matching file paths
    """

    matches = []

    # Skip node_modules and external packages
    if not import_path.startswith("."):
        return matches

    # Resolve relative import path
    current_dir = os.path.dirname(current_file)
    resolved_path = os.path.normpath(os.path.join(current_dir, import_path))
    resolved_path = resolved_path.replace("\\", "/")

    # Try to match with created files
    for created_file in created_files:
        created_normalized = created_file.replace("\\", "/")

        # Remove file extension from both paths for comparison
        created_without_ext = os.path.splitext(created_normalized)[0]
        resolved_without_ext = os.path.splitext(resolved_path)[0]

        # Check if paths match (with or without extension)
        if (
            created_without_ext == resolved_without_ext
            or created_normalized == resolved_path
            or created_without_ext.endswith(resolved_without_ext)
            or resolved_without_ext in created_without_ext
        ):
            matches.append(created_file)

    return matches


def _identify_dependencies_by_pattern(current_file: str, created_files: list) -> list:
    """
    FALLBACK: Identify dependencies using Express.js layered architecture pattern.

    This is used when:
    - File doesn't exist yet (being generated for first time)
    - Import parsing fails

    Express.js layered architecture:
    - Routes depend on Controllers
    - Controllers depend on Services
    - Services depend on Repositories
    - Repositories depend on Models

    Args:
        current_file: File being generated
        created_files: List of files already created

    Returns:
        List of dependency file paths
    """
    from pathlib import Path

    dependencies = []
    current_name = Path(current_file).stem

    # Controllers depend on Services
    if "/controllers/" in current_file:
        service_name = current_name.replace("Controller", "Service")
        for created in created_files:
            if "/services/" in created and service_name in created:
                dependencies.append(created)

    # Services depend on Repositories
    elif "/services/" in current_file:
        base_name = current_name.replace("Service", "")
        for created in created_files:
            if "/repositories/" in created:
                if base_name.lower() in created.lower() or "Repository" in created:
                    dependencies.append(created)

    # Repositories depend on Models
    elif "/repositories/" in current_file:
        base_name = current_name.replace("Repository", "")
        for created in created_files:
            if "/models/" in created:
                if base_name.lower() in created.lower():
                    dependencies.append(created)

    # Routes depend on Controllers
    elif "/routes/" in current_file:
        for created in created_files:
            if "/controllers/" in created and current_name in created.lower():
                dependencies.append(created)

    return dependencies


def _extract_dependency_api_summary(file_path: str, working_dir: str) -> str | None:
    """
    Extract API summary from dependency file by keeping signatures and minimal context.

    Smart truncation approach:
    - Keeps: Class/module declarations, method signatures, JSDoc comments
    - Keeps: First 2-3 lines of each method body (for context)
    - Keeps: Return statements
    - Removes: Detailed implementation logic
    - Adds: "// ... implementation details ..." placeholder
    - Limits: Maximum 60 lines per file

    Args:
        file_path: Path to dependency file
        working_dir: Working directory

    Returns:
        Truncated API summary or None if failed
    """
    try:
        # First, read the full file content
        read_result = read_file_tool.invoke(
            {"file_path": file_path, "working_directory": working_dir}
        )

        if "File not found" in read_result:
            return None

        # Extract actual content (remove line numbers if present)
        full_content = _extract_actual_content(read_result)

        # Apply smart truncation
        try:
            truncated = _truncate_to_api_summary(full_content)
            return truncated
        except Exception as truncate_error:
            print(
                f"      ⚠️ Truncation failed for {file_path}, using full content: {truncate_error}"
            )
            # Fallback to full content if truncation fails
            return full_content

    except Exception as e:
        print(f"      ⚠️ Could not read dependency file {file_path}: {e}")
        return None


def _truncate_to_api_summary(content: str, max_lines: int = 60) -> str:
    """
    Truncate file content to API summary by keeping signatures and minimal context.

    Strategy:
    - Keep class/module declarations
    - Keep method signatures
    - Keep first 2-3 lines of method body
    - Keep return statements
    - Replace detailed implementation with placeholder
    - Preserve JSDoc comments

    Args:
        content: Full file content
        max_lines: Maximum lines to keep (default: 60)

    Returns:
        Truncated content with API summary
    """
    lines = content.split("\n")
    summary_lines = []

    in_method = False
    method_body_lines = 0
    method_indent = 0
    method_start_line = 0
    seen_return = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        current_indent = len(line) - len(line.lstrip())

        # Skip empty lines in method bodies (but keep them elsewhere)
        if in_method and not stripped:
            continue

        # Keep JSDoc comments
        if (
            "/**" in stripped
            or (stripped.startswith("*") and not stripped.startswith("**"))
            or "*/" in stripped
        ):
            summary_lines.append(line)
            continue

        # Keep class declarations
        if stripped.startswith("class ") or "module.exports" in stripped:
            summary_lines.append(line)
            continue

        # Keep require/import statements
        if "require(" in stripped or "import " in stripped:
            summary_lines.append(line)
            continue

        # Detect method signatures (but NOT control flow statements)
        is_method_signature = False

        # Exclude control flow statements
        if not any(
            stripped.startswith(keyword)
            for keyword in [
                "if ",
                "if(",
                "for ",
                "for(",
                "while ",
                "while(",
                "switch ",
                "switch(",
                "catch ",
                "catch(",
            ]
        ):
            if any(
                pattern in stripped
                for pattern in [
                    "async ",
                    "function ",
                    ") {",
                    "(req, res)",
                    "(userData)",
                    "(email",
                    "(id",
                ]
            ):
                # Check if it looks like a method declaration
                if "(" in stripped and ("{" in stripped or stripped.endswith("{")):
                    is_method_signature = True

        # Start of method
        if is_method_signature and not in_method:
            summary_lines.append(line)
            in_method = True
            method_body_lines = 0
            method_indent = current_indent
            method_start_line = i
            seen_return = False
            continue

        # Inside method body
        if in_method:
            # ALWAYS keep return statements (CRITICAL for API contracts)
            if "return " in stripped:
                # Add placeholder before return if we skipped lines
                if method_body_lines >= 3 and not seen_return:
                    summary_lines.append(
                        " " * (method_indent + 2) + "// ... implementation details ..."
                    )
                summary_lines.append(line)
                seen_return = True
                method_body_lines += 1

            # Keep first 2-3 lines of method body (if not a return statement)
            elif method_body_lines < 3:
                summary_lines.append(line)
                method_body_lines += 1

            # Check if method ended (closing brace at SAME indent level as method start)
            if "}" in stripped and current_indent == method_indent:
                # Add placeholder if we haven't added it yet and haven't seen return
                if method_body_lines >= 3 and not seen_return:
                    summary_lines.append(
                        " " * (method_indent + 2) + "// ... implementation details ..."
                    )

                # Add closing brace
                summary_lines.append(line)
                in_method = False
                method_body_lines = 0

                # Add empty line after method for readability
                summary_lines.append("")

            continue

        # Keep closing braces for classes
        if stripped == "}" or stripped == "};":
            summary_lines.append(line)
            continue

        # Keep export statements
        if "module.exports" in stripped or "export " in stripped:
            summary_lines.append(line)
            continue

    # Limit to max_lines
    if len(summary_lines) > max_lines:
        summary_lines = summary_lines[:max_lines]
        summary_lines.append("")
        summary_lines.append("// ... additional methods truncated ...")

    return "\n".join(summary_lines)


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
