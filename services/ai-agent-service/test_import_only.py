"""
Test import của generate_code node.
"""

try:
    print("🧪 Testing imports...")
    
    # Test import state
    print("📦 Importing ImplementorState...")
    from app.agents.developer.implementor.state import FileChange, ImplementorState
    print("✅ ImplementorState imported successfully")
    
    # Test import generate_code
    print("📦 Importing generate_code...")
    from app.agents.developer.implementor.nodes.generate_code import generate_code
    print("✅ generate_code imported successfully")
    
    # Test import prompts
    print("📦 Importing prompts...")
    from app.templates.prompts.developer.implementor import (
        GENERATE_NEW_FILE_PROMPT,
        GENERATE_FILE_MODIFICATION_PROMPT,
        VALIDATE_GENERATED_CODE_PROMPT,
    )
    print("✅ Prompts imported successfully")
    
    print("\n🎉 All imports successful!")
    print("✅ Implementation is ready for testing")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Suggestion: Check dependencies and module paths")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
