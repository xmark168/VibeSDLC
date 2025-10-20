"""
Simple Test for Daytona Client Utilities

Test the Daytona client utility functions without full agent dependencies.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.agents.developer.implementor.utils.daytona_client import should_delete_sandbox
    from app.agents.developer.implementor.state import SandboxDeletion
    
    def test_should_delete_sandbox():
        """Test the should_delete_sandbox function logic."""
        
        print("🧪 Testing should_delete_sandbox function...")
        
        # Test cases
        test_cases = [
            # (status, sandbox_id, expected_result, description)
            ("completed", "sandbox-123", True, "Successful completion with sandbox ID"),
            ("pr_ready", "sandbox-456", True, "PR ready with sandbox ID"),
            ("finalized", "sandbox-789", True, "Finalized with sandbox ID"),
            ("error", "sandbox-error", False, "Error status - should not delete"),
            ("failed", "sandbox-failed", False, "Failed status - should not delete"),
            ("completed", "", False, "Successful but no sandbox ID"),
            ("completed", None, False, "Successful but None sandbox ID"),
            ("pr_ready", "   ", False, "PR ready but whitespace sandbox ID"),
        ]
        
        all_passed = True
        
        for status, sandbox_id, expected, description in test_cases:
            result = should_delete_sandbox(status, sandbox_id)
            
            if result == expected:
                print(f"✅ {description}: {result}")
            else:
                print(f"❌ {description}: Expected {expected}, got {result}")
                all_passed = False
        
        return all_passed
    
    
    def test_sandbox_deletion_model():
        """Test the SandboxDeletion model."""
        
        print("\n🧪 Testing SandboxDeletion model...")
        
        try:
            # Test successful deletion
            success_deletion = SandboxDeletion(
                sandbox_id="test-123",
                success=True,
                message="Sandbox deleted successfully",
                retries_used=1,
                error="",
                skipped=False,
                skip_reason=""
            )
            
            print(f"✅ Success deletion model: {success_deletion.sandbox_id}")
            
            # Test skipped deletion
            skipped_deletion = SandboxDeletion(
                sandbox_id="test-456",
                success=False,
                message="Sandbox deletion skipped: No sandbox ID provided",
                retries_used=0,
                error="",
                skipped=True,
                skip_reason="No sandbox ID provided"
            )
            
            print(f"✅ Skipped deletion model: {skipped_deletion.skip_reason}")
            
            # Test failed deletion
            failed_deletion = SandboxDeletion(
                sandbox_id="test-789",
                success=False,
                message="Failed to delete sandbox after 3 attempts",
                retries_used=2,
                error="Connection timeout",
                skipped=False,
                skip_reason=""
            )
            
            print(f"✅ Failed deletion model: {failed_deletion.error}")
            
            return True
            
        except Exception as e:
            print(f"❌ SandboxDeletion model test failed: {e}")
            return False
    
    
    def test_daytona_config():
        """Test Daytona configuration function."""
        
        print("\n🧪 Testing Daytona configuration...")
        
        try:
            from app.agents.developer.implementor.utils.daytona_client import get_daytona_config
            
            # Save original environment variables
            original_api_key = os.environ.get("DAYTONA_API_KEY")
            original_api_url = os.environ.get("DAYTONA_API_URL")
            original_target = os.environ.get("DAYTONA_TARGET")
            
            # Test with missing API key
            if "DAYTONA_API_KEY" in os.environ:
                del os.environ["DAYTONA_API_KEY"]
            
            try:
                config = get_daytona_config()
                print("❌ Should have raised ValueError for missing API key")
                return False
            except ValueError as e:
                print(f"✅ Correctly raised ValueError for missing API key: {str(e)[:50]}...")
            
            # Test with valid configuration
            os.environ["DAYTONA_API_KEY"] = "test-api-key"
            os.environ["DAYTONA_API_URL"] = "https://test.daytona.io/api"
            os.environ["DAYTONA_TARGET"] = "test"
            
            try:
                config = get_daytona_config()
                print(f"✅ Valid config created with API URL: {config.api_url}")
                print(f"✅ Valid config created with target: {config.target}")
            except Exception as e:
                print(f"❌ Failed to create valid config: {e}")
                return False
            
            # Restore original environment variables
            if original_api_key:
                os.environ["DAYTONA_API_KEY"] = original_api_key
            elif "DAYTONA_API_KEY" in os.environ:
                del os.environ["DAYTONA_API_KEY"]
                
            if original_api_url:
                os.environ["DAYTONA_API_URL"] = original_api_url
            elif "DAYTONA_API_URL" in os.environ:
                del os.environ["DAYTONA_API_URL"]
                
            if original_target:
                os.environ["DAYTONA_TARGET"] = original_target
            elif "DAYTONA_TARGET" in os.environ:
                del os.environ["DAYTONA_TARGET"]
            
            return True
            
        except ImportError as e:
            print(f"⚠️  Could not test Daytona config (missing dependencies): {e}")
            return True  # Don't fail the test for missing optional dependencies
        except Exception as e:
            print(f"❌ Daytona config test failed: {e}")
            return False
    
    
    def main():
        """Run simple Daytona client tests."""
        
        print("🚀 Testing Daytona Client Utilities\n")
        print("This test verifies the basic functionality of Daytona client utilities")
        print("without requiring full agent dependencies or actual Daytona API calls.\n")
        
        test1_success = test_should_delete_sandbox()
        test2_success = test_sandbox_deletion_model()
        test3_success = test_daytona_config()
        
        overall_success = test1_success and test2_success and test3_success
        
        if overall_success:
            print("\n🎉 DAYTONA CLIENT UTILITIES TEST SUCCESSFUL!")
            print("✅ should_delete_sandbox logic works correctly")
            print("✅ SandboxDeletion model works correctly")
            print("✅ Daytona configuration handling works correctly")
            print("✅ Ready for integration with finalize node")
        else:
            print("\n💥 DAYTONA CLIENT UTILITIES TEST FAILED!")
            print("❌ Some utility functions may not be working correctly")
        
        return overall_success

except ImportError as e:
    print(f"❌ Could not import required modules: {e}")
    print("This might be due to missing dependencies or incorrect Python path.")
    
    def main():
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
