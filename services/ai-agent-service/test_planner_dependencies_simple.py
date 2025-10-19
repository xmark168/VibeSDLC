"""
Simple Test for Planner Agent Dependency Management Enhancement

Test the prompt and structure changes without running the full agent.
"""

import json

def test_prompt_dependencies():
    """Test that the prompt includes dependency management instructions."""
    
    print("🧪 Testing Planner Agent prompt dependency instructions...")
    
    try:
        # Import the prompt templates
        from app.templates.prompts.developer.planner import (
            INITIALIZE_PROMPT,
            CODEBASE_ANALYSIS_PROMPT,
            GENERATE_PLAN_PROMPT
        )
        
        print("✅ Successfully imported prompt templates")
        
        # Check INITIALIZE_PROMPT for dependency mentions
        dependency_keywords = [
            "dependencies", "packages", "install", "external_dependencies",
            "installation_method", "install_command", "package_file"
        ]
        
        found_in_init = []
        for keyword in dependency_keywords:
            if keyword.lower() in INITIALIZE_PROMPT.lower():
                found_in_init.append(keyword)
        
        print(f"📝 INITIALIZE_PROMPT dependency keywords found: {len(found_in_init)}")
        print(f"   Keywords: {found_in_init}")
        
        # Check CODEBASE_ANALYSIS_PROMPT
        found_in_analysis = []
        for keyword in dependency_keywords:
            if keyword.lower() in CODEBASE_ANALYSIS_PROMPT.lower():
                found_in_analysis.append(keyword)
        
        print(f"📝 CODEBASE_ANALYSIS_PROMPT dependency keywords found: {len(found_in_analysis)}")
        print(f"   Keywords: {found_in_analysis}")
        
        # Check GENERATE_PLAN_PROMPT
        found_in_plan = []
        for keyword in dependency_keywords:
            if keyword.lower() in GENERATE_PLAN_PROMPT.lower():
                found_in_plan.append(keyword)
        
        print(f"📝 GENERATE_PLAN_PROMPT dependency keywords found: {len(found_in_plan)}")
        print(f"   Keywords: {found_in_plan}")
        
        # Check for specific enhanced fields
        enhanced_fields = [
            "installation_method", "install_command", "package_file", "section"
        ]
        
        enhanced_found = []
        for field in enhanced_fields:
            if field in GENERATE_PLAN_PROMPT:
                enhanced_found.append(field)
        
        print(f"🔧 Enhanced dependency fields found: {len(enhanced_found)}")
        print(f"   Fields: {enhanced_found}")
        
        # Check for example dependency structure
        if "python-jose[cryptography]" in GENERATE_PLAN_PROMPT:
            print("✅ Found JWT dependency example in prompt")
        else:
            print("⚠️ JWT dependency example not found")
        
        if "pip install" in GENERATE_PLAN_PROMPT:
            print("✅ Found pip install command example in prompt")
        else:
            print("⚠️ pip install command example not found")
        
        # Summary
        total_keywords = len(set(found_in_init + found_in_analysis + found_in_plan))
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Total unique dependency keywords: {total_keywords}")
        print(f"   ✅ Enhanced fields present: {len(enhanced_found)}/4")
        print(f"   ✅ Prompts updated: {sum([len(found_in_init) > 0, len(found_in_analysis) > 0, len(found_in_plan) > 0])}/3")
        
        if total_keywords >= 5 and len(enhanced_found) >= 3:
            print("✅ Prompt enhancement appears successful!")
            return True
        else:
            print("⚠️ Prompt enhancement may be incomplete")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_state_structure():
    """Test that the state structure supports dependencies."""
    
    print("\n🧪 Testing Planner Agent state structure...")
    
    try:
        # Import state classes
        from app.agents.developer.planner.state import CodebaseAnalysis
        
        print("✅ Successfully imported state classes")
        
        # Check if CodebaseAnalysis has external_dependencies field
        analysis = CodebaseAnalysis()
        
        if hasattr(analysis, 'external_dependencies'):
            print("✅ CodebaseAnalysis has external_dependencies field")
            print(f"   Default value: {analysis.external_dependencies}")
        else:
            print("❌ CodebaseAnalysis missing external_dependencies field")
            return False
        
        if hasattr(analysis, 'internal_dependencies'):
            print("✅ CodebaseAnalysis has internal_dependencies field")
        else:
            print("❌ CodebaseAnalysis missing internal_dependencies field")
            return False
        
        # Test creating a dependency structure
        test_dependency = {
            "package": "python-jose[cryptography]",
            "version": ">=3.3.0",
            "purpose": "JWT token generation and validation",
            "already_installed": False,
            "installation_method": "pip",
            "install_command": "pip install python-jose[cryptography]>=3.3.0",
            "package_file": "pyproject.toml",
            "section": "dependencies"
        }
        
        analysis.external_dependencies = [test_dependency]
        print("✅ Successfully created test dependency structure")
        print(f"   Test dependency: {test_dependency['package']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_generate_plan_logic():
    """Test that generate_plan.py has dependency enhancement logic."""
    
    print("\n🧪 Testing generate_plan.py dependency logic...")
    
    try:
        # Import the generate_plan module
        import app.agents.developer.planner.nodes.generate_plan as generate_plan_module
        
        print("✅ Successfully imported generate_plan module")
        
        # Check if the module has dependency-related functions
        module_content = str(generate_plan_module.__dict__)
        
        dependency_keywords = [
            "external_dependencies", "installation_method", "install_command",
            "package_file", "section"
        ]
        
        found_keywords = []
        for keyword in dependency_keywords:
            if keyword in module_content:
                found_keywords.append(keyword)
        
        print(f"🔧 Dependency keywords found in module: {len(found_keywords)}")
        print(f"   Keywords: {found_keywords}")
        
        # Read the source file to check for enhancement logic
        import inspect
        source_file = inspect.getfile(generate_plan_module)
        
        with open(source_file, 'r', encoding='utf-8') as f:
            source_content = f.read()
        
        # Check for specific enhancement logic
        enhancement_patterns = [
            "installation_method",
            "install_command", 
            "package_file",
            "Already installed",
            "pip install"
        ]
        
        found_patterns = []
        for pattern in enhancement_patterns:
            if pattern in source_content:
                found_patterns.append(pattern)
        
        print(f"🔧 Enhancement patterns found: {len(found_patterns)}")
        print(f"   Patterns: {found_patterns}")
        
        if len(found_patterns) >= 4:
            print("✅ Dependency enhancement logic appears to be implemented")
            return True
        else:
            print("⚠️ Dependency enhancement logic may be incomplete")
            return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run simple dependency management tests."""
    
    print("🚀 Testing Planner Agent Dependency Management Enhancement (Simple)\n")
    print("This test verifies the prompt and code changes without running the full agent.\n")
    
    test1 = test_prompt_dependencies()
    test2 = test_state_structure()
    test3 = test_generate_plan_logic()
    
    success = test1 and test2 and test3
    
    if success:
        print("\n🎉 PLANNER DEPENDENCY MANAGEMENT ENHANCEMENT SUCCESSFUL!")
        print("✅ Prompts updated with dependency instructions")
        print("✅ State structure supports dependency fields")
        print("✅ Generate plan logic includes dependency enhancement")
        print("✅ Ready for testing with real tasks")
    else:
        print("\n💥 PLANNER DEPENDENCY MANAGEMENT ENHANCEMENT INCOMPLETE!")
        print("❌ Some components may need additional updates")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
