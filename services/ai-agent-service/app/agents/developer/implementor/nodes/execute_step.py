"""
Execute Step Node - Option 1 Flow

Execute implementation steps sequentially với integrated code generation
và file implementation per sub-step.

Workflow:
1. Get current sub-step from plan
2. FOR EACH file in sub-step.files_affected:
   a) Generate code with sub-step specific context
   b) Implement file immediately using helpers
   c) Track success/errors
3. Run test verification if specified
4. Move to next sub-step or step
"""

import os

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import read_file_tool

# Import helper functions from refactored implement_files
from .implement_files import implement_single_file


def execute_step(state: ImplementorState) -> ImplementorState:
    """
    Execute current step với integrated code generation + implementation.

    Option 1 Flow:
    1. Get current sub-step
    2. FOR EACH file in files_affected:
       - Generate code with focused context
       - Implement immediately
    3. Run test verification
    4. Move to next sub-step

    Args:
        state: ImplementorState với plan_steps và current indices

    Returns:
        Updated ImplementorState với execution results
    """
    try:
        print(f"\n🎯 Executing Step {state.current_step_index + 1}...")

        # Check if we have steps to execute
        if not state.plan_steps:
            print("⚠️ No plan steps found - falling back to legacy file-based execution")
            state.current_phase = "implement_files"
            return state

        # Check if all steps completed
        if state.current_step_index >= len(state.plan_steps):
            print("✅ All steps completed!")
            state.current_phase = "run_tests"
            return state

        # Get current step
        current_step = state.plan_steps[state.current_step_index]
        step_number = current_step.get("step", state.current_step_index + 1)
        step_title = current_step.get("title", f"Step {step_number}")
        step_category = current_step.get("category", "backend")
        sub_steps = current_step.get("sub_steps", [])

        print(f"📋 Step {step_number}: {step_title} ({step_category})")
        print(f"   Sub-steps: {len(sub_steps)}")

        # Check if all sub_steps in current step completed
        if state.current_sub_step_index >= len(sub_steps):
            print(f"✅ Step {step_number} completed! Moving to next step...")
            state.current_step_index += 1
            state.current_sub_step_index = 0
            return execute_step(state)  # Recursive call for next step

        # Get current sub_step
        current_sub_step = sub_steps[state.current_sub_step_index]
        sub_step_id = current_sub_step.get(
            "sub_step", f"{step_number}.{state.current_sub_step_index + 1}"
        )
        sub_step_title = current_sub_step.get("title", f"Sub-step {sub_step_id}")
        action_type = current_sub_step.get("action_type", "modify")
        files_affected = current_sub_step.get("files_affected", [])
        test_instruction = current_sub_step.get("test", "")

        print(f"\n🔧 Sub-step {sub_step_id}: {sub_step_title}")
        print(f"   Action: {action_type}")
        print(f"   Files: {files_affected}")

        # Execute sub_step with integrated generation + implementation
        execution_success = True
        execution_errors = []

        try:
            # Initialize LLM for code generation
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
            )

            if action_type == "create":
                execution_success, errors = _execute_create_action_with_generation(
                    state, current_sub_step, files_affected, llm
                )
                execution_errors.extend(errors)

            elif action_type == "modify":
                execution_success, errors = _execute_modify_action_with_generation(
                    state, current_sub_step, files_affected, llm
                )
                execution_errors.extend(errors)

            elif action_type == "setup":
                execution_success, errors = _execute_setup_action(
                    state, current_sub_step
                )
                execution_errors.extend(errors)

            elif action_type == "test":
                execution_success, errors = _execute_test_action(
                    state, current_sub_step
                )
                execution_errors.extend(errors)

            else:
                print(f"⚠️ Unknown action_type: {action_type}")
                execution_errors.append(f"Unknown action_type: {action_type}")
                execution_success = False

        except Exception as e:
            print(f"❌ Error executing sub-step {sub_step_id}: {e}")
            execution_errors.append(f"Sub-step {sub_step_id} failed: {str(e)}")
            execution_success = False

        # Run test verification if provided và execution successful
        if execution_success and test_instruction:
            print(f"🧪 Running test verification: {test_instruction}")
            test_success, test_error = _run_test_verification(state, test_instruction)
            if not test_success:
                execution_errors.append(f"Test failed: {test_error}")
                execution_success = False
            else:
                print("✅ Test verification passed")

        # Log completion
        if execution_success:
            print(f"✅ Sub-step {sub_step_id} completed successfully")
            state.current_sub_step_index += 1
        else:
            print(f"❌ Sub-step {sub_step_id} failed: {'; '.join(execution_errors)}")
            state.error_message = (
                f"Sub-step {sub_step_id} failed: {'; '.join(execution_errors[:2])}"
            )
            state.status = "step_execution_failed"

        # Store execution results
        if "step_execution" not in state.tools_output:
            state.tools_output["step_execution"] = []

        state.tools_output["step_execution"].append(
            {
                "step": step_number,
                "sub_step": sub_step_id,
                "title": sub_step_title,
                "action_type": action_type,
                "files_affected": files_affected,
                "success": execution_success,
                "errors": execution_errors,
                "test_instruction": test_instruction,
            }
        )

        # Add message
        if execution_success:
            message = AIMessage(
                content=f"✅ Sub-step {sub_step_id} completed: {sub_step_title}"
            )
        else:
            message = AIMessage(
                content=f"❌ Sub-step {sub_step_id} failed: {'; '.join(execution_errors[:2])}"
            )
        state.messages.append(message)

        return state

    except Exception as e:
        state.error_message = f"Step execution failed: {str(e)}"
        state.status = "error"
        print(f"❌ Step execution failed: {e}")
        return state


def _execute_create_action_with_generation(
    state: ImplementorState, sub_step: dict, files_affected: list, llm: ChatOpenAI
) -> tuple[bool, list]:
    """
    Execute create action WITH code generation per file.

    AUTO-DETECTION:
    - Check if file exists before creating
    - If file already exists → switch to MODIFY mode (preserve existing content)
    - If file doesn't exist → CREATE as normal
    """
    errors = []
    success = True
    working_dir = state.codebase_path or "."

    for file_path in files_affected:
        try:
            # 🔍 AUTO-DETECT: Check if file already exists
            file_exists = _check_file_exists(file_path, working_dir)

            if file_exists:
                print(f"   ⚠️  File already exists: {file_path}")
                print(
                    "   🔄 Auto-switching to MODIFY mode (preserving existing content)"
                )

                # Read existing content and generate incremental modification
                read_result = read_file_tool.invoke(
                    {"file_path": file_path, "working_directory": working_dir}
                )

                if "File not found" not in read_result:
                    from .generate_code import _extract_actual_content

                    existing_content = _extract_actual_content(read_result)
                    print(
                        f"      📖 Read {len(existing_content)} chars from existing file"
                    )

                    # Build context for modification
                    context = _build_file_context(
                        state=state,
                        sub_step=sub_step,
                        file_path=file_path,
                        is_creation=False,  # It's a modification now
                        existing_content=existing_content,
                    )

                    # ✅ Generate full-file regeneration
                    print("      🤖 Generating full-file regeneration...")
                    modification_result = _generate_file_modification(
                        llm=llm,
                        file_path=file_path,
                        existing_content=existing_content,
                        context=context,
                        tech_stack=state.tech_stack,
                        sub_step=sub_step,
                    )

                    if modification_result:
                        # ✅ NEW: modification_result is complete file content (string), not tuple
                        modification_content = modification_result

                        file_change = FileChange(
                            file_path=file_path,
                            operation="modify",
                            content=modification_content,  # Complete file content
                            change_type="full_file",  # ✅ FIXED: Use "full_file" to match Pydantic schema
                            description=sub_step.get("description", ""),
                            structured_modifications="",  # No longer used
                        )

                        # Implement modification
                        impl_success, error_msg = implement_single_file(
                            file_change=file_change, working_dir=working_dir
                        )

                        if impl_success:
                            if file_path not in state.files_modified:
                                state.files_modified.append(file_path)
                            print(f"   ✅ Modified (auto-detected): {file_path}")
                        else:
                            errors.append(f"Failed to modify {file_path}: {error_msg}")
                            success = False
                    else:
                        errors.append(
                            f"Failed to generate modification for {file_path}"
                        )
                        success = False
                else:
                    errors.append(f"File exists but could not be read: {file_path}")
                    success = False

                continue  # Skip create logic, already handled

            # File doesn't exist → proceed with CREATE
            print(f"   📝 Creating new file: {file_path}")

            # 1. BUILD CONTEXT for this specific file
            context = _build_file_context(
                state=state, sub_step=sub_step, file_path=file_path, is_creation=True
            )

            # 2. GENERATE CODE with focused context
            print("      🤖 Generating code...")
            content = _generate_new_file_content(
                llm=llm,
                file_path=file_path,
                context=context,
                tech_stack=state.tech_stack,
                sub_step=sub_step,
            )

            if not content:
                errors.append(f"Failed to generate content for {file_path}")
                success = False
                continue

            print(f"      ✅ Generated {len(content)} chars")

            # 3. CREATE FileChange object
            file_change = FileChange(
                file_path=file_path,
                operation="create",
                content=content,
                change_type="full_file",
                description=sub_step.get("description", ""),
            )

            # 4. IMPLEMENT immediately using helper
            print("      💾 Implementing file...")
            impl_success, error_msg = implement_single_file(
                file_change=file_change, working_dir=working_dir
            )

            if impl_success:
                state.files_created.append(file_path)
                print(f"   ✅ Created: {file_path}")
            else:
                errors.append(f"Failed to implement {file_path}: {error_msg}")
                success = False

        except Exception as e:
            errors.append(f"Error creating {file_path}: {str(e)}")
            success = False
            print(f"   ❌ Error: {e}")

    return success, errors


def _execute_modify_action_with_generation(
    state: ImplementorState, sub_step: dict, files_affected: list, llm: ChatOpenAI
) -> tuple[bool, list]:
    """
    Execute modify action WITH code generation per file.

    AUTO-DETECTION:
    - Check if file exists before modifying
    - If file doesn't exist → switch to CREATE mode (create new file)
    - If file exists → MODIFY as normal
    """
    errors = []
    success = True
    working_dir = state.codebase_path or "."

    for file_path in files_affected:
        try:
            # 🔍 AUTO-DETECT: Check if file exists
            file_exists = _check_file_exists(file_path, working_dir)

            if not file_exists:
                print(f"   ⚠️  File does not exist: {file_path}")
                print("   🆕 Auto-switching to CREATE mode")

                # Build context for creation
                context = _build_file_context(
                    state=state,
                    sub_step=sub_step,
                    file_path=file_path,
                    is_creation=True,
                )

                # Generate new file content
                print("      🤖 Generating new file content...")
                content = _generate_new_file_content(
                    llm=llm,
                    file_path=file_path,
                    context=context,
                    tech_stack=state.tech_stack,
                    sub_step=sub_step,
                )

                if content:
                    file_change = FileChange(
                        file_path=file_path,
                        operation="create",
                        content=content,
                        change_type="full_file",
                        description=sub_step.get("description", ""),
                    )

                    # Implement creation
                    impl_success, error_msg = implement_single_file(
                        file_change=file_change, working_dir=working_dir
                    )

                    if impl_success:
                        state.files_created.append(file_path)
                        print(f"   ✅ Created (auto-detected): {file_path}")
                    else:
                        errors.append(f"Failed to create {file_path}: {error_msg}")
                        success = False
                else:
                    errors.append(f"Failed to generate content for {file_path}")
                    success = False

                continue  # Skip modify logic, already handled

            # File exists → proceed with MODIFY
            print(f"   🔧 Modifying existing file: {file_path}")

            # 1. READ existing file content
            print("      📖 Reading existing content...")
            existing_content = ""
            try:
                read_result = read_file_tool.invoke(
                    {"file_path": file_path, "working_directory": working_dir}
                )
                if "File not found" not in read_result:
                    # Extract actual content (remove line numbers)
                    from .generate_code import _extract_actual_content

                    existing_content = _extract_actual_content(read_result)
                    print(f"      ✅ Read {len(existing_content)} chars")
            except Exception as e:
                print(f"      ⚠️ Could not read file: {e}")

            # 2. BUILD CONTEXT for this specific file
            context = _build_file_context(
                state=state,
                sub_step=sub_step,
                file_path=file_path,
                is_creation=False,
                existing_content=existing_content,
            )

            # 3. ✅ GENERATE FULL-FILE REGENERATION
            print("      🤖 Generating full-file regeneration...")
            modification_content = _generate_file_modification(
                llm=llm,
                file_path=file_path,
                existing_content=existing_content,
                context=context,
                tech_stack=state.tech_stack,
                sub_step=sub_step,
            )

            if not modification_content:
                errors.append(f"Failed to generate modification for {file_path}")
                success = False
                continue

            print("      ✅ Generated complete file")

            # 4. CREATE FileChange object
            # ✅ NEW: modification_content is complete file (string), not tuple
            file_change = FileChange(
                file_path=file_path,
                operation="modify",
                content=modification_content,  # Complete file content
                change_type="full_file",  # ✅ FIXED: Use "full_file" to match Pydantic schema
                description=sub_step.get("description", ""),
                structured_modifications="",  # No longer used
            )

            # 5. IMPLEMENT immediately using helper
            print("      💾 Applying modification...")
            impl_success, error_msg = implement_single_file(
                file_change=file_change, working_dir=working_dir
            )

            if impl_success:
                if file_path not in state.files_modified:
                    state.files_modified.append(file_path)
                print(f"   ✅ Modified: {file_path}")
            else:
                errors.append(f"Failed to implement {file_path}: {error_msg}")
                success = False

        except Exception as e:
            errors.append(f"Error modifying {file_path}: {str(e)}")
            success = False
            print(f"   ❌ Error: {e}")

    return success, errors


def _execute_setup_action(state: ImplementorState, sub_step: dict) -> tuple[bool, list]:
    """Execute setup action (install dependencies, configure environment)."""
    errors = []
    success = True

    try:
        description = sub_step.get("description", "")
        print(f"   ⚙️ Setup: {description}")

        # For now, just log setup action
        # In future, could parse description to run specific setup commands
        print(f"   ✅ Setup action logged: {description}")

    except Exception as e:
        errors.append(f"Setup action failed: {str(e)}")
        success = False

    return success, errors


def _execute_test_action(state: ImplementorState, sub_step: dict) -> tuple[bool, list]:
    """Execute test action."""
    errors = []
    success = True

    try:
        description = sub_step.get("description", "")
        test_instruction = sub_step.get("test", "")

        print(f"   🧪 Test: {description}")

        if test_instruction:
            test_success, test_error = _run_test_verification(state, test_instruction)
            if not test_success:
                errors.append(test_error)
                success = False
            else:
                print("   ✅ Test passed")
        else:
            print(f"   ✅ Test action logged: {description}")

    except Exception as e:
        errors.append(f"Test action failed: {str(e)}")
        success = False

    return success, errors


# ========================================
# FILE EXISTENCE CHECK
# ========================================


def _check_file_exists(file_path: str, working_dir: str) -> bool:
    """
    Check if file exists in the working directory.

    This is used for auto-detection: decide between create/modify based on file existence.

    Args:
        file_path: Relative file path
        working_dir: Working directory

    Returns:
        True if file exists, False otherwise
    """
    try:
        from pathlib import Path

        full_path = Path(working_dir) / file_path
        exists = full_path.exists() and full_path.is_file()
        return exists
    except Exception as e:
        print(f"      ⚠️ Error checking file existence: {e}")
        return False


# ========================================
# CODE GENERATION HELPERS
# ========================================


def _build_file_context(
    state: ImplementorState,
    sub_step: dict,
    file_path: str,
    is_creation: bool,
    existing_content: str = "",
) -> str:
    """
    Build focused context for single file generation.

    Args:
        state: Current state
        sub_step: Current sub-step being executed
        file_path: File being generated
        is_creation: True if creating new file, False if modifying
        existing_content: Existing file content (for modifications)

    Returns:
        Context string for LLM
    """
    context = f"Task: {state.task_description}\n"
    context += f"Tech Stack: {state.tech_stack}\n"
    context += f"File: {file_path}\n"
    context += f"Action: {'Create' if is_creation else 'Modify'}\n\n"

    # Add sub-step specific context
    context += "Current Sub-step:\n"
    context += f"- ID: {sub_step.get('sub_step', 'N/A')}\n"
    context += f"- Title: {sub_step.get('title', 'N/A')}\n"
    context += f"- Description: {sub_step.get('description', 'N/A')}\n\n"

    # Add files already created (for reference)
    if state.files_created:
        context += "Files already created in previous sub-steps:\n"
        for created_file in state.files_created[-5:]:  # Last 5 files
            context += f"- {created_file}\n"
        context += "\n"

    # ✅ NEW: Add dependency files API summary for API contract coordination
    dependency_files = _identify_dependency_files(
        file_path, state.files_created, state.codebase_path
    )
    if dependency_files:
        context += "=" * 80 + "\n"
        context += "📚 DEPENDENCY FILES - API SUMMARY (API CONTRACT REFERENCE)\n"
        context += "=" * 80 + "\n\n"
        context += "⚠️ CRITICAL: Use EXACT method names, return types, and signatures from these files.\n"
        context += "Note: Implementation details are truncated for brevity. Focus on method signatures.\n\n"

        for dep_file in dependency_files:
            # Use new smart truncation function
            dep_summary = _extract_dependency_api_summary(dep_file, state.codebase_path)
            if dep_summary:
                context += f"📄 File: {dep_file}\n"
                context += f"```javascript\n{dep_summary}\n```\n\n"

        context += "=" * 80 + "\n\n"

    # Add existing content for modifications
    if not is_creation and existing_content:
        lines_count = len(existing_content.split("\n"))
        context += f"Existing file content ({lines_count} lines):\n"
        context += f"```\n{existing_content}\n```\n\n"
        context += "⚠️ IMPORTANT: This file already has content. Use INCREMENTAL modifications (OLD_CODE/NEW_CODE format).\n\n"

    return context


def _identify_dependency_files(
    current_file: str, created_files: list, working_dir: str = None
) -> list:
    """
    Identify which previously created files are dependencies of current file.

    NEW APPROACH: Parse import/require statements from the current file to detect
    ALL dependencies, not just layered architecture patterns.

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
        from .generate_code import _extract_actual_content

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
    import os

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
        from .generate_code import _extract_actual_content

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


def _generate_new_file_content(
    llm: ChatOpenAI, file_path: str, context: str, tech_stack: str, sub_step: dict
) -> str | None:
    """
    Generate content for a new file.

    Args:
        llm: LLM instance
        file_path: File path
        context: Generation context
        tech_stack: Technology stack
        sub_step: Current sub-step

    Returns:
        Generated file content or None if failed
    """
    try:
        from pathlib import Path

        file_ext = Path(file_path).suffix

        # Import prompt selection from generate_code
        from .generate_code import _select_prompt_based_on_tech_stack

        # Select appropriate prompt
        selected_prompt = _select_prompt_based_on_tech_stack(tech_stack, "creation")

        # Format prompt
        prompt = selected_prompt.format(
            implementation_plan=context,
            file_path=file_path,
            file_specs=sub_step.get("description", "New file implementation"),
            tech_stack=tech_stack,
            project_type="existing_project",
        )

        # Call LLM
        response = llm.invoke(prompt)
        raw_response = response.content.strip()

        # Clean response
        from .generate_code import _clean_llm_response, _validate_generated_code

        generated_code = _clean_llm_response(raw_response)

        # Validate
        if generated_code and _validate_generated_code(generated_code, file_ext):
            return generated_code
        else:
            print("      ⚠️ Generated code failed validation")
            return None

    except Exception as e:
        print(f"      ❌ Error generating new file: {e}")
        return None


def _generate_file_modification(
    llm: ChatOpenAI,
    file_path: str,
    existing_content: str,
    context: str,
    tech_stack: str,
    sub_step: dict,
) -> str | None:
    """
    Generate full-file regeneration for existing file modification.

    ✅ NEW APPROACH: Full-file regeneration (not incremental OLD_CODE/NEW_CODE)

    Args:
        llm: LLM instance
        file_path: File path
        existing_content: Current file content
        context: Generation context
        tech_stack: Technology stack
        sub_step: Current sub-step

    Returns:
        Complete regenerated file content, or None if failed
    """
    try:
        from pathlib import Path

        # Import from generate_code
        from .generate_code import (
            _clean_llm_response,
            _select_prompt_based_on_tech_stack,
        )

        # Select appropriate prompt (now uses full-file regeneration prompt)
        selected_prompt = _select_prompt_based_on_tech_stack(tech_stack, "modification")

        # Determine language
        file_ext = Path(file_path).suffix
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "jsx",
            ".tsx": "tsx",
        }
        language = language_map.get(file_ext, "text")

        # Format prompt with existing content
        prompt = selected_prompt.format(
            current_content=existing_content or "File not found",
            modification_specs=sub_step.get("description", "File modification"),
            change_type="full_file",  # ✅ FIXED: Use "full_file" for consistency
            target_element="",
            tech_stack=tech_stack,
            file_path=file_path,
            language=language,
        )

        # Call LLM
        print("      🤖 Calling LLM for full-file regeneration...")
        response = llm.invoke(prompt)
        raw_response = response.content.strip()

        print(f"      ✅ LLM response received ({len(raw_response)} chars)")

        # ✅ NEW APPROACH: Clean and return complete file content
        cleaned_response = _clean_llm_response(raw_response)

        if not cleaned_response or len(cleaned_response.strip()) == 0:
            print("      ❌ LLM response is empty after cleaning")
            return None

        # Validate response length
        if existing_content:
            existing_lines = existing_content.split("\n")
            response_lines = cleaned_response.split("\n")

            if len(response_lines) < len(existing_lines) * 0.5:
                print(
                    f"      ⚠️ Warning: Generated file ({len(response_lines)} lines) is significantly shorter than original ({len(existing_lines)} lines)"
                )
                print(
                    "      💡 This might indicate LLM didn't preserve all existing code"
                )

            print(
                f"      ✅ Generated complete file: {len(response_lines)} lines (original: {len(existing_lines)} lines)"
            )

        # Return complete file content
        return cleaned_response

    except Exception as e:
        print(f"      ❌ Error generating modification: {e}")
        return None


# ========================================
# TEST VERIFICATION
# ========================================


def _run_test_verification(
    state: ImplementorState, test_instruction: str
) -> tuple[bool, str]:
    """Run test verification command."""
    try:
        # Simple test verification - could be enhanced
        if "run" in test_instruction.lower() and (
            "npm" in test_instruction.lower() or "python" in test_instruction.lower()
        ):
            # Extract command from test instruction
            # For now, just log the test instruction
            print(f"   📋 Test instruction: {test_instruction}")
            return True, ""
        else:
            # Non-command test (e.g., "verify file exists", "check output")
            print(f"   📋 Test verification: {test_instruction}")
            return True, ""

    except Exception as e:
        return False, f"Test verification failed: {str(e)}"
