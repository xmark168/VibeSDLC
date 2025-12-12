"""FileRepository for zero-shot test planning. Pre-computes workspace context for instant planning."""
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FileRepository:
    """Pre-computed workspace context: file tree, API routes, components, schemas."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.files: Dict[str, str] = {}
        self.file_tree: List[str] = []
        self.components: Dict[str, str] = {}
        self.api_routes: List[str] = []
        self.test_files: List[str] = []
        self.component_analysis: Dict[str, Dict] = {}
        
        if workspace_path and os.path.exists(workspace_path):
            self._scan()
    
    def _scan(self):
        """Scan workspace to build context."""
        exclude_dirs = {'node_modules', '.next', '.git', '__pycache__', '.prisma', 'dist', 'build'}
        
        for root, dirs, files in os.walk(self.workspace_path):
            # Filter excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for f in files:
                if f.endswith(('.ts', '.tsx', '.prisma', '.json', '.md')):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.workspace_path).replace('\\', '/')
                    
                    self.file_tree.append(rel_path)
                    
                    # Load important files
                    if self._is_important(rel_path):
                        self.files[rel_path] = self._read_file(full_path)
                    
                    # Track components (exclude UI primitives)
                    if '/components/' in rel_path and rel_path.endswith('.tsx') and '/ui/' not in rel_path:
                        name = os.path.basename(rel_path).replace('.tsx', '')
                        import_path = '@/' + rel_path.replace('.tsx', '')
                        self.components[name] = import_path
                        
                        # Analyze component for unit tests
                        content = self._read_file(full_path)
                        if content:
                            self.component_analysis[rel_path] = self._analyze_component(rel_path, content)
                    
                    # Track API routes
                    if '/api/' in rel_path and rel_path.endswith('route.ts'):
                        self.api_routes.append(rel_path)
                    
                    # Track existing test files
                    if '.test.' in rel_path or '__tests__' in rel_path:
                        self.test_files.append(rel_path)
        
        logger.info(f"[FileRepository] Scanned: {len(self.file_tree)} files, "
                   f"{len(self.components)} components, {len(self.api_routes)} routes")
    
    def _is_important(self, path: str) -> bool:
        """Check if file should be pre-loaded."""
        important_patterns = [
            'prisma/schema.prisma',
            'src/types/index.ts',
            'src/types/',
            'package.json',
            'src/app/layout.tsx',
            'src/lib/prisma.ts',
            'jest.config.ts',
            'jest.setup.ts',
            'tsconfig.json',
        ]
        return any(p in path for p in important_patterns)
    
    def _read_file(self, full_path: str) -> str:
        """Read file content safely."""
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def _analyze_component(self, file_path: str, content: str) -> Dict:
        """Analyze component for unit test generation.
        
        Extracts:
        - Component name
        - Props interface
        - Data attributes
        - Exports
        - Has loading/skeleton state
        - Uses fetch/useEffect
        """
        info = {
            "name": "",
            "path": file_path,
            "props": [],
            "data_attributes": [],
            "exports": [],
            "has_skeleton": False,
            "has_fetch": False,
            "has_use_effect": False,
        }
        
        # Extract component name
        filename = file_path.split("/")[-1].replace(".tsx", "").replace(".ts", "")
        info["name"] = filename
        
        # Extract exports
        export_patterns = [
            r'export\s+(?:function|const)\s+(\w+)',
            r'export\s+default\s+(?:function\s+)?(\w+)',
        ]
        for pattern in export_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match and match not in info["exports"]:
                    info["exports"].append(match)
        
        # Extract props from interface/type
        props_pattern = r'(?:interface|type)\s+\w*Props\w*\s*(?:=\s*)?\{([^}]+)\}'
        props_match = re.search(props_pattern, content, re.DOTALL)
        if props_match:
            props_content = props_match.group(1)
            prop_names = re.findall(r'(\w+)\s*[?:]', props_content)
            info["props"] = list(set(prop_names))[:10]
        
        # Extract data attributes
        data_attrs = re.findall(r'data-(\w+)(?:=|["\'])', content)
        info["data_attributes"] = list(set(data_attrs))
        
        # Check for skeleton/loading patterns
        content_lower = content.lower()
        if "skeleton" in content_lower or "loading" in content_lower:
            info["has_skeleton"] = True
        
        # Check for fetch/useEffect (async component)
        if "useeffect" in content_lower:
            info["has_use_effect"] = True
        if "fetch(" in content_lower or "usefetch" in content_lower:
            info["has_fetch"] = True
        
        return info
    
    def get_api_source_code(self, max_routes: int = 10) -> str:
        """Get source code of API routes for context."""
        if not self.api_routes:
            return "No API routes found."
        
        parts = []
        for route in self.api_routes[:max_routes]:
            full_path = os.path.join(self.workspace_path, route)
            if os.path.exists(full_path):
                try:
                    content = self._read_file(full_path)
                    if len(content) > 2000:
                        content = content[:2000] + "\n// ... (truncated)"
                    
                    # Extract route URL from path
                    route_url = route.replace("src/app", "").replace("app", "")
                    route_url = route_url.replace("/route.ts", "").replace("\\", "/")
                    if not route_url.startswith("/"):
                        route_url = "/" + route_url
                    
                    parts.append(f"### {route_url}\nFile: {route}\n```typescript\n{content}\n```")
                except Exception:
                    pass
        
        return "\n\n".join(parts) if parts else "No API source code available."
    
    def get_components_for_keywords(self, keywords: List[str], max_results: int = 10) -> List[Dict]:
        """Find components matching keywords for unit testing.
        
        Scores components by keyword relevance and returns top matches.
        """
        scored_components = []
        
        for path, analysis in self.component_analysis.items():
            score = 0
            path_lower = path.lower()
            name_lower = analysis.get("name", "").lower()
            
            for keyword in keywords:
                kw_lower = keyword.lower()
                if kw_lower in name_lower:
                    score += 3  # Name match is most relevant
                if kw_lower in path_lower:
                    score += 2
            
            if score > 0:
                scored_components.append({**analysis, "score": score})
        
        # Sort by score and return top matches
        scored_components.sort(key=lambda x: x.get("score", 0), reverse=True)
        return scored_components[:max_results]
    
    def format_component_context(self, components: List[Dict] = None) -> str:
        """Format component analysis for LLM context."""
        if components is None:
            components = list(self.component_analysis.values())[:10]
        
        if not components:
            return "No components found for unit testing."
        
        lines = ["## Components for Unit Testing:\n"]
        
        for comp in components:
            lines.append(f"### {comp.get('name', 'Unknown')}")
            lines.append(f"- **Path**: `{comp.get('path', '')}`")
            
            if comp.get("exports"):
                lines.append(f"- **Exports**: {', '.join(comp['exports'][:5])}")
            
            if comp.get("props"):
                lines.append(f"- **Props**: {', '.join(comp['props'][:8])}")
            
            if comp.get("has_fetch") or comp.get("has_use_effect"):
                lines.append("- **Async**: Yes (uses fetch/useEffect)")
            
            if comp.get("has_skeleton"):
                lines.append("- **Has Loading State**: Yes")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def to_context(self, max_chars: int = 15000) -> str:
        """Build complete context string for zero-shot planning."""
        parts = []
        
        # File tree (compact)
        parts.append("## Project Files")
        parts.append("```")
        parts.append("\n".join(sorted(self.file_tree)[:100]))  # Limit to 100 files
        if len(self.file_tree) > 100:
            parts.append(f"... and {len(self.file_tree) - 100} more files")
        parts.append("```")
        
        # Schema
        schema_content = self.files.get('prisma/schema.prisma', '')
        if schema_content:
            parts.append("\n## Database Schema (prisma/schema.prisma)")
            parts.append("```prisma")
            parts.append(schema_content[:3000] if len(schema_content) > 3000 else schema_content)
            parts.append("```")
        
        # Types
        types_content = self.files.get('src/types/index.ts', '')
        if types_content:
            parts.append("\n## Types (src/types/index.ts)")
            parts.append("```typescript")
            parts.append(types_content[:2000] if len(types_content) > 2000 else types_content)
            parts.append("```")
        
        # Components
        if self.components:
            parts.append("\n## Component Imports (USE EXACT PATHS)")
            for name, path in sorted(self.components.items())[:20]:
                parts.append(f"- {name}: `import {{ {name} }} from '{path}'`")
        
        # API Routes
        if self.api_routes:
            parts.append("\n## API Routes")
            for route in sorted(self.api_routes)[:15]:
                route_url = route.replace("src/app", "").replace("/route.ts", "")
                parts.append(f"- {route_url}")
        
        # Existing tests (for reference)
        if self.test_files:
            parts.append("\n## Existing Test Files")
            for test in sorted(self.test_files)[:10]:
                parts.append(f"- {test}")
        
        result = "\n".join(parts)
        
        # Truncate if too long
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n... (truncated)"
        
        return result
    
    def preload_dependencies(self, steps: List[Dict], stories: List[Dict] = None) -> Dict[str, str]:
        """Pre-load dependency files for implementation steps (MetaGPT-style).
        
        Args:
            steps: Test plan steps
            stories: Story data for keyword extraction
            
        Returns:
            Dict mapping file_path -> content
        """
        dependencies = {}
        
        # 1. Always include common test setup files
        common_files = [
            "jest.config.ts",
            "jest.setup.ts",
            "prisma/schema.prisma",
            "src/lib/prisma.ts",
            "src/types/index.ts",
        ]
        for file_path in common_files:
            if file_path in self.files:
                dependencies[file_path] = self.files[file_path]
            else:
                full_path = os.path.join(self.workspace_path, file_path)
                if os.path.exists(full_path):
                    dependencies[file_path] = self._read_file(full_path)
        
        # 2. Collect dependencies from steps
        for step in steps:
            step_deps = step.get("dependencies", [])
            if isinstance(step_deps, list):
                for dep in step_deps:
                    if isinstance(dep, str) and dep not in dependencies:
                        full_path = os.path.join(self.workspace_path, dep)
                        if os.path.exists(full_path):
                            content = self._read_file(full_path)
                            if content:
                                dependencies[dep] = content[:5000]  # Limit size
        
        # 3. Add API route source code
        for route in self.api_routes[:10]:
            if route not in dependencies:
                full_path = os.path.join(self.workspace_path, route)
                if os.path.exists(full_path):
                    content = self._read_file(full_path)
                    if content:
                        dependencies[route] = content[:3000]
        
        # 4. Add component source code (for unit tests)
        for path in list(self.component_analysis.keys())[:10]:
            if path not in dependencies:
                full_path = os.path.join(self.workspace_path, path)
                if os.path.exists(full_path):
                    content = self._read_file(full_path)
                    if content:
                        dependencies[path] = content[:3000]
        
        logger.info(f"[FileRepository] Pre-loaded {len(dependencies)} dependency files")
        return dependencies
