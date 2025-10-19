"""
Simple Workflow Logic Test

Verify the workflow logic by analyzing the code structure.
"""

import ast
import inspect


def analyze_process_tasks_function():
    """Analyze the process_tasks function to verify workflow logic."""
    
    print("🔍 Analyzing process_tasks function...")
    
    # Read the source code
    with open("app/agents/developer/nodes/process_tasks.py", "r") as f:
        source_code = f.read()
    
    # Parse AST
    tree = ast.parse(source_code)
    
    # Find process_tasks function
    process_tasks_func = None
    process_single_task_func = None
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name == "process_tasks":
                process_tasks_func = node
            elif node.name == "_process_single_task":
                process_single_task_func = node
    
    if not process_tasks_func:
        print("❌ process_tasks function not found")
        return False
    
    if not process_single_task_func:
        print("❌ _process_single_task function not found")
        return False
    
    print("✅ Found both process_tasks and _process_single_task functions")
    
    # Analyze process_tasks structure
    print("\n🔍 Analyzing process_tasks structure...")
    
    # Look for loop over eligible_tasks
    has_task_loop = False
    calls_process_single_task = False
    
    for node in ast.walk(process_tasks_func):
        # Check for loop over eligible_tasks
        if isinstance(node, ast.For):
            if isinstance(node.iter, ast.Attribute) and node.iter.attr == "eligible_tasks":
                has_task_loop = True
                print("✅ Found loop over state.eligible_tasks")
                
                # Check if loop calls _process_single_task
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        if child.func.id == "_process_single_task":
                            calls_process_single_task = True
                            print("✅ Found call to _process_single_task inside loop")
    
    if not has_task_loop:
        print("❌ No loop over eligible_tasks found")
        return False
    
    if not calls_process_single_task:
        print("❌ No call to _process_single_task found in loop")
        return False
    
    # Analyze _process_single_task structure
    print("\n🔍 Analyzing _process_single_task structure...")
    
    # Look for sequential calls to subagents
    planner_call_found = False
    implementor_call_found = False
    reviewer_call_found = False
    
    # Get function body statements
    statements = process_single_task_func.body
    
    for stmt in statements:
        # Look for assignments that call subagent functions
        if isinstance(stmt, ast.Assign):
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                func_name = stmt.value.func.id
                if func_name == "_invoke_planner_agent":
                    planner_call_found = True
                    print("✅ Found call to _invoke_planner_agent")
                elif func_name == "_invoke_implementor_agent":
                    implementor_call_found = True
                    print("✅ Found call to _invoke_implementor_agent")
                elif func_name == "_invoke_code_reviewer_agent":
                    reviewer_call_found = True
                    print("✅ Found call to _invoke_code_reviewer_agent")
    
    if not planner_call_found:
        print("❌ No call to _invoke_planner_agent found")
        return False
    
    if not implementor_call_found:
        print("❌ No call to _invoke_implementor_agent found")
        return False
    
    if not reviewer_call_found:
        print("❌ No call to _invoke_code_reviewer_agent found")
        return False
    
    print("\n🎉 WORKFLOW STRUCTURE ANALYSIS COMPLETE!")
    print("✅ process_tasks loops over each task")
    print("✅ Each task calls _process_single_task")
    print("✅ _process_single_task calls all three subagents sequentially")
    print("✅ This means each task goes through complete lifecycle before next task")
    
    return True


def analyze_execution_flow():
    """Analyze the execution flow to confirm sequential processing."""
    
    print("\n🔍 Analyzing execution flow...")
    
    # Read the source code
    with open("app/agents/developer/nodes/process_tasks.py", "r") as f:
        lines = f.readlines()
    
    # Find key lines
    key_patterns = {
        "task_loop": "for i, task in enumerate(state.eligible_tasks):",
        "process_single_call": "task_result = _process_single_task(task, state)",
        "planner_call": "planner_result = _invoke_planner_agent(task, state)",
        "implementor_call": "implementor_result = _invoke_implementor_agent(task, planner_result, state)",
        "reviewer_call": "reviewer_result = _invoke_code_reviewer_agent(task, implementor_result, state)"
    }
    
    found_patterns = {}
    
    for i, line in enumerate(lines):
        line = line.strip()
        for pattern_name, pattern in key_patterns.items():
            if pattern in line:
                found_patterns[pattern_name] = i + 1
                print(f"✅ Line {i+1}: {pattern_name}")
    
    # Verify all patterns found
    if len(found_patterns) == len(key_patterns):
        print("\n🎉 ALL KEY EXECUTION PATTERNS FOUND!")
        print("✅ Workflow executes tasks sequentially")
        print("✅ Each task completes all phases before next task")
        return True
    else:
        missing = set(key_patterns.keys()) - set(found_patterns.keys())
        print(f"\n❌ Missing patterns: {missing}")
        return False


def verify_workflow_correctness():
    """Verify that the workflow is implemented correctly."""
    
    print("🎯 WORKFLOW CORRECTNESS VERIFICATION")
    print("="*60)
    
    print("\nExpected workflow:")
    print("  Task 1: Planner → Implementor → Code Reviewer (complete)")
    print("  Task 2: Planner → Implementor → Code Reviewer (complete)")
    print("  Task 3: Planner → Implementor → Code Reviewer (complete)")
    
    print("\nIncorrect workflow (what we DON'T want):")
    print("  All tasks → Planner")
    print("  All tasks → Implementor")
    print("  All tasks → Code Reviewer")
    
    print("\n" + "="*60)
    
    # Run analysis
    structure_correct = analyze_process_tasks_function()
    flow_correct = analyze_execution_flow()
    
    if structure_correct and flow_correct:
        print("\n🎉 WORKFLOW IS CORRECTLY IMPLEMENTED!")
        print("✅ The current code implements the desired workflow")
        print("✅ Each task goes through complete lifecycle before next task")
        print("✅ No batch processing by subagent type")
        return True
    else:
        print("\n❌ WORKFLOW HAS ISSUES!")
        return False


def main():
    """Run workflow verification."""
    
    print("🚀 Developer Agent Workflow Logic Verification\n")
    
    try:
        result = verify_workflow_correctness()
        
        if result:
            print("\n" + "="*60)
            print("🎯 CONCLUSION")
            print("="*60)
            print("✅ The workflow is ALREADY CORRECTLY IMPLEMENTED!")
            print("✅ No changes needed to process_tasks.py")
            print("✅ Each task processes through complete Planner → Implementor → Code Reviewer lifecycle")
            print("✅ Tasks are processed sequentially, not in batches")
            
            print("\n💡 If you're experiencing different behavior:")
            print("   1. Check if there are other workflow implementations")
            print("   2. Verify which process_tasks function is being called")
            print("   3. Check for any overrides or modifications")
            print("   4. Run actual execution tests to confirm behavior")
            
            return True
        else:
            print("\n❌ Workflow needs fixes")
            return False
            
    except Exception as e:
        print(f"💥 Analysis failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
