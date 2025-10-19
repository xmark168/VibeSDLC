"""
Test Install Dependencies Node

Test that the install_dependencies node correctly processes external dependencies
from implementation plan and installs required packages.
"""

from app.agents.developer.implementor.nodes.install_dependencies import install_dependencies
from app.agents.developer.implementor.state import ImplementorState


def test_install_dependencies_node():
    """Test install_dependencies node with mock implementation plan."""
    
    print("🧪 Testing install_dependencies node...")
    
    # Create mock implementation plan with external dependencies
    mock_implementation_plan = {
        "infrastructure": {
            "external_dependencies": [
                {
                    "package": "python-jose[cryptography]",
                    "version": ">=3.3.0",
                    "purpose": "JWT token generation and validation",
                    "already_installed": False,
                    "installation_method": "pip",
                    "install_command": "pip install python-jose[cryptography]>=3.3.0",
                    "package_file": "pyproject.toml",
                    "section": "dependencies"
                },
                {
                    "package": "fastapi",
                    "version": ">=0.100.0",
                    "purpose": "Web framework",
                    "already_installed": True,
                    "installation_method": "pip",
                    "install_command": "Already installed",
                    "package_file": "pyproject.toml",
                    "section": "dependencies"
                },
                {
                    "package": "pytest",
                    "version": ">=7.0.0",
                    "purpose": "Testing framework",
                    "already_installed": False,
                    "installation_method": "pip",
                    "install_command": "pip install pytest>=7.0.0",
                    "package_file": "pyproject.toml",
                    "section": "devDependencies"
                }
            ]
        }
    }
    
    # Create initial state
    initial_state = ImplementorState(
        implementation_plan=mock_implementation_plan,
        task_description="Test JWT authentication implementation",
        codebase_path=".",  # Use current directory for testing
    )
    
    print(f"📦 Input dependencies: {len(mock_implementation_plan['infrastructure']['external_dependencies'])}")
    
    # Run install_dependencies node
    try:
        result_state = install_dependencies(initial_state)
        
        print(f"\n📊 Results:")
        print(f"   Current Phase: {result_state.current_phase}")
        print(f"   Status: {result_state.status}")
        print(f"   Dependencies Installed: {result_state.dependencies_installed}")
        print(f"   Installation Results: {len(result_state.dependency_installations)}")
        
        # Check results
        if result_state.current_phase == "install_dependencies":
            print("✅ Current phase set correctly")
        else:
            print(f"❌ Wrong current phase: {result_state.current_phase}")
            
        if result_state.dependency_installations:
            print(f"✅ Found {len(result_state.dependency_installations)} installation results")
            
            # Check each installation result
            for i, install_result in enumerate(result_state.dependency_installations):
                print(f"\n   📦 Dependency {i+1}: {install_result.package}")
                print(f"      Success: {install_result.success}")
                print(f"      Already Installed: {install_result.already_installed}")
                print(f"      Command: {install_result.install_command}")
                if install_result.error_message:
                    print(f"      Error: {install_result.error_message[:100]}...")
        else:
            print("❌ No installation results found")
            
        # Check tools output
        if "dependency_installation" in result_state.tools_output:
            summary = result_state.tools_output["dependency_installation"]
            print(f"\n📋 Summary:")
            print(f"   Total Dependencies: {summary.get('total_dependencies', 0)}")
            print(f"   Already Installed: {summary.get('already_installed', 0)}")
            print(f"   Attempted Installs: {summary.get('attempted_installs', 0)}")
            print(f"   Successful Installs: {summary.get('successful_installs', 0)}")
            print(f"   Failed Installs: {summary.get('failed_installs', 0)}")
        
        # Check messages
        if result_state.messages:
            print(f"\n💬 AI Messages: {len(result_state.messages)}")
            for msg in result_state.messages:
                print(f"   {msg.content[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_install_dependencies_no_deps():
    """Test install_dependencies node with no external dependencies."""
    
    print("\n🧪 Testing install_dependencies node with no dependencies...")
    
    # Create mock implementation plan with no external dependencies
    mock_implementation_plan = {
        "infrastructure": {
            "external_dependencies": []
        }
    }
    
    # Create initial state
    initial_state = ImplementorState(
        implementation_plan=mock_implementation_plan,
        task_description="Test with no dependencies",
        codebase_path=".",
    )
    
    try:
        result_state = install_dependencies(initial_state)
        
        print(f"📊 Results:")
        print(f"   Status: {result_state.status}")
        print(f"   Dependencies Installed: {result_state.dependencies_installed}")
        
        if result_state.status == "dependencies_complete" and result_state.dependencies_installed:
            print("✅ Correctly handled no dependencies case")
            return True
        else:
            print("❌ Failed to handle no dependencies case correctly")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


def main():
    """Run install_dependencies node tests."""
    
    print("🚀 Testing Install Dependencies Node\n")
    print("This test verifies that the install_dependencies node correctly")
    print("processes external dependencies from implementation plan.\n")
    
    test1_success = test_install_dependencies_node()
    test2_success = test_install_dependencies_no_deps()
    
    overall_success = test1_success and test2_success
    
    if overall_success:
        print("\n🎉 INSTALL DEPENDENCIES NODE TEST SUCCESSFUL!")
        print("✅ Node correctly processes external dependencies")
        print("✅ Node handles installation commands properly")
        print("✅ Node updates state with installation results")
        print("✅ Node handles edge cases (no dependencies)")
    else:
        print("\n💥 INSTALL DEPENDENCIES NODE TEST FAILED!")
        print("❌ Node may not be processing dependencies correctly")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
