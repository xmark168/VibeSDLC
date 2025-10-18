#!/usr/bin/env python3
"""
Simple integration test để kiểm tra codebase analysis integration
"""

import os
import sys

# Test codebase analysis function directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Import directly from the file to avoid dependency issues
exec(open('app/agents/developer/planner/tools/codebase_analyzer.py').read())

def test_integration():
    """Test integration của codebase analysis với prompt template"""
    print("🧪 Testing Codebase Analysis Integration...")
    print("=" * 60)
    
    # Test 1: Codebase Analysis
    codebase_path = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    print(f"📁 Step 1: Analyzing codebase at: {codebase_path}")
    
    try:
        context = analyze_codebase_context(codebase_path)
        print(f"✅ Codebase analysis: {len(context)} chars generated")
        
        # Test 2: Check context content
        print(f"\n📋 Step 2: Validating context content...")
        
        key_elements = [
            ("File structure", "### File Structure:" in context),
            ("Statistics", "### Statistics:" in context),
            ("Python files found", "Python files:" in context),
            ("Classes detected", "Classes:" in context),
            ("Functions detected", "Functions:" in context),
            ("Demo app structure", "app/" in context),
            ("Models found", "user.py" in context),
            ("Services found", "services/" in context),
            ("API endpoints", "endpoints/" in context),
        ]
        
        passed_checks = 0
        for element, check in key_elements:
            status = "✅" if check else "❌"
            print(f"  {status} {element}")
            if check:
                passed_checks += 1
        
        print(f"\n📊 Context validation: {passed_checks}/{len(key_elements)} checks passed")
        
        # Test 3: Prompt template integration
        print(f"\n📝 Step 3: Testing prompt template integration...")
        
        # Read the prompt template
        try:
            with open('app/templates/prompts/developer/planner.py', 'r', encoding='utf-8') as f:
                prompt_content = f.read()
            
            # Check if template has codebase_context placeholder
            has_placeholder = "{codebase_context}" in prompt_content
            print(f"  {'✅' if has_placeholder else '❌'} Prompt template has codebase_context placeholder")
            
            # Test formatting
            if has_placeholder:
                # Extract the CODEBASE_ANALYSIS_PROMPT
                start_marker = 'CODEBASE_ANALYSIS_PROMPT = """'
                end_marker = '"""'
                
                start_idx = prompt_content.find(start_marker)
                if start_idx != -1:
                    start_idx += len(start_marker)
                    end_idx = prompt_content.find(end_marker, start_idx)
                    if end_idx != -1:
                        template = prompt_content[start_idx:end_idx]
                        
                        # Test formatting
                        mock_requirements = '{"task_id": "TEST-001", "description": "Test task"}'
                        try:
                            formatted = template.format(
                                task_requirements=mock_requirements,
                                codebase_context=context
                            )
                            print(f"  ✅ Template formatting successful: {len(formatted)} chars")
                            
                            # Check if context is properly included
                            context_included = "### File Structure:" in formatted
                            print(f"  {'✅' if context_included else '❌'} Codebase context included in formatted prompt")
                            
                        except Exception as e:
                            print(f"  ❌ Template formatting failed: {e}")
                            return False
                    else:
                        print(f"  ❌ Could not find end of CODEBASE_ANALYSIS_PROMPT")
                        return False
                else:
                    print(f"  ❌ Could not find CODEBASE_ANALYSIS_PROMPT in template")
                    return False
            else:
                print(f"  ❌ Template missing codebase_context placeholder")
                return False
                
        except Exception as e:
            print(f"  ❌ Failed to read prompt template: {e}")
            return False
        
        # Test 4: Expected LLM benefits
        print(f"\n🎯 Step 4: Expected benefits for LLM...")
        
        benefits = [
            ("Real file paths", any(path.endswith('.py') for path in context.split())),
            ("Existing classes", "Classes:" in context),
            ("Existing functions", "Functions:" in context),
            ("Project structure", "app/" in context and "tests/" in context),
            ("Configuration files", "pyproject.toml" in context or "Dockerfile" in context),
        ]
        
        for benefit, check in benefits:
            status = "✅" if check else "❌"
            print(f"  {status} LLM will know: {benefit}")
        
        # Final assessment
        total_checks = len(key_elements) + 4 + len(benefits)  # context + template + benefits
        passed_total = passed_checks + (4 if has_placeholder else 0) + sum(1 for _, check in benefits if check)
        
        print(f"\n" + "=" * 60)
        print(f"📊 INTEGRATION TEST RESULTS:")
        print(f"  Total checks: {total_checks}")
        print(f"  Passed: {passed_total}")
        print(f"  Success rate: {passed_total/total_checks*100:.1f}%")
        
        if passed_total >= total_checks * 0.8:  # 80% success rate
            print(f"\n🎉 INTEGRATION TEST PASSED!")
            print(f"✅ Codebase analysis is properly integrated")
            print(f"✅ LLM will receive real codebase context")
            print(f"✅ Recommendations will be based on actual code structure")
            return True
        else:
            print(f"\n⚠️ Integration test needs improvement")
            return False
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_integration()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
