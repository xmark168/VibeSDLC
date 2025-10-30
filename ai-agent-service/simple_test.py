#!/usr/bin/env python3
"""
Simple test for planner agent without complex imports
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    from agents.developer.planner.agent import PlannerAgent
    print("✅ Successfully imported PlannerAgent")
    
    # Test basic initialization
    planner = PlannerAgent(
        model="gpt-4o",
        session_id="test_session",
        user_id="test_user"
    )
    print("✅ Successfully created PlannerAgent instance")
    
    # Test basic attributes
    print(f"📊 Model: {planner.model_name}")
    print(f"🔗 Session ID: {planner.session_id}")
    print(f"👤 User ID: {planner.user_id}")
    print(f"🤖 Langfuse Handler: {'✅ Configured' if planner.langfuse_handler else '⚠️  Not configured'}")
    print(f"📈 Graph: {'✅ Built' if planner.graph else '❌ Not built'}")
    
    print("\n🎉 Basic planner agent test PASSED!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
