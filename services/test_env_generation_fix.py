#!/usr/bin/env python3
"""
Test script để verify .env file generation fix
"""

import sys
import os

def test_nodejs_env_example_exists():
    """Test Node.js template có .env.example file"""
    
    print("🧪 Testing Node.js .env.example template")
    print("=" * 60)
    
    env_example_path = "ai-agent-service/app/templates/boilerplate/be/nodejs/express-basic/.env.example"
    
    if os.path.exists(env_example_path):
        print("✅ .env.example file exists")
        
        with open(env_example_path, 'r') as f:
            content = f.read()
        
        print(f"   File size: {len(content)} characters")
        print(f"   Lines: {len(content.splitlines())} lines")
        
        # Check for key environment variables
        required_vars = [
            "NODE_ENV", "PORT", "JWT_SECRET", "MONGODB_URI", 
            "REDIS_URL", "CORS_ORIGINS", "SMTP_HOST"
        ]
        
        found_vars = []
        missing_vars = []
        
        for var in required_vars:
            if var in content:
                found_vars.append(var)
            else:
                missing_vars.append(var)
        
        print(f"\n📋 Environment Variables Check:")
        print(f"   ✅ Found: {len(found_vars)}/{len(required_vars)}")
        for var in found_vars:
            print(f"      ✅ {var}")
        
        if missing_vars:
            print(f"   ❌ Missing: {len(missing_vars)}")
            for var in missing_vars:
                print(f"      ❌ {var}")
        
        return len(missing_vars) == 0
    else:
        print("❌ .env.example file not found")
        return False

def test_prompts_env_requirements():
    """Test Implementor prompts có .env requirements"""
    
    print("\n🧪 Testing Implementor prompts .env requirements")
    print("=" * 60)
    
    try:
        # Read prompts file
        prompts_file = "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
        
        if os.path.exists(prompts_file):
            with open(prompts_file, 'r') as f:
                content = f.read()
            
            print("✅ Successfully read prompts.py")
            
            # Check for .env requirements
            env_checks = [
                ("ENV file requirements section", "CRITICAL .ENV FILE REQUIREMENTS" in content),
                ("Complete env files instruction", "Generate COMPLETE environment variable files" in content),
                ("Node.js env variables", "For Node.js/Express: Include PORT, JWT_SECRET" in content),
                ("Python env variables", "For Python/FastAPI: Include DATABASE_URL, SECRET_KEY" in content),
                ("No empty env warning", "NEVER generate empty .env files" in content),
                ("Format instruction", "VARIABLE_NAME=default_value_or_placeholder" in content)
            ]
            
            passed = 0
            for check_name, check_result in env_checks:
                status = "✅" if check_result else "❌"
                print(f"   {status} {check_name}")
                if check_result:
                    passed += 1
            
            print(f"\n📊 Overall: {passed}/{len(env_checks)} checks passed")
            return passed == len(env_checks)
        else:
            print(f"❌ File not found: {prompts_file}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_config_env_mapping():
    """Test config/index.js và .env.example mapping"""
    
    print("\n🧪 Testing config/index.js và .env.example mapping")
    print("=" * 60)
    
    try:
        # Read config file
        config_file = "ai-agent-service/app/templates/boilerplate/be/nodejs/express-basic/src/config/index.js"
        env_file = "ai-agent-service/app/templates/boilerplate/be/nodejs/express-basic/.env.example"
        
        if os.path.exists(config_file) and os.path.exists(env_file):
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            with open(env_file, 'r') as f:
                env_content = f.read()
            
            print("✅ Successfully read both files")
            
            # Extract process.env variables from config
            import re
            env_vars_in_config = re.findall(r'process\.env\.(\w+)', config_content)
            env_vars_in_config = list(set(env_vars_in_config))  # Remove duplicates
            
            print(f"\n📋 Environment variables in config: {len(env_vars_in_config)}")
            
            # Check mapping
            mapped = 0
            unmapped = []
            
            for var in env_vars_in_config:
                if var in env_content:
                    mapped += 1
                    print(f"   ✅ {var}")
                else:
                    unmapped.append(var)
                    print(f"   ❌ {var} (missing in .env.example)")
            
            print(f"\n📊 Mapping: {mapped}/{len(env_vars_in_config)} variables mapped")
            
            if unmapped:
                print(f"⚠️ Unmapped variables: {unmapped}")
            
            return len(unmapped) == 0
        else:
            print("❌ Required files not found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_comparison_with_fastapi():
    """Test comparison với FastAPI .env.example"""
    
    print("\n🧪 Testing comparison với FastAPI .env.example")
    print("=" * 60)
    
    try:
        nodejs_env = "ai-agent-service/app/templates/boilerplate/be/nodejs/express-basic/.env.example"
        fastapi_env = "ai-agent-service/app/templates/boilerplate/be/python/fastapi-basic/.env.example"
        
        if os.path.exists(nodejs_env) and os.path.exists(fastapi_env):
            with open(nodejs_env, 'r') as f:
                nodejs_content = f.read()
            
            with open(fastapi_env, 'r') as f:
                fastapi_content = f.read()
            
            nodejs_lines = len(nodejs_content.splitlines())
            fastapi_lines = len(fastapi_content.splitlines())
            
            print(f"📊 File comparison:")
            print(f"   Node.js .env.example: {nodejs_lines} lines")
            print(f"   FastAPI .env.example: {fastapi_lines} lines")
            
            # Check completeness
            if nodejs_lines >= 30:  # Reasonable threshold
                print("✅ Node.js .env.example has comprehensive content")
                return True
            else:
                print("❌ Node.js .env.example seems incomplete")
                return False
        else:
            print("❌ Required files not found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    
    print("🚀 .ENV Generation Fix Verification")
    print("=" * 80)
    
    tests = [
        ("Node.js .env.example exists", test_nodejs_env_example_exists),
        ("Prompts .env requirements", test_prompts_env_requirements),
        ("Config/env mapping", test_config_env_mapping),
        ("Comparison with FastAPI", test_comparison_with_fastapi)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 .ENV GENERATION FIX SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 .ENV Generation Fix Successfully Applied!")
        print("\n✅ Key Improvements:")
        print("   - Added .env.example template for Node.js Express")
        print("   - Enhanced Implementor prompts with .env requirements")
        print("   - Ensured comprehensive environment variable coverage")
        print("   - Added specific instructions for different tech stacks")
        
        print("\n🚀 LLM should now generate complete .env files!")
        print("\n📋 Expected .env content for Node.js:")
        print("   - PORT, NODE_ENV, JWT_SECRET")
        print("   - MONGODB_URI, REDIS_URL")
        print("   - CORS_ORIGINS, SMTP configuration")
        print("   - External API keys, logging, monitoring")
        
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
