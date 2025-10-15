# app/agents/developer/implementor/tools/generation_tools.py
"""
Code generation and integration strategy tools
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool


@tool
def select_integration_strategy_tool(
    task_description: str,
    codebase_context: str,
    target_files: List[str] = None
) -> str:
    """
    Select the best integration strategy for implementing a task.
    
    This tool analyzes the task requirements and existing codebase to determine
    the most appropriate integration approach.
    
    Args:
        task_description: Description of the task to implement
        codebase_context: Context about the existing codebase
        target_files: List of files that might be affected (optional)
        
    Returns:
        JSON string with recommended integration strategy and reasoning
        
    Example:
        select_integration_strategy_tool(
            "Add user authentication endpoints",
            "FastAPI application with existing user models",
            ["app/models/user.py", "app/api/routes/"]
        )
    """
    try:
        # Analyze task description for keywords
        task_lower = task_description.lower()
        
        # Strategy scoring system
        strategies = {
            "extend_existing": {"score": 0, "reasons": []},
            "create_new": {"score": 0, "reasons": []},
            "refactor": {"score": 0, "reasons": []},
            "fix_issue": {"score": 0, "reasons": []},
            "hybrid": {"score": 0, "reasons": []}
        }
        
        # Analyze task type
        if any(keyword in task_lower for keyword in ["add", "implement", "create", "build"]):
            if any(keyword in task_lower for keyword in ["endpoint", "route", "api", "method", "function"]):
                strategies["extend_existing"]["score"] += 3
                strategies["extend_existing"]["reasons"].append("Adding new endpoints/methods to existing structure")
            elif any(keyword in task_lower for keyword in ["service", "module", "component", "class"]):
                strategies["create_new"]["score"] += 3
                strategies["create_new"]["reasons"].append("Creating new service/module/component")
            else:
                strategies["create_new"]["score"] += 2
                strategies["create_new"]["reasons"].append("General creation task")
        
        if any(keyword in task_lower for keyword in ["fix", "bug", "error", "issue", "problem"]):
            strategies["fix_issue"]["score"] += 4
            strategies["fix_issue"]["reasons"].append("Task involves fixing bugs or issues")
        
        if any(keyword in task_lower for keyword in ["refactor", "improve", "optimize", "restructure", "reorganize"]):
            strategies["refactor"]["score"] += 4
            strategies["refactor"]["reasons"].append("Task involves code improvement or restructuring")
        
        if any(keyword in task_lower for keyword in ["update", "modify", "change", "enhance"]):
            strategies["extend_existing"]["score"] += 2
            strategies["extend_existing"]["reasons"].append("Task involves modifying existing functionality")
        
        # Analyze codebase context
        context_lower = codebase_context.lower()
        
        if "existing" in context_lower and any(keyword in context_lower for keyword in ["models", "routes", "controllers", "services"]):
            strategies["extend_existing"]["score"] += 2
            strategies["extend_existing"]["reasons"].append("Existing structure detected that can be extended")
        
        if any(keyword in context_lower for keyword in ["legacy", "old", "outdated"]):
            strategies["refactor"]["score"] += 2
            strategies["refactor"]["reasons"].append("Legacy code detected that may benefit from refactoring")
        
        if "empty" in context_lower or "new project" in context_lower:
            strategies["create_new"]["score"] += 3
            strategies["create_new"]["reasons"].append("New or empty project - creating new structure")
        
        # Analyze target files
        if target_files:
            existing_files = []
            new_files = []
            
            for file_path in target_files:
                path = Path(file_path)
                if path.exists():
                    existing_files.append(file_path)
                else:
                    new_files.append(file_path)
            
            if existing_files:
                strategies["extend_existing"]["score"] += len(existing_files)
                strategies["extend_existing"]["reasons"].append(f"Found {len(existing_files)} existing files to extend")
            
            if new_files:
                strategies["create_new"]["score"] += len(new_files)
                strategies["create_new"]["reasons"].append(f"Need to create {len(new_files)} new files")
        
        # Determine recommended strategy
        recommended_strategy = max(strategies.items(), key=lambda x: x[1]["score"])
        strategy_name = recommended_strategy[0]
        strategy_info = recommended_strategy[1]
        
        # If scores are tied or very low, default to create_new
        if strategy_info["score"] <= 1:
            strategy_name = "create_new"
            strategy_info = {
                "score": 2,
                "reasons": ["Default strategy for unclear requirements"]
            }
        
        # Check for hybrid approach
        sorted_strategies = sorted(strategies.items(), key=lambda x: x[1]["score"], reverse=True)
        if len(sorted_strategies) >= 2 and sorted_strategies[0][1]["score"] - sorted_strategies[1][1]["score"] <= 1:
            if sorted_strategies[0][1]["score"] >= 3:
                strategy_name = "hybrid"
                strategy_info = {
                    "score": sorted_strategies[0][1]["score"],
                    "reasons": [
                        f"Combination of {sorted_strategies[0][0]} and {sorted_strategies[1][0]}",
                        "Multiple approaches needed for complex task"
                    ],
                    "primary_strategy": sorted_strategies[0][0],
                    "secondary_strategy": sorted_strategies[1][0]
                }
        
        # Generate implementation guidance
        guidance = generate_implementation_guidance(strategy_name, task_description, codebase_context)
        
        result = {
            "recommended_strategy": strategy_name,
            "confidence": min(strategy_info["score"] / 5.0, 1.0),
            "reasoning": strategy_info["reasons"],
            "all_strategies": {k: v["score"] for k, v in strategies.items()},
            "implementation_guidance": guidance,
            "task_analysis": {
                "task_type": analyze_task_type(task_description),
                "complexity": estimate_complexity(task_description),
                "estimated_effort": estimate_effort(task_description, strategy_name)
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error selecting integration strategy: {str(e)}"


def analyze_task_type(task_description: str) -> str:
    """Analyze the type of task based on description"""
    task_lower = task_description.lower()
    
    if any(keyword in task_lower for keyword in ["auth", "login", "register", "jwt", "token"]):
        return "authentication"
    elif any(keyword in task_lower for keyword in ["api", "endpoint", "route", "rest"]):
        return "api_development"
    elif any(keyword in task_lower for keyword in ["database", "model", "schema", "migration"]):
        return "database"
    elif any(keyword in task_lower for keyword in ["ui", "frontend", "component", "page"]):
        return "frontend"
    elif any(keyword in task_lower for keyword in ["test", "testing", "unit test", "integration test"]):
        return "testing"
    elif any(keyword in task_lower for keyword in ["deploy", "deployment", "docker", "ci/cd"]):
        return "deployment"
    elif any(keyword in task_lower for keyword in ["fix", "bug", "error", "issue"]):
        return "bug_fix"
    else:
        return "general_development"


def estimate_complexity(task_description: str) -> str:
    """Estimate task complexity based on description"""
    task_lower = task_description.lower()
    complexity_indicators = {
        "high": ["complex", "advanced", "integration", "multiple", "system", "architecture"],
        "medium": ["implement", "create", "add", "build", "develop"],
        "low": ["simple", "basic", "small", "minor", "quick"]
    }
    
    for level, indicators in complexity_indicators.items():
        if any(indicator in task_lower for indicator in indicators):
            return level
    
    # Default to medium complexity
    return "medium"


def estimate_effort(task_description: str, strategy: str) -> str:
    """Estimate implementation effort"""
    complexity = estimate_complexity(task_description)
    
    effort_matrix = {
        ("low", "extend_existing"): "1-2 hours",
        ("low", "create_new"): "2-4 hours", 
        ("low", "refactor"): "2-3 hours",
        ("low", "fix_issue"): "30min-2 hours",
        ("medium", "extend_existing"): "4-8 hours",
        ("medium", "create_new"): "1-2 days",
        ("medium", "refactor"): "1-2 days",
        ("medium", "fix_issue"): "2-6 hours",
        ("high", "extend_existing"): "1-3 days",
        ("high", "create_new"): "3-5 days",
        ("high", "refactor"): "3-7 days",
        ("high", "fix_issue"): "1-2 days",
    }
    
    return effort_matrix.get((complexity, strategy), "1-2 days")


def generate_implementation_guidance(strategy: str, task_description: str, codebase_context: str) -> Dict[str, Any]:
    """Generate specific implementation guidance based on strategy"""
    
    guidance = {
        "approach": "",
        "steps": [],
        "considerations": [],
        "files_to_modify": [],
        "files_to_create": [],
        "testing_strategy": ""
    }
    
    if strategy == "extend_existing":
        guidance["approach"] = "Extend existing codebase by adding new functionality to current files and structures"
        guidance["steps"] = [
            "Identify existing files and classes to extend",
            "Add new methods, properties, or endpoints",
            "Update existing configurations if needed",
            "Ensure backward compatibility",
            "Add tests for new functionality"
        ]
        guidance["considerations"] = [
            "Maintain existing code style and patterns",
            "Avoid breaking existing functionality",
            "Consider impact on existing tests",
            "Update documentation for new features"
        ]
        guidance["testing_strategy"] = "Add unit tests for new functionality, run existing tests to ensure no regression"
    
    elif strategy == "create_new":
        guidance["approach"] = "Create new files, modules, or components to implement the functionality"
        guidance["steps"] = [
            "Design new module/component structure",
            "Create new files and directories",
            "Implement core functionality",
            "Integrate with existing system",
            "Add comprehensive tests"
        ]
        guidance["considerations"] = [
            "Follow project conventions and patterns",
            "Ensure proper separation of concerns",
            "Consider future extensibility",
            "Document new components thoroughly"
        ]
        guidance["testing_strategy"] = "Create comprehensive test suite for new components, including unit and integration tests"
    
    elif strategy == "refactor":
        guidance["approach"] = "Improve existing code structure while maintaining functionality"
        guidance["steps"] = [
            "Analyze current code structure and identify issues",
            "Plan refactoring approach to minimize risk",
            "Implement changes incrementally",
            "Verify functionality at each step",
            "Update tests and documentation"
        ]
        guidance["considerations"] = [
            "Maintain existing functionality exactly",
            "Refactor in small, testable increments",
            "Have comprehensive test coverage before starting",
            "Consider performance implications"
        ]
        guidance["testing_strategy"] = "Ensure 100% test coverage before refactoring, run tests after each change"
    
    elif strategy == "fix_issue":
        guidance["approach"] = "Identify and fix specific bugs or issues with minimal code changes"
        guidance["steps"] = [
            "Reproduce the issue consistently",
            "Identify root cause through debugging",
            "Implement minimal fix",
            "Verify fix resolves the issue",
            "Add regression tests"
        ]
        guidance["considerations"] = [
            "Make minimal changes to reduce risk",
            "Understand why the issue occurred",
            "Consider edge cases and similar issues",
            "Document the fix for future reference"
        ]
        guidance["testing_strategy"] = "Create specific test cases that reproduce the bug, verify fix with comprehensive testing"
    
    elif strategy == "hybrid":
        guidance["approach"] = "Combine multiple strategies for complex implementation"
        guidance["steps"] = [
            "Break down task into sub-components",
            "Apply appropriate strategy for each component",
            "Implement in logical order",
            "Integrate components carefully",
            "Test entire system thoroughly"
        ]
        guidance["considerations"] = [
            "Coordinate between different approaches",
            "Maintain consistency across components",
            "Plan integration points carefully",
            "Consider overall system architecture"
        ]
        guidance["testing_strategy"] = "Test each component individually, then perform comprehensive integration testing"
    
    return guidance


@tool
def generate_code_tool(
    strategy: str,
    task_description: str,
    codebase_context: str,
    target_files: List[str] = None,
    additional_context: str = ""
) -> str:
    """
    Generate code based on the selected integration strategy.
    
    This tool uses the code_generator subagent to create code that implements
    the specified task using the chosen integration strategy.
    
    Args:
        strategy: Integration strategy to use
        task_description: Description of what to implement
        codebase_context: Context about the existing codebase
        target_files: List of files to create or modify
        additional_context: Any additional context or requirements
        
    Returns:
        JSON string with generated code and implementation details
        
    Example:
        generate_code_tool(
            "extend_existing",
            "Add user authentication endpoints",
            "FastAPI app with existing user models",
            ["app/api/routes/auth.py"]
        )
    """
    try:
        # This tool will delegate to the code_generator subagent
        # For now, we'll return a structured response that indicates
        # the subagent should be called
        
        generation_request = {
            "action": "generate_code",
            "strategy": strategy,
            "task_description": task_description,
            "codebase_context": codebase_context,
            "target_files": target_files or [],
            "additional_context": additional_context,
            "subagent_required": "code_generator",
            "generation_prompt": create_generation_prompt(
                strategy, task_description, codebase_context, target_files, additional_context
            )
        }
        
        return json.dumps(generation_request, indent=2)
        
    except Exception as e:
        return f"Error preparing code generation: {str(e)}"


def create_generation_prompt(
    strategy: str,
    task_description: str,
    codebase_context: str,
    target_files: Optional[List[str]],
    additional_context: str
) -> str:
    """Create a detailed prompt for the code generator subagent"""
    
    prompt = f"""# CODE GENERATION REQUEST

## Task Description
{task_description}

## Integration Strategy
{strategy}

## Codebase Context
{codebase_context}

## Target Files
{', '.join(target_files) if target_files else 'To be determined'}

## Additional Context
{additional_context}

## Generation Requirements

Based on the integration strategy '{strategy}', please generate the appropriate code:

"""

    if strategy == "extend_existing":
        prompt += """
### Extend Existing Strategy
- Add new functionality to existing files
- Maintain existing code patterns and style
- Ensure backward compatibility
- Follow existing naming conventions
- Add proper error handling
"""

    elif strategy == "create_new":
        prompt += """
### Create New Strategy
- Create new files and modules as needed
- Follow project structure conventions
- Implement clean, modular code
- Add proper documentation and comments
- Include error handling and validation
"""

    elif strategy == "refactor":
        prompt += """
### Refactor Strategy
- Improve code structure while maintaining functionality
- Apply best practices and design patterns
- Optimize performance where appropriate
- Maintain existing API contracts
- Ensure all tests still pass
"""

    elif strategy == "fix_issue":
        prompt += """
### Fix Issue Strategy
- Make minimal changes to fix the specific issue
- Identify and address root cause
- Add validation to prevent similar issues
- Include regression tests
- Document the fix
"""

    prompt += """

## Output Format
Please provide:
1. Complete code for each file
2. Explanation of changes made
3. Integration notes
4. Testing recommendations
5. Any configuration changes needed

## Quality Requirements
- Follow language-specific best practices
- Include proper error handling
- Add clear comments and documentation
- Ensure code is testable
- Consider security implications
"""

    return prompt
