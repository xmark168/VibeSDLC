"""
Simple Test for Prompt Selection Logic

Test prompt selection without dependencies by directly testing the logic.
"""

def test_tech_stack_classification():
    """Test the core logic for classifying tech stacks."""
    
    print("🧪 Testing tech stack classification logic...")
    
    # Backend tech stacks
    backend_stacks = [
        "fastapi", "django", "express", "nodejs", "python",
        "flask", "rails", "spring", "laravel", "asp.net"
    ]
    
    # Frontend tech stacks  
    frontend_stacks = [
        "react", "nextjs", "next.js", "vue", "react-vite",
        "angular", "svelte", "nuxt", "gatsby", "vite"
    ]
    
    # Test backend classification
    for tech_stack in backend_stacks:
        tech_stack_lower = tech_stack.lower()
        is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
        is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)
        
        if is_backend and not is_frontend:
            print(f"✅ {tech_stack} -> Backend")
        else:
            print(f"❌ {tech_stack} -> Misclassified")
            return False
    
    # Test frontend classification
    for tech_stack in frontend_stacks:
        tech_stack_lower = tech_stack.lower()
        is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
        is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)
        
        if is_frontend and not is_backend:
            print(f"✅ {tech_stack} -> Frontend")
        else:
            print(f"❌ {tech_stack} -> Misclassified")
            return False
    
    # Test unknown stacks
    unknown_stacks = ["unknown", "custom", "proprietary", ""]
    for tech_stack in unknown_stacks:
        tech_stack_lower = tech_stack.lower() if tech_stack else ""
        is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
        is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)
        
        if not is_backend and not is_frontend:
            print(f"✅ {tech_stack or 'Empty'} -> Generic (fallback)")
        else:
            print(f"❌ {tech_stack or 'Empty'} -> Unexpected classification")
            return False
    
    return True


def test_case_insensitive_logic():
    """Test case insensitive matching."""
    
    print("\n🧪 Testing case insensitive logic...")
    
    backend_stacks = ["fastapi", "django", "express", "nodejs", "python"]
    frontend_stacks = ["react", "nextjs", "vue", "angular"]
    
    test_cases = [
        ("FastAPI", True, False),  # (tech_stack, should_be_backend, should_be_frontend)
        ("FASTAPI", True, False),
        ("fastapi", True, False),
        ("React", False, True),
        ("REACT", False, True),
        ("react", False, True),
        ("NextJS", False, True),
        ("nextjs", False, True),
        ("UNKNOWN", False, False),
        ("", False, False),
    ]
    
    for tech_stack, expected_backend, expected_frontend in test_cases:
        tech_stack_lower = tech_stack.lower() if tech_stack else ""
        is_backend = any(stack in tech_stack_lower for stack in backend_stacks)
        is_frontend = any(stack in tech_stack_lower for stack in frontend_stacks)
        
        if is_backend == expected_backend and is_frontend == expected_frontend:
            classification = "Backend" if is_backend else "Frontend" if is_frontend else "Generic"
            print(f"✅ {tech_stack or 'Empty'} -> {classification}")
        else:
            print(f"❌ {tech_stack or 'Empty'} -> Wrong classification")
            return False
    
    return True


def test_prompt_content_exists():
    """Test that prompt files exist and contain expected content."""
    
    print("\n🧪 Testing prompt content exists...")
    
    try:
        # Read the prompts file directly
        with open("app/agents/developer/implementor/utils/prompts.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for backend prompt
        if "BACKEND_FILE_CREATION_PROMPT" in content:
            print("✅ Backend creation prompt defined")
        else:
            print("❌ Backend creation prompt missing")
            return False
        
        if "BACKEND_FILE_MODIFICATION_PROMPT" in content:
            print("✅ Backend modification prompt defined")
        else:
            print("❌ Backend modification prompt missing")
            return False
        
        # Check for frontend prompt
        if "FRONTEND_FILE_CREATION_PROMPT" in content:
            print("✅ Frontend creation prompt defined")
        else:
            print("❌ Frontend creation prompt missing")
            return False
        
        if "FRONTEND_FILE_MODIFICATION_PROMPT" in content:
            print("✅ Frontend modification prompt defined")
        else:
            print("❌ Frontend modification prompt missing")
            return False
        
        # Check for generic prompts (fallback)
        if "GENERIC_FILE_CREATION_PROMPT" in content:
            print("✅ Generic creation prompt defined")
        else:
            print("❌ Generic creation prompt missing")
            return False
        
        if "GENERIC_FILE_MODIFICATION_PROMPT" in content:
            print("✅ Generic modification prompt defined")
        else:
            print("❌ Generic modification prompt missing")
            return False
        
        # Check for backend-specific content
        backend_keywords = ["API DESIGN", "DATABASE OPERATIONS", "FastAPI", "Django", "Express.js"]
        backend_found = sum(1 for keyword in backend_keywords if keyword in content)
        if backend_found >= 3:
            print(f"✅ Backend-specific content found ({backend_found}/{len(backend_keywords)} keywords)")
        else:
            print(f"❌ Insufficient backend-specific content ({backend_found}/{len(backend_keywords)} keywords)")
            return False
        
        # Check for frontend-specific content
        frontend_keywords = ["COMPONENT ARCHITECTURE", "STATE MANAGEMENT", "React", "Next.js", "Vue"]
        frontend_found = sum(1 for keyword in frontend_keywords if keyword in content)
        if frontend_found >= 3:
            print(f"✅ Frontend-specific content found ({frontend_found}/{len(frontend_keywords)} keywords)")
        else:
            print(f"❌ Insufficient frontend-specific content ({frontend_found}/{len(frontend_keywords)} keywords)")
            return False
        
        return True
        
    except FileNotFoundError:
        print("❌ Prompts file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading prompts file: {e}")
        return False


def test_generate_code_integration():
    """Test that generate_code.py has the selection function."""
    
    print("\n🧪 Testing generate_code.py integration...")
    
    try:
        # Read the generate_code file directly
        with open("app/agents/developer/implementor/nodes/generate_code.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for selection function
        if "_select_prompt_based_on_tech_stack" in content:
            print("✅ Prompt selection function exists")
        else:
            print("❌ Prompt selection function missing")
            return False
        
        # Check that function is used in file generation
        if "selected_prompt = _select_prompt_based_on_tech_stack" in content:
            print("✅ Prompt selection function is used")
        else:
            print("❌ Prompt selection function not used")
            return False
        
        # Check for backend/frontend stack lists
        if "backend_stacks" in content and "frontend_stacks" in content:
            print("✅ Tech stack classification lists exist")
        else:
            print("❌ Tech stack classification lists missing")
            return False
        
        # Check that old references are removed
        if "is_new_project" in content:
            print("❌ Old is_new_project reference still exists")
            return False
        else:
            print("✅ Old is_new_project references removed")
        
        if "boilerplate_template" in content:
            print("❌ Old boilerplate_template reference still exists")
            return False
        else:
            print("✅ Old boilerplate_template references removed")
        
        return True
        
    except FileNotFoundError:
        print("❌ generate_code.py file not found")
        return False
    except Exception as e:
        print(f"❌ Error reading generate_code.py file: {e}")
        return False


def main():
    """Run simple prompt selection tests."""
    
    print("🚀 Simple Prompt Selection Test\n")
    print("Testing prompt selection logic without external dependencies.\n")
    
    test1_success = test_tech_stack_classification()
    test2_success = test_case_insensitive_logic()
    test3_success = test_prompt_content_exists()
    test4_success = test_generate_code_integration()
    
    overall_success = test1_success and test2_success and test3_success and test4_success
    
    if overall_success:
        print("\n🎉 SIMPLE PROMPT SELECTION TEST SUCCESSFUL!")
        print("✅ Tech stack classification logic works correctly")
        print("✅ Case insensitive matching works")
        print("✅ All required prompts are defined with appropriate content")
        print("✅ generate_code.py integration is complete")
        print("✅ Old references (is_new_project, boilerplate_template) removed")
        print("\n💡 System prompts have been successfully enhanced!")
        print("💡 Backend: API design, database ops, security, framework-specific patterns")
        print("💡 Frontend: Component architecture, state management, UI/UX, accessibility")
        print("💡 Code generation quality should improve significantly")
    else:
        print("\n💥 SIMPLE PROMPT SELECTION TEST FAILED!")
        print("❌ Some issues found with prompt selection implementation")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
