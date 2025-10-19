"""
Test cho generate_code node để verify implementation.
"""

import os
import tempfile
from pathlib import Path

from app.agents.developer.implementor.nodes.generate_code import generate_code
from app.agents.developer.implementor.state import FileChange, ImplementorState


def test_generate_code_basic():
    """Test basic code generation functionality."""
    print("🧪 Testing generate_code node...")
    
    # Setup test environment
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test state
        state = ImplementorState(
            task_description="Create a simple user service",
            tech_stack="Python FastAPI",
            codebase_path=temp_dir,
            base_branch="main",
            feature_branch="feature/user-service",
            files_to_create=[
                FileChange(
                    file_path="app/services/user_service.py",
                    operation="create",
                    description="User service for managing user operations",
                    content="",  # Should be empty initially
                )
            ],
            files_to_modify=[],
            status="ready_for_code_generation",
            current_phase="generate_code",
            messages=[],
            tools_output={},
        )
        
        print(f"📁 Test directory: {temp_dir}")
        print(f"📝 Files to create: {len(state.files_to_create)}")
        print(f"✏️  Files to modify: {len(state.files_to_modify)}")
        
        # Test generate_code function
        try:
            result_state = generate_code(state)
            
            # Verify results
            print(f"✅ Status: {result_state.status}")
            print(f"📊 Phase: {result_state.current_phase}")
            
            # Check if content was generated
            for file_change in result_state.files_to_create:
                print(f"📄 File: {file_change.file_path}")
                print(f"   Content length: {len(file_change.content)} chars")
                print(f"   Has content: {'✅' if file_change.content else '❌'}")
                
                if file_change.content:
                    # Show first few lines
                    lines = file_change.content.split('\n')[:5]
                    print(f"   Preview:")
                    for i, line in enumerate(lines, 1):
                        print(f"     {i}: {line}")
                    if len(file_change.content.split('\n')) > 5:
                        print(f"     ... ({len(file_change.content.split('\n'))} total lines)")
            
            # Check tools output
            if "code_generation" in result_state.tools_output:
                gen_info = result_state.tools_output["code_generation"]
                print(f"📈 Generation stats:")
                print(f"   Files generated: {gen_info.get('files_generated', 0)}")
                print(f"   Files failed: {gen_info.get('files_failed', 0)}")
                print(f"   Total files: {gen_info.get('total_files', 0)}")
            
            # Check messages
            if result_state.messages:
                last_message = result_state.messages[-1]
                print(f"💬 Last message: {last_message.content[:100]}...")
            
            return result_state.status in ["code_generated", "code_partially_generated"]
            
        except Exception as e:
            print(f"❌ Error during code generation: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_generate_code_with_modification():
    """Test code generation with file modification."""
    print("\n🧪 Testing generate_code with file modification...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create an existing file to modify
        existing_file = Path(temp_dir) / "app" / "models" / "user.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("""
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
""")
        
        # Create test state with modification
        state = ImplementorState(
            task_description="Add email field to User model",
            tech_stack="Python SQLAlchemy",
            codebase_path=temp_dir,
            base_branch="main", 
            feature_branch="feature/add-email",
            files_to_create=[],
            files_to_modify=[
                FileChange(
                    file_path="app/models/user.py",
                    operation="modify",
                    description="Add email field to User model",
                    content="",  # Should be empty initially
                    change_type="incremental",
                    target_class="User",
                )
            ],
            status="ready_for_code_generation",
            current_phase="generate_code",
            messages=[],
            tools_output={},
        )
        
        print(f"📁 Test directory: {temp_dir}")
        print(f"📝 Files to create: {len(state.files_to_create)}")
        print(f"✏️  Files to modify: {len(state.files_to_modify)}")
        
        try:
            result_state = generate_code(state)
            
            print(f"✅ Status: {result_state.status}")
            
            # Check modification results
            for file_change in result_state.files_to_modify:
                print(f"📄 File: {file_change.file_path}")
                print(f"   Content length: {len(file_change.content)} chars")
                print(f"   Has content: {'✅' if file_change.content else '❌'}")
                
                if file_change.content:
                    print(f"   Modified content preview:")
                    lines = file_change.content.split('\n')[:10]
                    for i, line in enumerate(lines, 1):
                        print(f"     {i}: {line}")
            
            return result_state.status in ["code_generated", "code_partially_generated"]
            
        except Exception as e:
            print(f"❌ Error during modification: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print("🚀 Starting generate_code node tests...")
    
    # Set environment variables if needed
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not set - tests may fail")
    
    # Run tests
    test1_passed = test_generate_code_basic()
    test2_passed = test_generate_code_with_modification()
    
    print(f"\n📊 Test Results:")
    print(f"   Basic generation: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   File modification: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
