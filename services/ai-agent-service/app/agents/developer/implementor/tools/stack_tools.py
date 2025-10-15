# app/agents/developer/implementor/tools/stack_tools.py
"""
Stack detection and boilerplate retrieval tools
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from langchain_core.tools import tool
import shutil


@tool
def detect_stack_tool(project_path: str) -> str:
    """
    Detect the technology stack of a project.
    
    This tool analyzes project files to identify the technology stack,
    frameworks, and dependencies being used.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        JSON string containing detected stack information
        
    Example:
        detect_stack_tool("./my-project")
    """
    try:
        project_dir = Path(project_path).resolve()
        
        if not project_dir.exists():
            return f"Error: Directory '{project_path}' does not exist"
        
        if not project_dir.is_dir():
            return f"Error: '{project_path}' is not a directory"
        
        stack_info = {
            "primary_language": None,
            "frameworks": [],
            "package_managers": [],
            "databases": [],
            "tools": [],
            "confidence": 0.0,
            "detected_files": [],
            "recommendations": []
        }
        
        # Stack detection patterns
        stack_patterns = {
            # Python
            "requirements.txt": {"language": "Python", "confidence": 0.9, "type": "package_manager"},
            "pyproject.toml": {"language": "Python", "confidence": 0.95, "type": "package_manager"},
            "setup.py": {"language": "Python", "confidence": 0.8, "type": "package_manager"},
            "Pipfile": {"language": "Python", "confidence": 0.9, "type": "package_manager"},
            "poetry.lock": {"language": "Python", "confidence": 0.95, "type": "package_manager"},
            
            # Node.js
            "package.json": {"language": "JavaScript", "confidence": 0.95, "type": "package_manager"},
            "yarn.lock": {"language": "JavaScript", "confidence": 0.8, "type": "package_manager"},
            "pnpm-lock.yaml": {"language": "JavaScript", "confidence": 0.8, "type": "package_manager"},
            "package-lock.json": {"language": "JavaScript", "confidence": 0.8, "type": "package_manager"},
            
            # Java
            "pom.xml": {"language": "Java", "confidence": 0.95, "type": "package_manager"},
            "build.gradle": {"language": "Java", "confidence": 0.9, "type": "package_manager"},
            "build.gradle.kts": {"language": "Kotlin", "confidence": 0.9, "type": "package_manager"},
            
            # .NET
            "*.csproj": {"language": "C#", "confidence": 0.9, "type": "project_file"},
            "*.sln": {"language": "C#", "confidence": 0.8, "type": "solution_file"},
            "packages.config": {"language": "C#", "confidence": 0.7, "type": "package_manager"},
            
            # Go
            "go.mod": {"language": "Go", "confidence": 0.95, "type": "package_manager"},
            "go.sum": {"language": "Go", "confidence": 0.8, "type": "package_manager"},
            
            # Rust
            "Cargo.toml": {"language": "Rust", "confidence": 0.95, "type": "package_manager"},
            "Cargo.lock": {"language": "Rust", "confidence": 0.8, "type": "package_manager"},
            
            # PHP
            "composer.json": {"language": "PHP", "confidence": 0.9, "type": "package_manager"},
            "composer.lock": {"language": "PHP", "confidence": 0.8, "type": "package_manager"},
            
            # Ruby
            "Gemfile": {"language": "Ruby", "confidence": 0.9, "type": "package_manager"},
            "Gemfile.lock": {"language": "Ruby", "confidence": 0.8, "type": "package_manager"},
            
            # Docker
            "Dockerfile": {"tool": "Docker", "confidence": 0.8, "type": "containerization"},
            "docker-compose.yml": {"tool": "Docker Compose", "confidence": 0.8, "type": "containerization"},
            "docker-compose.yaml": {"tool": "Docker Compose", "confidence": 0.8, "type": "containerization"},
        }
        
        detected_languages = {}
        detected_tools = []
        detected_files = []
        
        # Check for stack indicator files
        for root, dirs, files in os.walk(project_dir):
            # Skip hidden directories and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'target', 'build']]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_dir)
                
                # Check exact file matches
                if file in stack_patterns:
                    pattern = stack_patterns[file]
                    detected_files.append(str(relative_path))
                    
                    if "language" in pattern:
                        lang = pattern["language"]
                        confidence = pattern["confidence"]
                        detected_languages[lang] = max(detected_languages.get(lang, 0), confidence)
                    
                    if "tool" in pattern:
                        detected_tools.append(pattern["tool"])
                
                # Check pattern matches (like *.csproj)
                for pattern_key, pattern_info in stack_patterns.items():
                    if "*" in pattern_key:
                        extension = pattern_key.replace("*", "")
                        if file.endswith(extension):
                            detected_files.append(str(relative_path))
                            
                            if "language" in pattern_info:
                                lang = pattern_info["language"]
                                confidence = pattern_info["confidence"]
                                detected_languages[lang] = max(detected_languages.get(lang, 0), confidence)
        
        # Determine primary language
        if detected_languages:
            primary_lang = max(detected_languages.items(), key=lambda x: x[1])
            stack_info["primary_language"] = primary_lang[0]
            stack_info["confidence"] = primary_lang[1]
        
        # Detect frameworks based on dependencies
        frameworks = detect_frameworks(project_dir, stack_info["primary_language"])
        stack_info["frameworks"] = frameworks
        
        # Detect databases
        databases = detect_databases(project_dir)
        stack_info["databases"] = databases
        
        stack_info["tools"] = list(set(detected_tools))
        stack_info["detected_files"] = detected_files
        
        # Generate recommendations
        recommendations = generate_stack_recommendations(stack_info)
        stack_info["recommendations"] = recommendations
        
        return json.dumps(stack_info, indent=2)
        
    except Exception as e:
        return f"Error detecting stack: {str(e)}"


def detect_frameworks(project_dir: Path, primary_language: Optional[str]) -> List[str]:
    """Detect frameworks based on dependencies and file patterns"""
    frameworks = []
    
    if primary_language == "Python":
        # Check requirements.txt
        req_file = project_dir / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    content = f.read().lower()
                    if "fastapi" in content:
                        frameworks.append("FastAPI")
                    if "django" in content:
                        frameworks.append("Django")
                    if "flask" in content:
                        frameworks.append("Flask")
                    if "streamlit" in content:
                        frameworks.append("Streamlit")
            except:
                pass
        
        # Check pyproject.toml
        pyproject_file = project_dir / "pyproject.toml"
        if pyproject_file.exists():
            try:
                with open(pyproject_file, 'r') as f:
                    content = f.read().lower()
                    if "fastapi" in content:
                        frameworks.append("FastAPI")
                    if "django" in content:
                        frameworks.append("Django")
                    if "flask" in content:
                        frameworks.append("Flask")
            except:
                pass
    
    elif primary_language == "JavaScript":
        # Check package.json
        package_file = project_dir / "package.json"
        if package_file.exists():
            try:
                with open(package_file, 'r') as f:
                    package_data = json.load(f)
                    deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                    
                    if "react" in deps:
                        frameworks.append("React")
                    if "vue" in deps:
                        frameworks.append("Vue.js")
                    if "@angular/core" in deps:
                        frameworks.append("Angular")
                    if "express" in deps:
                        frameworks.append("Express.js")
                    if "next" in deps:
                        frameworks.append("Next.js")
                    if "nuxt" in deps:
                        frameworks.append("Nuxt.js")
                    if "svelte" in deps:
                        frameworks.append("Svelte")
                    if "nestjs" in deps or "@nestjs/core" in deps:
                        frameworks.append("NestJS")
            except:
                pass
    
    return list(set(frameworks))


def detect_databases(project_dir: Path) -> List[str]:
    """Detect database usage from configuration files and dependencies"""
    databases = []
    
    # Common database indicators
    db_patterns = {
        "postgresql": ["psycopg2", "pg", "postgres", "postgresql"],
        "mysql": ["mysql", "pymysql", "mysql2"],
        "sqlite": ["sqlite3", "sqlite"],
        "mongodb": ["pymongo", "mongoose", "mongodb"],
        "redis": ["redis", "redis-py"],
        "elasticsearch": ["elasticsearch"],
    }
    
    # Check Python requirements
    req_file = project_dir / "requirements.txt"
    if req_file.exists():
        try:
            with open(req_file, 'r') as f:
                content = f.read().lower()
                for db, patterns in db_patterns.items():
                    if any(pattern in content for pattern in patterns):
                        databases.append(db.title())
        except:
            pass
    
    # Check Node.js dependencies
    package_file = project_dir / "package.json"
    if package_file.exists():
        try:
            with open(package_file, 'r') as f:
                package_data = json.load(f)
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                
                for db, patterns in db_patterns.items():
                    if any(pattern in deps for pattern in patterns):
                        databases.append(db.title())
        except:
            pass
    
    return list(set(databases))


def generate_stack_recommendations(stack_info: Dict) -> List[str]:
    """Generate recommendations based on detected stack"""
    recommendations = []
    
    primary_lang = stack_info.get("primary_language")
    frameworks = stack_info.get("frameworks", [])
    
    if primary_lang == "Python":
        if not frameworks:
            recommendations.append("Consider using FastAPI for modern web APIs or Flask for simpler applications")
        if "FastAPI" in frameworks:
            recommendations.append("FastAPI detected - consider adding Pydantic models and automatic API documentation")
        recommendations.append("Consider using virtual environments (venv or conda) for dependency management")
    
    elif primary_lang == "JavaScript":
        if "React" in frameworks:
            recommendations.append("React detected - consider using TypeScript for better type safety")
        if not any(fw in frameworks for fw in ["React", "Vue.js", "Angular"]):
            recommendations.append("Consider using a modern frontend framework like React, Vue.js, or Angular")
    
    if not stack_info.get("databases"):
        recommendations.append("No database detected - consider adding database integration if needed")
    
    return recommendations


@tool
def retrieve_boilerplate_tool(
    stack: str,
    template_name: str = "basic",
    target_directory: str = ".",
    boilerplate_path: str = None
) -> str:
    """
    Retrieve boilerplate code from templates based on detected stack.
    
    This tool copies boilerplate code from the templates directory
    to the target project directory.
    
    Args:
        stack: Technology stack (e.g., "python", "nodejs", "java")
        template_name: Specific template to use (e.g., "basic", "api", "fullstack")
        target_directory: Directory to copy boilerplate to
        boilerplate_path: Path to boilerplate templates (optional)
        
    Returns:
        Status message about boilerplate retrieval
        
    Example:
        retrieve_boilerplate_tool("python", "fastapi-basic", "./my-project")
    """
    try:
        target_dir = Path(target_directory).resolve()
        
        # Set default boilerplate path if not provided
        if boilerplate_path is None:
            # Default to the templates/boilerplate directory
            current_file = Path(__file__).resolve()
            boilerplate_path = current_file.parent.parent.parent.parent / "templates" / "boilerplate"
        else:
            boilerplate_path = Path(boilerplate_path).resolve()
        
        if not boilerplate_path.exists():
            return f"Error: Boilerplate templates directory '{boilerplate_path}' does not exist"
        
        # Normalize stack name
        stack_normalized = stack.lower().replace(" ", "").replace(".", "")
        stack_mapping = {
            "python": "python",
            "javascript": "nodejs", 
            "nodejs": "nodejs",
            "node": "nodejs",
            "java": "java",
            "csharp": "csharp",
            "c#": "csharp",
            "go": "go",
            "rust": "rust",
            "php": "php",
            "ruby": "ruby"
        }
        
        mapped_stack = stack_mapping.get(stack_normalized, stack_normalized)
        
        # Look for available templates
        available_templates = []
        stack_dir = boilerplate_path / mapped_stack
        
        if stack_dir.exists():
            for item in stack_dir.iterdir():
                if item.is_dir():
                    available_templates.append(item.name)
        
        # If no specific stack directory, check for generic templates
        if not available_templates:
            # Check for demo or generic templates
            demo_dir = boilerplate_path / "demo"
            if demo_dir.exists():
                template_source = demo_dir
                template_used = "demo"
            else:
                return f"Error: No boilerplate templates found for stack '{stack}'"
        else:
            # Use specific template
            if template_name in available_templates:
                template_source = stack_dir / template_name
                template_used = f"{mapped_stack}/{template_name}"
            elif "basic" in available_templates:
                template_source = stack_dir / "basic"
                template_used = f"{mapped_stack}/basic"
            else:
                template_source = stack_dir / available_templates[0]
                template_used = f"{mapped_stack}/{available_templates[0]}"
        
        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy boilerplate files
        copied_files = []
        skipped_files = []
        
        def copy_template_files(src_dir: Path, dst_dir: Path, relative_path: str = ""):
            for item in src_dir.iterdir():
                if item.name.startswith('.'):
                    continue
                
                src_item = src_dir / item.name
                dst_item = dst_dir / item.name
                item_relative_path = f"{relative_path}/{item.name}" if relative_path else item.name
                
                if src_item.is_dir():
                    dst_item.mkdir(exist_ok=True)
                    copy_template_files(src_item, dst_item, item_relative_path)
                else:
                    if dst_item.exists():
                        skipped_files.append(item_relative_path)
                    else:
                        shutil.copy2(src_item, dst_item)
                        copied_files.append(item_relative_path)
        
        copy_template_files(template_source, target_dir)
        
        result = {
            "status": "success",
            "message": f"Retrieved boilerplate template '{template_used}'",
            "stack": stack,
            "template": template_used,
            "target_directory": str(target_dir),
            "available_templates": available_templates,
            "files_copied": len(copied_files),
            "files_skipped": len(skipped_files),
            "copied_files": copied_files[:10],  # Show first 10 files
            "skipped_files": skipped_files[:5],  # Show first 5 skipped files
            "next_steps": [
                "Review the copied boilerplate files",
                "Customize configuration files for your project",
                "Install dependencies using the appropriate package manager",
                "Update README.md with your project information"
            ]
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error retrieving boilerplate: {str(e)}"
