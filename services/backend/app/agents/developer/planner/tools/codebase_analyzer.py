"""
Multi-Language Codebase Analysis Tools for Planner Agent

Tools để phân tích codebase thực tế từ nhiều ngôn ngữ lập trình và cung cấp context cho LLM
Hỗ trợ: Python, JavaScript/TypeScript, Java, C#, Go, Rust, PHP, Ruby
"""

import ast
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path


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
        ".py": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".jsx": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".tsx": Language.TYPESCRIPT,
        ".java": Language.JAVA,
        ".cs": Language.CSHARP,
        ".go": Language.GO,
        ".rs": Language.RUST,
        ".php": Language.PHP,
        ".rb": Language.RUBY,
    }

    CONFIG_FILES = {
        # Python
        "pyproject.toml",
        "requirements.txt",
        "setup.py",
        "Pipfile",
        # JavaScript/TypeScript
        "package.json",
        "tsconfig.json",
        "webpack.config.js",
        "vite.config.js",
        # Java
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        # C#
        "*.csproj",
        "*.sln",
        "packages.config",
        # Go
        "go.mod",
        "go.sum",
        # Rust
        "Cargo.toml",
        "Cargo.lock",
        # PHP
        "composer.json",
        "composer.lock",
        # Ruby
        "Gemfile",
        "Gemfile.lock",
        "*.gemspec",
        # General
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
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
            file_name.endswith(config.replace("*", ""))
            for config in cls.CONFIG_FILES
            if "*" in config
        )


class LanguageAnalyzer(ABC):
    """Abstract base class for language-specific analyzers"""

    @abstractmethod
    def analyze_file(self, file_path: Path, content: str) -> dict:
        """
        Analyze a source file and extract structural information

        Args:
            file_path: Path to the file
            content: File content as string

        Returns:
            Dict containing classes, functions, imports, etc.
        """
        pass

    @abstractmethod
    def get_api_patterns(self) -> list[str]:
        """Get regex patterns for API endpoints in this language"""
        pass

    @abstractmethod
    def get_model_patterns(self) -> list[str]:
        """Get regex patterns for data models in this language"""
        pass


class PythonAnalyzer(LanguageAnalyzer):
    """Analyzer for Python files using AST"""

    def analyze_file(self, file_path: Path, content: str) -> dict:
        """Analyze Python file using AST"""
        try:
            tree = ast.parse(content)

            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ]
                    classes.append(
                        {"name": node.name, "methods": methods, "line": node.lineno}
                    )
                elif isinstance(node, ast.FunctionDef) and not any(
                    node.lineno >= cls["line"] for cls in classes
                ):
                    # Only top-level functions (not methods)
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                        }
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(
                                f"{module}.{alias.name}" if module else alias.name
                            )

            return {
                "language": Language.PYTHON.value,
                "path": str(file_path),
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "lines": len(content.splitlines()),
            }

        except Exception as e:
            return {
                "language": Language.PYTHON.value,
                "path": str(file_path),
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": [],
                "lines": 0,
            }

    def get_api_patterns(self) -> list[str]:
        """FastAPI and Flask patterns"""
        return [
            r"@app\.(get|post|put|delete|patch)",  # FastAPI routes
            r"@router\.(get|post|put|delete|patch)",  # FastAPI router
            r"@bp\.(route|get|post|put|delete)",  # Flask blueprint
            r"def (get|post|put|delete|patch)_\w+",  # Function names
        ]

    def get_model_patterns(self) -> list[str]:
        """SQLAlchemy and Pydantic patterns"""
        return [
            r"class \w+\(.*Base.*\):",  # SQLAlchemy models
            r"class \w+\(.*BaseModel.*\):",  # Pydantic models
            r"class \w+\(.*Model.*\):",  # Django/other models
        ]


class JavaScriptTypeScriptAnalyzer(LanguageAnalyzer):
    """Analyzer for JavaScript and TypeScript files using regex"""

    def analyze_file(self, file_path: Path, content: str) -> dict:
        """Analyze JS/TS file using regex patterns"""
        try:
            classes = self._extract_classes(content)
            functions = self._extract_functions(content)
            imports = self._extract_imports(content)
            interfaces = (
                self._extract_interfaces(content)
                if file_path.suffix in [".ts", ".tsx"]
                else []
            )

            return {
                "language": (
                    Language.TYPESCRIPT.value
                    if file_path.suffix in [".ts", ".tsx"]
                    else Language.JAVASCRIPT.value
                ),
                "path": str(file_path),
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "interfaces": interfaces,
                "lines": len(content.splitlines()),
            }

        except Exception as e:
            return {
                "language": (
                    Language.TYPESCRIPT.value
                    if file_path.suffix in [".ts", ".tsx"]
                    else Language.JAVASCRIPT.value
                ),
                "path": str(file_path),
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": [],
                "interfaces": [],
                "lines": 0,
            }

    def _extract_classes(self, content: str) -> list[dict]:
        """Extract class definitions"""
        classes = []
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+\w+)?\s*\{"
        method_pattern = r"(\w+)\s*\([^)]*\)\s*\{"

        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            # Find methods in this class (simplified)
            class_start = match.end()
            brace_count = 1
            class_end = class_start

            for i, char in enumerate(content[class_start:], class_start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i
                        break

            class_content = content[class_start:class_end]
            methods = [m.group(1) for m in re.finditer(method_pattern, class_content)]

            classes.append({"name": class_name, "methods": methods, "line": line_num})

        return classes

    def _extract_functions(self, content: str) -> list[dict]:
        """Extract function definitions"""
        functions = []

        # Regular functions
        func_patterns = [
            r"function\s+(\w+)\s*\([^)]*\)",
            r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>",
            r"let\s+(\w+)\s*=\s*\([^)]*\)\s*=>",
            r"var\s+(\w+)\s*=\s*\([^)]*\)\s*=>",
            r"export\s+function\s+(\w+)\s*\([^)]*\)",
            # Regular methods
            r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*{",
            # Static methods
            r"static\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*{",
            # Arrow functions
            r"(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
            # Getter/Setter
            r"(?:get|set)\s+(\w+)\s*\([^)]*\)\s*{",
        ]

        for pattern in func_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1
                functions.append(
                    {"name": func_name, "line": line_num, "type": "function"}
                )

        return functions

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements"""
        imports = []

        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'const\s+.*?\s*=\s*require\([\'"]([^\'"]+)[\'"]\)',
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, content):
                imports.append(match.group(1))

        return imports

    def _extract_interfaces(self, content: str) -> list[dict]:
        """Extract TypeScript interfaces"""
        interfaces = []
        interface_pattern = r"interface\s+(\w+)(?:\s+extends\s+[\w,\s]+)?\s*\{"

        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            interface_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            interfaces.append({"name": interface_name, "line": line_num})

        return interfaces

    def get_api_patterns(self) -> list[str]:
        """Express.js and other JS framework patterns"""
        return [
            r"app\.(get|post|put|delete|patch)\s*\(",  # Express routes
            r"router\.(get|post|put|delete|patch)\s*\(",  # Express router
            r"@(Get|Post|Put|Delete|Patch)\s*\(",  # NestJS decorators
            r"export\s+async\s+function\s+(get|post|put|delete|patch)\w*",  # Next.js API routes
        ]

    def get_model_patterns(self) -> list[str]:
        """JavaScript/TypeScript model patterns"""
        return [
            r"interface\s+\w+.*\{",  # TypeScript interfaces
            r"type\s+\w+\s*=\s*\{",  # TypeScript types
            r"class\s+\w+.*Model.*\{",  # Model classes
            r"const\s+\w+Schema\s*=",  # Mongoose schemas
        ]


class CodebaseAnalyzer:
    """Multi-language codebase analyzer"""

    def __init__(self, codebase_path: str):
        """
        Initialize analyzer với path tới codebase

        Args:
            codebase_path: Absolute path tới thư mục codebase cần phân tích
        """
        self.codebase_path = Path(codebase_path)
        if not self.codebase_path.exists():
            raise ValueError(f"Codebase path không tồn tại: {codebase_path}")

        # Initialize language-specific analyzers
        self.analyzers = {
            Language.PYTHON: PythonAnalyzer(),
            Language.JAVASCRIPT: JavaScriptTypeScriptAnalyzer(),
            Language.TYPESCRIPT: JavaScriptTypeScriptAnalyzer(),
        }

    def get_file_structure(self) -> dict[str, list[str]]:
        """
        Lấy cấu trúc files trong codebase với multi-language support

        Returns:
            Dict với key là thư mục, value là list files (source + config)
        """
        structure = {}

        for root, dirs, files in os.walk(self.codebase_path):
            # Skip hidden directories và __pycache__, node_modules
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["__pycache__", "node_modules", "target", "bin", "obj"]
            ]

            relative_root = os.path.relpath(root, self.codebase_path)
            if relative_root == ".":
                relative_root = "root"

            # Filter source files và config files
            source_files = [f for f in files if LanguageDetector.is_source_file(f)]
            config_files = [f for f in files if LanguageDetector.is_config_file(f)]

            if source_files or config_files:
                structure[relative_root] = source_files + config_files

        return structure

    def get_language_statistics(self) -> dict[str, int]:
        """
        Thống kê số lượng files theo ngôn ngữ

        Returns:
            Dict với key là language, value là số lượng files
        """
        stats = {}

        for root, dirs, files in os.walk(self.codebase_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in ["__pycache__", "node_modules", "target", "bin", "obj"]
            ]

            for file in files:
                if LanguageDetector.is_source_file(file):
                    language = LanguageDetector.detect_language(file)
                    stats[language.value] = stats.get(language.value, 0) + 1

        return stats

    def analyze_file_by_language(self, file_path: str) -> dict:
        """
        Phân tích file dựa trên ngôn ngữ được detect

        Args:
            file_path: Relative path từ codebase root

        Returns:
            Dict chứa thông tin về file
        """
        full_path = self.codebase_path / file_path
        if not full_path.exists():
            return {}

        language = LanguageDetector.detect_language(file_path)
        if language == Language.UNKNOWN:
            return {}

        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            # Use appropriate analyzer
            if language in self.analyzers:
                return self.analyzers[language].analyze_file(full_path, content)
            else:
                # Fallback for unsupported languages
                return {
                    "language": language.value,
                    "path": file_path,
                    "classes": [],
                    "functions": [],
                    "imports": [],
                    "lines": len(content.splitlines()),
                    "note": "Language analyzer not implemented yet",
                }

        except Exception as e:
            return {
                "language": language.value,
                "path": file_path,
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": [],
                "lines": 0,
            }

    def analyze_python_file(self, file_path: str) -> dict:
        """
        Phân tích một Python file để extract classes, functions, imports

        Args:
            file_path: Relative path từ codebase root

        Returns:
            Dict chứa thông tin về file
        """
        full_path = self.codebase_path / file_path
        if not full_path.exists() or not full_path.suffix == ".py":
            return {}

        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            classes = []
            functions = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [
                        n.name for n in node.body if isinstance(n, ast.FunctionDef)
                    ]
                    classes.append(
                        {"name": node.name, "methods": methods, "line": node.lineno}
                    )
                elif isinstance(node, ast.FunctionDef) and not any(
                    node.lineno >= cls["line"] for cls in classes
                ):
                    # Only top-level functions (not methods)
                    functions.append(
                        {
                            "name": node.name,
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                        }
                    )
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    else:  # ImportFrom
                        module = node.module or ""
                        for alias in node.names:
                            imports.append(
                                f"{module}.{alias.name}" if module else alias.name
                            )

            return {
                "path": file_path,
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "lines": len(content.splitlines()),
            }

        except Exception as e:
            return {
                "path": file_path,
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": [],
                "lines": 0,
            }

    def get_dependencies(self) -> dict[str, list[str]]:
        """
        Phân tích dependencies giữa các modules

        Returns:
            Dict với key là file, value là list dependencies
        """
        dependencies = {}

        # Get all Python files
        for root, dirs, files in os.walk(self.codebase_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.relpath(
                        os.path.join(root, file), self.codebase_path
                    )
                    analysis = self.analyze_python_file(file_path)

                    # Extract internal dependencies (imports from same codebase)
                    internal_deps = []
                    for imp in analysis.get("imports", []):
                        if imp.startswith("app.") or imp.startswith("."):
                            internal_deps.append(imp)

                    if internal_deps:
                        dependencies[file_path] = internal_deps

        return dependencies

    def search_patterns(self, patterns: list[str]) -> dict[str, list[dict]]:
        """
        Tìm kiếm patterns trong codebase với multi-language support

        Args:
            patterns: List regex patterns để tìm

        Returns:
            Dict với key là pattern, value là list matches
        """
        results = {}

        for pattern in patterns:
            regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
            matches = []

            for root, dirs, files in os.walk(self.codebase_path):
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d not in ["__pycache__", "node_modules", "target", "bin", "obj"]
                ]

                for file in files:
                    if LanguageDetector.is_source_file(file):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, self.codebase_path)

                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()

                            for match in regex.finditer(content):
                                line_num = content[: match.start()].count("\n") + 1
                                matches.append(
                                    {
                                        "file": relative_path,
                                        "line": line_num,
                                        "match": match.group().strip(),
                                        "context": self._get_context(
                                            content, match.start(), match.end()
                                        ),
                                    }
                                )
                        except Exception:
                            continue

            results[pattern] = matches

        return results

    def get_all_patterns(self) -> dict[str, list[str]]:
        """
        Lấy tất cả patterns từ các language analyzers

        Returns:
            Dict với key là pattern type, value là list patterns
        """
        all_api_patterns = []
        all_model_patterns = []

        for analyzer in self.analyzers.values():
            all_api_patterns.extend(analyzer.get_api_patterns())
            all_model_patterns.extend(analyzer.get_model_patterns())

        return {"api_patterns": all_api_patterns, "model_patterns": all_model_patterns}

    def _get_context(
        self, content: str, start: int, end: int, context_lines: int = 2
    ) -> str:
        """Get context lines around a match"""
        lines = content.splitlines()
        match_line = content[:start].count("\n")

        start_line = max(0, match_line - context_lines)
        end_line = min(len(lines), match_line + context_lines + 1)

        context = lines[start_line:end_line]
        return "\n".join(context)

    def get_codebase_summary(self) -> dict:
        """
        Tạo summary tổng quan về codebase với multi-language support

        Returns:
            Dict chứa thông tin tổng quan
        """
        structure = self.get_file_structure()
        dependencies = self.get_dependencies()
        language_stats = self.get_language_statistics()

        # Count statistics
        total_files = sum(len(files) for files in structure.values())
        source_files = sum(language_stats.values())

        # Get all patterns from language analyzers
        all_patterns = self.get_all_patterns()
        api_matches = self.search_patterns(all_patterns["api_patterns"])
        model_matches = self.search_patterns(all_patterns["model_patterns"])

        return {
            "structure": structure,
            "statistics": {
                "total_files": total_files,
                "source_files": source_files,
                "directories": len(structure),
                "languages": language_stats,
            },
            "dependencies": dependencies,
            "patterns": {
                "api_endpoints": sum(len(matches) for matches in api_matches.values()),
                "models": sum(len(matches) for matches in model_matches.values()),
            },
            "api_details": api_matches,
            "model_details": model_matches,
        }


def analyze_codebase_context(codebase_path: str) -> str:
    """
    Phân tích codebase và tạo context string cho LLM với multi-language support

    Args:
        codebase_path: Path tới codebase cần phân tích

    Returns:
        Formatted string chứa codebase context
    """
    try:
        analyzer = CodebaseAnalyzer(codebase_path)
        summary = analyzer.get_codebase_summary()

        context = """
## EXISTING CODEBASE ANALYSIS (Multi-Language)

### Languages Detected:
"""

        # Show language statistics
        for language, count in summary["statistics"]["languages"].items():
            context += f"- {language.title()}: {count} files\n"

        context += "\n### File Structure:\n"

        for directory, files in summary["structure"].items():
            context += f"\n**{directory}/**\n"
            for file in files:
                if LanguageDetector.is_source_file(file):
                    file_analysis = analyzer.analyze_file_by_language(
                        f"{directory}/{file}" if directory != "root" else file
                    )

                    language = file_analysis.get("language", "unknown")
                    classes = [cls["name"] for cls in file_analysis.get("classes", [])]
                    functions = [
                        func["name"] for func in file_analysis.get("functions", [])
                    ]
                    interfaces = [
                        iface["name"] for iface in file_analysis.get("interfaces", [])
                    ]

                    context += f"  - {file} ({language})"
                    if classes:
                        context += f" (Classes: {', '.join(classes)})"
                    if functions:
                        context += f" (Functions: {', '.join(functions)})"
                    if interfaces:
                        context += f" (Interfaces: {', '.join(interfaces)})"
                    context += "\n"
                else:
                    context += f"  - {file} (config)\n"

        context += f"""
### Statistics:
- Total files: {summary["statistics"]["total_files"]}
- Source files: {summary["statistics"]["source_files"]}
- Directories: {summary["statistics"]["directories"]}
- API endpoints found: {summary["patterns"]["api_endpoints"]}
- Models found: {summary["patterns"]["models"]}

### Existing API Patterns:
"""

        for pattern, matches in summary["api_details"].items():
            if matches:
                context += f"\n**Pattern: {pattern}**\n"
                for match in matches[:3]:  # Limit to first 3 matches
                    context += (
                        f"  - {match['file']}:{match['line']} - {match['match']}\n"
                    )

        context += "\n### Existing Models:\n"
        for pattern, matches in summary["model_details"].items():
            if matches:
                context += f"\n**Pattern: {pattern}**\n"
                for match in matches[:3]:  # Limit to first 3 matches
                    context += (
                        f"  - {match['file']}:{match['line']} - {match['match']}\n"
                    )

        context += """
### Dependencies:
"""
        for file, deps in list(summary["dependencies"].items())[:5]:  # Limit to first 5
            context += f"- {file}: {', '.join(deps)}\n"

        return context

    except Exception as e:
        return f"Error analyzing codebase: {str(e)}"
