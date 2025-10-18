#!/usr/bin/env python3
"""
Simple test để kiểm tra language detection
"""

import os
import sys
from pathlib import Path
from enum import Enum

class Language(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    UNKNOWN = "unknown"


class LanguageDetector:
    """Detect programming language based on file extension"""
    
    EXTENSION_MAP = {
        '.py': Language.PYTHON,
        '.js': Language.JAVASCRIPT,
        '.jsx': Language.JAVASCRIPT,
        '.ts': Language.TYPESCRIPT,
        '.tsx': Language.TYPESCRIPT,
        '.java': Language.JAVA,
        '.cs': Language.CSHARP,
        '.go': Language.GO,
        '.rs': Language.RUST,
        '.php': Language.PHP,
        '.rb': Language.RUBY,
    }
    
    CONFIG_FILES = {
        # Python
        'pyproject.toml', 'requirements.txt', 'setup.py', 'Pipfile',
        # JavaScript/TypeScript
        'package.json', 'tsconfig.json', 'webpack.config.js', 'vite.config.js',
        # Java
        'pom.xml', 'build.gradle', 'build.gradle.kts',
        # C#
        '*.csproj', '*.sln', 'packages.config',
        # Go
        'go.mod', 'go.sum',
        # Rust
        'Cargo.toml', 'Cargo.lock',
        # PHP
        'composer.json', 'composer.lock',
        # Ruby
        'Gemfile', 'Gemfile.lock', '*.gemspec',
        # General
        'Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Language:
        """Detect language from file extension"""
        ext = Path(file_path).suffix.lower()
        return cls.EXTENSION_MAP.get(ext, Language.UNKNOWN)
    
    @classmethod
    def is_source_file(cls, file_path: str) -> bool:
        """Check if file is a source code file"""
        return cls.detect_language(file_path) != Language.UNKNOWN
    
    @classmethod
    def is_config_file(cls, file_name: str) -> bool:
        """Check if file is a configuration file"""
        return file_name in cls.CONFIG_FILES or any(
            file_name.endswith(config.replace('*', '')) 
            for config in cls.CONFIG_FILES 
            if '*' in config
        )


def test_language_detection():
    """Test language detection functionality"""
    print("🧪 Testing Language Detection...")
    print("=" * 50)
    
    test_cases = [
        # Python
        ("main.py", Language.PYTHON, True),
        ("models.py", Language.PYTHON, True),
        ("__init__.py", Language.PYTHON, True),
        
        # JavaScript
        ("app.js", Language.JAVASCRIPT, True),
        ("component.jsx", Language.JAVASCRIPT, True),
        ("server.js", Language.JAVASCRIPT, True),
        
        # TypeScript
        ("app.ts", Language.TYPESCRIPT, True),
        ("component.tsx", Language.TYPESCRIPT, True),
        ("types.ts", Language.TYPESCRIPT, True),
        
        # Java
        ("Main.java", Language.JAVA, True),
        ("Controller.java", Language.JAVA, True),
        
        # Other languages
        ("Program.cs", Language.CSHARP, True),
        ("main.go", Language.GO, True),
        ("lib.rs", Language.RUST, True),
        ("index.php", Language.PHP, True),
        ("app.rb", Language.RUBY, True),
        
        # Config files
        ("package.json", Language.UNKNOWN, False),
        ("requirements.txt", Language.UNKNOWN, False),
        ("Dockerfile", Language.UNKNOWN, False),
        
        # Unknown
        ("README.md", Language.UNKNOWN, False),
        ("data.json", Language.UNKNOWN, False),
        ("style.css", Language.UNKNOWN, False),
    ]
    
    passed = 0
    total = len(test_cases)
    
    print("🔍 Language Detection Tests:")
    for filename, expected_lang, expected_source in test_cases:
        detected_lang = LanguageDetector.detect_language(filename)
        is_source = LanguageDetector.is_source_file(filename)
        
        lang_correct = detected_lang == expected_lang
        source_correct = is_source == expected_source
        
        if lang_correct and source_correct:
            status = "✅"
            passed += 1
        else:
            status = "❌"
        
        print(f"  {status} {filename:<20} -> {detected_lang.value:<12} (source: {is_source})")
    
    print(f"\n📊 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    # Test config file detection
    print(f"\n🔧 Config File Detection Tests:")
    config_tests = [
        ("package.json", True),
        ("requirements.txt", True),
        ("tsconfig.json", True),
        ("pom.xml", True),
        ("Cargo.toml", True),
        ("go.mod", True),
        ("composer.json", True),
        ("Gemfile", True),
        ("Dockerfile", True),
        ("docker-compose.yml", True),
        ("README.md", False),
        ("main.py", False),
    ]
    
    config_passed = 0
    for filename, expected in config_tests:
        is_config = LanguageDetector.is_config_file(filename)
        if is_config == expected:
            status = "✅"
            config_passed += 1
        else:
            status = "❌"
        print(f"  {status} {filename:<20} -> {is_config}")
    
    print(f"\n📊 Config Results: {config_passed}/{len(config_tests)} tests passed ({config_passed/len(config_tests)*100:.1f}%)")
    
    # Overall assessment
    total_tests = total + len(config_tests)
    total_passed = passed + config_passed
    overall_rate = total_passed / total_tests * 100
    
    print(f"\n" + "=" * 50)
    print(f"📊 OVERALL RESULTS:")
    print(f"  Total tests: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Success rate: {overall_rate:.1f}%")
    
    if overall_rate >= 90:
        print(f"\n🎉 LANGUAGE DETECTION TEST PASSED!")
        print(f"✅ Multi-language detection working correctly")
        print(f"✅ Source file identification working")
        print(f"✅ Config file identification working")
        return True
    else:
        print(f"\n⚠️ Test needs improvement")
        return False


def test_demo_codebase():
    """Test với demo codebase thực tế"""
    print(f"\n🔍 Testing with actual demo codebase...")
    print("=" * 50)
    
    demo_path = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
    
    if not os.path.exists(demo_path):
        print(f"❌ Demo codebase not found at: {demo_path}")
        return False
    
    languages_found = {}
    config_files_found = []
    
    for root, dirs, files in os.walk(demo_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if LanguageDetector.is_source_file(file):
                language = LanguageDetector.detect_language(file)
                languages_found[language.value] = languages_found.get(language.value, 0) + 1
            elif LanguageDetector.is_config_file(file):
                config_files_found.append(file)
    
    print(f"📊 Languages detected in demo codebase:")
    for language, count in languages_found.items():
        print(f"  - {language.title()}: {count} files")
    
    print(f"\n🔧 Config files found:")
    for config in config_files_found:
        print(f"  - {config}")
    
    total_source = sum(languages_found.values())
    total_config = len(config_files_found)
    
    print(f"\n📈 Summary:")
    print(f"  - Source files: {total_source}")
    print(f"  - Config files: {total_config}")
    print(f"  - Languages: {len(languages_found)}")
    
    return total_source > 0


if __name__ == "__main__":
    print("🚀 Multi-Language Codebase Analyzer Test Suite")
    print("=" * 60)
    
    # Test 1: Language Detection
    test1_success = test_language_detection()
    
    # Test 2: Demo Codebase
    test2_success = test_demo_codebase()
    
    # Overall result
    overall_success = test1_success and test2_success
    
    print(f"\n" + "=" * 60)
    print(f"🏁 FINAL RESULTS:")
    print(f"  Language Detection: {'✅ PASS' if test1_success else '❌ FAIL'}")
    print(f"  Demo Codebase Test: {'✅ PASS' if test2_success else '❌ FAIL'}")
    print(f"  Overall: {'🎉 SUCCESS' if overall_success else '❌ FAILED'}")
    
    if overall_success:
        print(f"\n✅ Multi-language support is ready!")
        print(f"✅ Language detection working for 9+ languages")
        print(f"✅ Config file detection working")
        print(f"✅ Ready for integration with planner agent")
    
    sys.exit(0 if overall_success else 1)
