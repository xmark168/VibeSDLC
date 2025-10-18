#!/usr/bin/env python3
"""
Test script để kiểm tra codebase analyzer
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.agents.developer.planner.tools.codebase_analyzer import analyze_codebase_context


def test_codebase_analyzer():
    """Test codebase analyzer với demo codebase"""
    print("🧪 Testing Codebase Analyzer...")
    print("=" * 60)
    
    # Test với demo codebase
    codebase_path = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    print(f"📁 Analyzing codebase at: {codebase_path}")
    
    try:
        context = analyze_codebase_context(codebase_path)
        
        print(f"✅ Analysis completed successfully!")
        print(f"📊 Context length: {len(context)} characters")
        print("\n" + "=" * 60)
        print("📋 CODEBASE CONTEXT PREVIEW:")
        print("=" * 60)
        print(context[:1000] + "..." if len(context) > 1000 else context)
        print("=" * 60)
        
        # Check for key information
        checks = [
            ("File Structure", "### File Structure:" in context),
            ("Statistics", "### Statistics:" in context),
            ("API Patterns", "### Existing API Patterns:" in context),
            ("Models", "### Existing Models:" in context),
            ("Dependencies", "### Dependencies:" in context),
        ]
        
        print("\n🔍 Content Validation:")
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}: {'Found' if passed else 'Missing'}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All validation checks passed!")
            print("✅ Codebase analyzer is working correctly")
            return True
        else:
            print("\n⚠️ Some validation checks failed")
            return False
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_codebase_analyzer()
    sys.exit(0 if success else 1)
