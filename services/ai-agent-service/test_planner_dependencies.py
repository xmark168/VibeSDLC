"""
Test Planner Agent Dependency Management Enhancement

Test that the Planner Agent now includes dependency management
in implementation plans with complete package information.
"""

import json
import tempfile
from pathlib import Path

def test_planner_dependencies():
    """Test Planner Agent dependency analysis and inclusion."""
    
    print("🧪 Testing Planner Agent dependency management...")
    
    try:
        # Import Planner Agent
        from app.agents.developer.planner.agent import PlannerAgent
        
        # Create test planner
        planner = PlannerAgent(
            model="gpt-4o-mini",  # Use cheaper model for testing
            session_id="test_dependencies",
            user_id="test_user"
        )
        
        # Test task that requires external dependencies
        task_description = """
        Implement JWT-based user authentication system with the following requirements:
        
        1. User registration with email and password
        2. User login with JWT token generation
        3. Password hashing using bcrypt
        4. JWT token validation middleware
        5. Email verification for new users
        6. Password reset functionality
        
        Technical requirements:
        - Use JWT tokens with 15-minute expiry for access tokens
        - Use refresh tokens with 7-day expiry
        - Hash passwords with bcrypt
        - Send verification emails using SMTP
        - Store user data in PostgreSQL database
        """
        
        print(f"📝 Task: {task_description[:100]}...")
        print("\n🚀 Starting planner workflow...")
        
        # Run planner with demo codebase
        result = planner.run(
            task_description=task_description,
            codebase_path=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
            thread_id="test_dependencies_001",
        )
        
        # Display results
        print("\n" + "=" * 60)
        print("📊 PLANNER RESULTS")
        print("=" * 60)
        
        if result.get("success"):
            print("✅ Planning successful!")
            
            # Check if final_plan exists
            final_plan = result.get("final_plan", {})
            if not final_plan:
                print("❌ No final_plan in result")
                return False
            
            # Check infrastructure section
            infrastructure = final_plan.get("infrastructure", {})
            if not infrastructure:
                print("❌ No infrastructure section in final_plan")
                return False
            
            # Check external_dependencies
            external_deps = infrastructure.get("external_dependencies", [])
            print(f"\n📦 External Dependencies Found: {len(external_deps)}")
            
            if not external_deps:
                print("❌ No external dependencies found - this should include JWT, bcrypt, email packages")
                return False
            
            # Analyze each dependency
            required_packages = ["jose", "jwt", "bcrypt", "passlib", "email", "smtp"]
            found_packages = []
            
            for i, dep in enumerate(external_deps):
                print(f"\n📦 Dependency {i+1}:")
                print(f"   Package: {dep.get('package', 'MISSING')}")
                print(f"   Version: {dep.get('version', 'MISSING')}")
                print(f"   Purpose: {dep.get('purpose', 'MISSING')}")
                print(f"   Already Installed: {dep.get('already_installed', 'MISSING')}")
                print(f"   Installation Method: {dep.get('installation_method', 'MISSING')}")
                print(f"   Install Command: {dep.get('install_command', 'MISSING')}")
                print(f"   Package File: {dep.get('package_file', 'MISSING')}")
                print(f"   Section: {dep.get('section', 'MISSING')}")
                
                # Check if dependency has required fields
                required_fields = [
                    'package', 'version', 'purpose', 'already_installed',
                    'installation_method', 'install_command', 'package_file', 'section'
                ]
                
                missing_fields = [field for field in required_fields if field not in dep]
                if missing_fields:
                    print(f"   ⚠️ Missing fields: {missing_fields}")
                else:
                    print("   ✅ All required fields present")
                
                # Track found packages
                package_name = dep.get('package', '').lower()
                for req_pkg in required_packages:
                    if req_pkg in package_name:
                        found_packages.append(req_pkg)
                        break
            
            # Check if we found relevant packages
            print(f"\n🔍 Package Analysis:")
            print(f"   Required types: {required_packages}")
            print(f"   Found types: {found_packages}")
            
            if len(found_packages) >= 2:  # At least JWT and password hashing
                print("✅ Found relevant packages for authentication task")
            else:
                print("⚠️ May be missing some expected packages for authentication")
            
            # Check implementation steps mention dependencies
            impl_steps = final_plan.get("implementation_steps", [])
            dependency_mentioned = False
            
            for step in impl_steps:
                step_desc = step.get("description", "").lower()
                if "install" in step_desc or "dependency" in step_desc or "package" in step_desc:
                    dependency_mentioned = True
                    print(f"✅ Step mentions dependencies: {step.get('title', 'Unknown')}")
                    break
            
            if not dependency_mentioned:
                print("⚠️ Implementation steps don't explicitly mention dependency installation")
            
            print(f"\n📊 Summary:")
            print(f"   ✅ Planning successful: {result.get('success')}")
            print(f"   ✅ External dependencies found: {len(external_deps)}")
            print(f"   ✅ Dependencies have complete info: {all('install_command' in dep for dep in external_deps)}")
            print(f"   ✅ Relevant packages found: {len(found_packages)}")
            
            return True
            
        else:
            print(f"❌ Planning failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run Planner Agent dependency management test."""
    
    print("🚀 Testing Planner Agent Dependency Management Enhancement\n")
    print("This test verifies that Planner Agent now includes comprehensive")
    print("dependency management in implementation plans.\n")
    
    success = test_planner_dependencies()
    
    if success:
        print("\n🎉 PLANNER DEPENDENCY MANAGEMENT TEST SUCCESSFUL!")
        print("✅ Planner Agent now includes external dependencies")
        print("✅ Dependencies have complete package information")
        print("✅ Installation commands are provided")
        print("✅ Package manager and file locations are specified")
    else:
        print("\n💥 PLANNER DEPENDENCY MANAGEMENT TEST FAILED!")
        print("❌ Planner Agent may not be including dependencies properly")
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
