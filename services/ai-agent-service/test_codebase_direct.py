#!/usr/bin/env python3
"""
Test script để kiểm tra codebase analyzer trực tiếp
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class CodebaseAnalyzer:
    """Analyzer để đọc và phân tích codebase structure"""
    
    def __init__(self, codebase_path: str):
        """
        Initialize analyzer với path tới codebase
        
        Args:
            codebase_path: Absolute path tới thư mục codebase cần phân tích
        """
        self.codebase_path = Path(codebase_path)
        if not self.codebase_path.exists():
            raise ValueError(f"Codebase path không tồn tại: {codebase_path}")
    
    def get_file_structure(self) -> Dict[str, List[str]]:
        """
        Lấy cấu trúc files trong codebase
        
        Returns:
            Dict với key là thư mục, value là list files
        """
        structure = {}
        
        for root, dirs, files in os.walk(self.codebase_path):
            # Skip hidden directories và __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            relative_root = os.path.relpath(root, self.codebase_path)
            if relative_root == '.':
                relative_root = 'root'
            
            # Filter Python files và important config files
            python_files = [f for f in files if f.endswith('.py')]
            config_files = [f for f in files if f in ['pyproject.toml', 'requirements.txt', 'Dockerfile', 'docker-compose.yml']]
            
            if python_files or config_files:
                structure[relative_root] = python_files + config_files
        
        return structure
    
    def analyze_python_file(self, file_path: str) -> Dict:
        """
        Phân tích một Python file để extract classes, functions, imports
        
        Args:
            file_path: Relative path từ codebase root
            
        Returns:
            Dict chứa thông tin về file
        """
        full_path = self.codebase_path / file_path
        if not full_path.exists() or not full_path.suffix == '.py':
            return {}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({
                        'name': node.name,
                        'methods': methods,
                        'line': node.lineno
                    })
                elif isinstance(node, ast.FunctionDef) and not any(node.lineno >= cls['line'] for cls in classes):
                    # Only top-level functions (not methods)
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [arg.arg for arg in node.args.args]
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ''
                        for alias in node.names:
                            imports.append(f"{module}.{alias.name}" if module else alias.name)
            
            return {
                'path': file_path,
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'lines': len(content.splitlines())
            }
            
        except Exception as e:
            return {
                'path': file_path,
                'error': str(e),
                'classes': [],
                'functions': [],
                'imports': [],
                'lines': 0
            }
    
    def get_codebase_summary(self) -> Dict:
        """
        Tạo summary tổng quan về codebase
        
        Returns:
            Dict chứa thông tin tổng quan
        """
        structure = self.get_file_structure()
        
        # Count statistics
        total_files = sum(len(files) for files in structure.values())
        python_files = sum(len([f for f in files if f.endswith('.py')]) for files in structure.values())
        
        return {
            'structure': structure,
            'statistics': {
                'total_files': total_files,
                'python_files': python_files,
                'directories': len(structure)
            }
        }


def analyze_codebase_context(codebase_path: str) -> str:
    """
    Phân tích codebase và tạo context string cho LLM
    
    Args:
        codebase_path: Path tới codebase cần phân tích
        
    Returns:
        Formatted string chứa codebase context
    """
    try:
        analyzer = CodebaseAnalyzer(codebase_path)
        summary = analyzer.get_codebase_summary()
        
        context = f"""
## EXISTING CODEBASE ANALYSIS

### File Structure:
"""
        
        for directory, files in summary['structure'].items():
            context += f"\n**{directory}/**\n"
            for file in files:
                if file.endswith('.py'):
                    file_analysis = analyzer.analyze_python_file(f"{directory}/{file}" if directory != 'root' else file)
                    classes = [cls['name'] for cls in file_analysis.get('classes', [])]
                    functions = [func['name'] for func in file_analysis.get('functions', [])]
                    
                    context += f"  - {file}"
                    if classes:
                        context += f" (Classes: {', '.join(classes)})"
                    if functions:
                        context += f" (Functions: {', '.join(functions)})"
                    context += "\n"
                else:
                    context += f"  - {file}\n"
        
        context += f"""
### Statistics:
- Total files: {summary['statistics']['total_files']}
- Python files: {summary['statistics']['python_files']}
- Directories: {summary['statistics']['directories']}
"""
        
        return context
        
    except Exception as e:
        return f"Error analyzing codebase: {str(e)}"


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
        print(context[:1500] + "..." if len(context) > 1500 else context)
        print("=" * 60)
        
        # Check for key information
        checks = [
            ("File Structure", "### File Structure:" in context),
            ("Statistics", "### Statistics:" in context),
            ("Python files", "Python files:" in context),
            ("Classes found", "Classes:" in context or "Functions:" in context),
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
    print(f"\n{'🎉 SUCCESS' if success else '❌ FAILED'}")
