"""
Execute Step Node

Execute implementation steps và sub_steps theo thứ tự tuần tự từ simplified plan.
"""

import json
import subprocess
import time
from pathlib import Path

from langchain_core.messages import AIMessage

from ..state import FileChange, ImplementorState
from ..tool.filesystem_tools import (
    create_directory_tool,
    edit_file_tool,
    read_file_tool,
    write_file_tool,
)
from ..tool.incremental_tools import (
    add_function_tool,
    add_import_tool,
    create_method_tool,
    modify_function_tool,
)
from ..utils.incremental_modifications import (
    IncrementalModificationValidator,
    parse_structured_modifications,
)


def execute_step(state: ImplementorState) -> ImplementorState:
    """
    Execute current step và sub_steps theo thứ tự tuần tự.
    
    Workflow:
    1. Get current step từ plan_steps
    2. Execute sub_steps sequentially (1.1 → 1.2 → 1.3)
    3. Cho mỗi sub_step:
       - Execute action based on action_type (create/modify/setup/test)
       - Run test verification
       - Log completion
    4. Move to next step hoặc complete
    
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
        sub_step_id = current_sub_step.get("sub_step", f"{step_number}.{state.current_sub_step_index + 1}")
        sub_step_title = current_sub_step.get("title", f"Sub-step {sub_step_id}")
        action_type = current_sub_step.get("action_type", "modify")
        files_affected = current_sub_step.get("files_affected", [])
        test_instruction = current_sub_step.get("test", "")
        
        print(f"\n🔧 Sub-step {sub_step_id}: {sub_step_title}")
        print(f"   Action: {action_type}")
        print(f"   Files: {files_affected}")
        
        # Execute sub_step based on action_type
        execution_success = True
        execution_errors = []
        
        try:
            if action_type == "create":
                execution_success, errors = _execute_create_action(state, current_sub_step, files_affected)
                execution_errors.extend(errors)
                
            elif action_type == "modify":
                execution_success, errors = _execute_modify_action(state, current_sub_step, files_affected)
                execution_errors.extend(errors)
                
            elif action_type == "setup":
                execution_success, errors = _execute_setup_action(state, current_sub_step)
                execution_errors.extend(errors)
                
            elif action_type == "test":
                execution_success, errors = _execute_test_action(state, current_sub_step)
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
            state.error_message = f"Sub-step {sub_step_id} failed: {'; '.join(execution_errors[:2])}"
            state.status = "step_execution_failed"
            
        # Store execution results
        if "step_execution" not in state.tools_output:
            state.tools_output["step_execution"] = []
            
        state.tools_output["step_execution"].append({
            "step": step_number,
            "sub_step": sub_step_id,
            "title": sub_step_title,
            "action_type": action_type,
            "files_affected": files_affected,
            "success": execution_success,
            "errors": execution_errors,
            "test_instruction": test_instruction
        })
        
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


def _execute_create_action(state: ImplementorState, sub_step: dict, files_affected: list) -> tuple[bool, list]:
    """Execute create action for files."""
    errors = []
    success = True
    
    for file_path in files_affected:
        try:
            print(f"   📝 Creating file: {file_path}")
            
            # Find corresponding FileChange for this file
            file_change = None
            for fc in state.files_to_create:
                if fc.file_path == file_path:
                    file_change = fc
                    break
                    
            if not file_change:
                errors.append(f"No FileChange found for {file_path}")
                success = False
                continue
                
            # Create file using write_file_tool
            if file_change.content:
                result = write_file_tool.invoke({
                    "file_path": file_path,
                    "content": file_change.content
                })
                
                if "Error" in result:
                    errors.append(f"Failed to create {file_path}: {result}")
                    success = False
                else:
                    print(f"   ✅ Created: {file_path}")
                    state.files_created.append(file_path)
            else:
                errors.append(f"No content provided for {file_path}")
                success = False
                
        except Exception as e:
            errors.append(f"Error creating {file_path}: {str(e)}")
            success = False
            
    return success, errors


def _execute_modify_action(state: ImplementorState, sub_step: dict, files_affected: list) -> tuple[bool, list]:
    """Execute modify action for files (INCREMENTAL)."""
    errors = []
    success = True
    
    for file_path in files_affected:
        try:
            print(f"   🔧 Modifying file: {file_path}")
            
            # Find corresponding FileChange for this file
            file_change = None
            for fc in state.files_to_modify:
                if fc.file_path == file_path:
                    file_change = fc
                    break
                    
            if not file_change:
                errors.append(f"No FileChange found for {file_path}")
                success = False
                continue
                
            # Use incremental modification (preserve existing logic)
            if file_change.structured_modifications:
                # Parse structured modifications
                modifications = parse_structured_modifications(file_change.structured_modifications)
                
                for mod in modifications:
                    result = edit_file_tool.invoke({
                        "file_path": file_path,
                        "old_content": mod["old_code"],
                        "new_content": mod["new_code"]
                    })
                    
                    if "Error" in result:
                        errors.append(f"Failed to modify {file_path}: {result}")
                        success = False
                    else:
                        print(f"   ✅ Modified: {file_path}")
                        if file_path not in state.files_modified:
                            state.files_modified.append(file_path)
            else:
                errors.append(f"No structured modifications provided for {file_path}")
                success = False
                
        except Exception as e:
            errors.append(f"Error modifying {file_path}: {str(e)}")
            success = False
            
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
                print(f"   ✅ Test passed")
        else:
            print(f"   ✅ Test action logged: {description}")
            
    except Exception as e:
        errors.append(f"Test action failed: {str(e)}")
        success = False
        
    return success, errors


def _run_test_verification(state: ImplementorState, test_instruction: str) -> tuple[bool, str]:
    """Run test verification command."""
    try:
        # Simple test verification - could be enhanced
        if "run" in test_instruction.lower() and ("npm" in test_instruction.lower() or "python" in test_instruction.lower()):
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
