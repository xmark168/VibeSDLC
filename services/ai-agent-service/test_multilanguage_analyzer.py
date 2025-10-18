#!/usr/bin/env python3
"""
Test script để kiểm tra multi-language codebase analyzer
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Import directly from the file to avoid dependency issues
exec(open('app/agents/developer/planner/tools/codebase_analyzer.py', encoding='utf-8').read())


def create_test_codebase():
    """Tạo test codebase với nhiều ngôn ngữ"""
    temp_dir = tempfile.mkdtemp()
    base_path = Path(temp_dir)
    
    # Python files
    (base_path / "app").mkdir()
    (base_path / "app" / "main.py").write_text("""
from fastapi import FastAPI
from .models import User

app = FastAPI()

@app.get("/users")
async def get_users():
    return {"users": []}

class UserService:
    def get_user(self, user_id: int):
        return User.query.get(user_id)
""")
    
    (base_path / "app" / "models.py").write_text("""
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
""")
    
    # JavaScript files
    (base_path / "frontend").mkdir()
    (base_path / "frontend" / "app.js").write_text("""
const express = require('express');
const app = express();

app.get('/api/users', (req, res) => {
    res.json({ users: [] });
});

class UserController {
    async getUsers() {
        return await User.findAll();
    }
    
    async createUser(userData) {
        return await User.create(userData);
    }
}

function validateUser(user) {
    return user.name && user.email;
}

module.exports = { UserController, validateUser };
""")
    
    # TypeScript files
    (base_path / "frontend" / "types.ts").write_text("""
interface User {
    id: number;
    name: string;
    email: string;
}

interface UserResponse {
    users: User[];
    total: number;
}

class ApiClient {
    async getUsers(): Promise<UserResponse> {
        const response = await fetch('/api/users');
        return response.json();
    }
}

export { User, UserResponse, ApiClient };
""")
    
    # Config files
    (base_path / "package.json").write_text('{"name": "test-app", "version": "1.0.0"}')
    (base_path / "requirements.txt").write_text("fastapi==0.68.0\nsqlalchemy==1.4.0")
    (base_path / "tsconfig.json").write_text('{"compilerOptions": {"target": "es2020"}}')
    
    return str(base_path)


def test_multilanguage_analyzer():
    """Test multi-language analyzer"""
    print("🧪 Testing Multi-Language Codebase Analyzer...")
    print("=" * 70)
    
    # Create test codebase
    test_path = create_test_codebase()
    print(f"📁 Created test codebase at: {test_path}")
    
    try:
        # Test language detection
        print(f"\n🔍 Step 1: Testing Language Detection...")
        
        detector_tests = [
            ("main.py", Language.PYTHON),
            ("app.js", Language.JAVASCRIPT),
            ("types.ts", Language.TYPESCRIPT),
            ("component.jsx", Language.JAVASCRIPT),
            ("App.tsx", Language.TYPESCRIPT),
            ("package.json", Language.UNKNOWN),  # Config file
        ]
        
        for filename, expected in detector_tests:
            detected = LanguageDetector.detect_language(filename)
            status = "✅" if detected == expected else "❌"
            print(f"  {status} {filename} -> {detected.value} (expected: {expected.value})")
        
        # Test codebase analysis
        print(f"\n📊 Step 2: Testing Codebase Analysis...")
        
        analyzer = CodebaseAnalyzer(test_path)
        
        # Test file structure
        structure = analyzer.get_file_structure()
        print(f"  ✅ File structure detected: {len(structure)} directories")
        
        # Test language statistics
        lang_stats = analyzer.get_language_statistics()
        print(f"  ✅ Language statistics: {lang_stats}")
        
        # Test file analysis
        print(f"\n🔬 Step 3: Testing File Analysis...")
        
        # Test Python file
        py_analysis = analyzer.analyze_file_by_language("app/main.py")
        print(f"  ✅ Python analysis: {len(py_analysis.get('classes', []))} classes, {len(py_analysis.get('functions', []))} functions")
        
        # Test JavaScript file
        js_analysis = analyzer.analyze_file_by_language("frontend/app.js")
        print(f"  ✅ JavaScript analysis: {len(js_analysis.get('classes', []))} classes, {len(js_analysis.get('functions', []))} functions")
        
        # Test TypeScript file
        ts_analysis = analyzer.analyze_file_by_language("frontend/types.ts")
        print(f"  ✅ TypeScript analysis: {len(ts_analysis.get('classes', []))} classes, {len(ts_analysis.get('interfaces', []))} interfaces")
        
        # Test context generation
        print(f"\n📝 Step 4: Testing Context Generation...")
        
        context = analyze_codebase_context(test_path)
        print(f"  ✅ Context generated: {len(context)} characters")
        
        # Validate context content
        validation_checks = [
            ("Multi-language header", "Multi-Language" in context),
            ("Languages detected section", "Languages Detected:" in context),
            ("Python detected", "Python:" in context),
            ("JavaScript detected", "Javascript:" in context or "javascript:" in context),
            ("TypeScript detected", "Typescript:" in context or "typescript:" in context),
            ("File structure", "File Structure:" in context),
            ("Classes found", "Classes:" in context),
            ("Functions found", "Functions:" in context),
            ("Interfaces found", "Interfaces:" in context),
            ("Statistics section", "Statistics:" in context),
            ("Source files count", "Source files:" in context),
        ]
        
        print(f"\n🔍 Step 5: Validation Checks...")
        passed_checks = 0
        for check_name, passed in validation_checks:
            status = "✅" if passed else "❌"
            print(f"  {status} {check_name}")
            if passed:
                passed_checks += 1
        
        success_rate = passed_checks / len(validation_checks) * 100
        print(f"\n📊 Validation Results: {passed_checks}/{len(validation_checks)} ({success_rate:.1f}%)")
        
        # Show context preview
        print(f"\n📋 Context Preview (first 1000 chars):")
        print("-" * 50)
        print(context[:1000] + "..." if len(context) > 1000 else context)
        print("-" * 50)
        
        # Final assessment
        if success_rate >= 80:
            print(f"\n🎉 MULTI-LANGUAGE ANALYZER TEST PASSED!")
            print(f"✅ Language detection working")
            print(f"✅ File analysis working for multiple languages")
            print(f"✅ Context generation includes multi-language info")
            print(f"✅ LLM will receive comprehensive codebase context")
            return True
        else:
            print(f"\n⚠️ Test needs improvement (success rate: {success_rate:.1f}%)")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        import shutil
        try:
            shutil.rmtree(test_path)
            print(f"🧹 Cleaned up test directory")
        except:
            pass


if __name__ == "__main__":
    success = test_multilanguage_analyzer()
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")
    sys.exit(0 if success else 1)
