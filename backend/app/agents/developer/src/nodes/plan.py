"""Analyze and Plan node"""
import os
import logging
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.developer.src.state import DeveloperState
from app.agents.developer.src.utils.llm_utils import get_langfuse_config as _cfg, flush_langfuse, track_node
from app.agents.core.llm_factory import get_llm
from app.agents.developer.src.schemas import SimplePlanOutput
from app.agents.developer.src.skills.registry import SkillRegistry
from app.agents.developer.src.skills import get_plan_prompts
from app.agents.developer.src.utils.story_logger import StoryLogger

logger = logging.getLogger(__name__)

BOILERPLATE_FILES = {"src/lib/prisma.ts", "src/lib/utils.ts", "src/auth.ts"}

class FileRepository:
    """Pre-computed workspace context for zero-shot planning."""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.files = {}
        self.file_tree = []
        self.components = {}
        self.api_routes = []
        self._scan()
    
    def _scan(self):
        if not self.workspace_path or not os.path.exists(self.workspace_path):
            return
        exclude_dirs = {'node_modules', '.next', '.git', '__pycache__', '.prisma'}
        # NOTE: os.walk can take 1-5s for large projects but _scan() is sync
        # This is acceptable since it's only called during plan phase
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f.endswith(('.ts', '.tsx', '.prisma', '.json', '.md')):
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.workspace_path).replace('\\', '/')
                    self.file_tree.append(rel_path)
                    if self._is_important(rel_path):
                        self.files[rel_path] = self._read_file(full_path)
                    if '/components/' in rel_path and rel_path.endswith('.tsx') and '/ui/' not in rel_path:
                        name = os.path.basename(rel_path).replace('.tsx', '')
                        self.components[name] = '@/' + rel_path.replace('.tsx', '')
                    if '/api/' in rel_path and rel_path.endswith('route.ts'):
                        self.api_routes.append(rel_path)
    
    def _is_important(self, path: str) -> bool:
        """Determine if a file should be fully loaded into context.

        """
        important_files = [
            'prisma/schema.prisma', 
            'src/types/index.ts', 
            'package.json', 
            'src/app/layout.tsx', 
            'src/lib/prisma.ts',
            'src/app/page.tsx',  
        ]
        
        return any(path.endswith(p) for p in important_files)
    
    def _read_file(self, full_path: str) -> str:
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""
    
    def to_context(self) -> str:
        parts = ["## Project Files (COMPLETE)", "```", "\n".join(sorted(self.file_tree)), "```"]
        
        # Schema
        schema = self.files.get('prisma/schema.prisma', '')
        parts.extend(["\n## prisma/schema.prisma", "```prisma", schema if len(schema) > 100 else "// Empty", "```"])
        
        # Types
        types = self.files.get('src/types/index.ts', '')
        if len(types) > 100:
            parts.extend(["\n## src/types/index.ts", "```typescript", types[:2500], "```"])
        
        # Homepage components - include full content for navigation-critical files
        for home_comp in ['src/app/page.tsx', 'src/components/home/Input.tsx', 'src/components/home/CategoryNavigation.tsx']:
            content = self.files.get(home_comp, '')
            if len(content) > 100:
                parts.extend([f"\n## {home_comp}", "```tsx", content[:2500], "```"])
        
        # Component imports
        if self.components:
            parts.append("\n## Component Imports")
            for name, path in sorted(self.components.items()):
                parts.append(f"- {name} → `import {{ {name} }} from '{path}'`")
        
        # API routes
        if self.api_routes:
            parts.append("\n## API Routes")
            parts.extend(f"- {r}" for r in sorted(self.api_routes))
        
        return "\n".join(parts)


def _preload_dependencies(workspace_path: str, steps: list) -> dict:
    deps_content = {}
    if not workspace_path or not os.path.exists(workspace_path):
        return deps_content
    all_deps = set()
    for step in steps:
        for dep in step.get("dependencies", []):
            if isinstance(dep, str) and dep:
                all_deps.add(dep)
            elif isinstance(dep, int):
                for s in steps:
                    if s.get("order") == dep and s.get("file_path"):
                        all_deps.add(s["file_path"])
                        break
    all_deps.update(["prisma/schema.prisma", "src/app/layout.tsx", "src/types/index.ts", "src/lib/prisma.ts"])
    for dep in all_deps:
        if not isinstance(dep, str):
            continue
        fp = os.path.join(workspace_path, dep)
        if os.path.exists(fp) and os.path.isfile(fp):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    deps_content[dep] = f.read()
            except:
                pass
    return deps_content


def _auto_assign_skills(file_path: str) -> list:
    if not file_path:
        return []
    fp = file_path.lower()
    if "schema.prisma" in fp:
        return ["database-model"]
    if "seed.ts" in fp:
        return ["database-seed"]
    if "/api/" in fp or "route.ts" in fp:
        return ["api-route"]
    if "/actions/" in fp:
        return ["server-action"]
    if "auth" in fp:
        return ["authentication"]
    if fp.endswith(".tsx"):
        if "/components/" in fp:
            return ["frontend-component", "frontend-design"]
        if "/app/" in fp:
            return ["frontend-component", "frontend-design"]
    return []


def _auto_detect_dependencies(file_path: str, all_steps: list = None) -> list:
    if not file_path:
        return []
    fp = file_path.lower()
    deps = []
    if "/api/" in fp or "/actions/" in fp or "seed.ts" in fp:
        deps.append("prisma/schema.prisma")
    if fp.endswith(".tsx"):
        deps.append("src/types/index.ts")
    if "/api/" in fp:
        deps.append("src/lib/prisma.ts")
    
    # Auto-detect Zustand store dependencies for components
    if fp.endswith(".tsx") and "/components/" in fp:
        # Payment-related components need payment store
        if "payment" in fp or "checkout" in fp:
            deps.append("src/lib/payment-store.ts")
        
        # Cart-related components need cart store
        if "cart" in fp or "checkout" in fp:
            deps.append("src/lib/cart-store.ts")
        
        # Order-related components might need both stores
        if "order" in fp:
            deps.append("src/lib/payment-store.ts")
    if all_steps and fp.endswith(".tsx"):
        filename = file_path.split("/")[-1].replace(".tsx", "").lower()
        if "section" in filename:
            domain = filename.replace("section", "").replace("s", "")[:6]
            for step in all_steps:
                other = step.get("file_path", "").lower()
                other_name = other.split("/")[-1].replace(".tsx", "")
                if other != fp and other.endswith(".tsx") and ("card" in other_name or "item" in other_name) and domain in other_name:
                    deps.append(step.get("file_path", ""))
        if "page.tsx" in fp:
            for step in all_steps:
                other = step.get("file_path", "").lower()
                if other != fp and other.endswith(".tsx") and ("section" in other or "card" in other):
                    deps.append(step.get("file_path", ""))
    return list(set(deps))


def _auto_fix_dependencies(steps: list) -> list:
    comp_paths = [s["file_path"] for s in steps if "/components/" in s.get("file_path", "")]
    api_routes = [s["file_path"] for s in steps if "/api/" in s.get("file_path", "")]
    for step in steps:
        fp = step.get("file_path", "")
        deps = step.get("dependencies", []) if isinstance(step.get("dependencies"), list) else []
        if "page.tsx" in fp:
            deps.extend(c for c in comp_paths if c not in deps)
        if "/components/" in fp:
            name = fp.split("/")[-1].replace(".tsx", "")
            if any(kw in name for kw in ["Section", "List", "Grid", "Carousel"]) and not any(kw in name for kw in ["Form", "Input", "Button", "Dialog", "Modal", "Card", "Item"]):
                if not any("/api/" in d for d in deps) and api_routes:
                    deps.append(api_routes[0])
        step["dependencies"] = list(set(deps))
    return steps


# =====================================================================
# Tools for Plan Node - Allow LLM to explore codebase
# =====================================================================

def create_planning_tools(workspace_path: str):
    """Create tools for LLM to explore workspace during planning."""
    from langchain_core.tools import tool
    
    @tool
    def grep_file_contents(pattern: str, path: str = "src", file_extension: str = "tsx") -> str:
        """Search for pattern in files to find existing code.
        
        Args:
            pattern: Text or regex pattern to search for (e.g., "BookCard", "Button")
            path: Directory to search in relative to workspace (default: src)
            file_extension: File type to search (tsx, ts, prisma, etc.)
            
        Returns:
            Matching files with line numbers and context, or "No matches found"
            
        Example:
            grep_file_contents("BookCard", "src/components", "tsx")
            → Shows all files using BookCard component
        """
        import subprocess
        
        full_path = os.path.join(workspace_path, path)
        if not os.path.exists(full_path):
            return f"Directory {path} not found"
        
        try:
            # Map common extensions to ripgrep types
            type_map = {
                "tsx": "tsx", "ts": "ts", "js": "js", "jsx": "jsx",
                "prisma": "txt", "json": "json", "md": "md"
            }
            rg_type = type_map.get(file_extension, "txt")
            
            result = subprocess.run(
                ["rg", "--type", rg_type, "-n", "-C", "2", pattern, "."],
                capture_output=True,
                text=True,
                cwd=full_path,
                timeout=10
            )
            
            if result.stdout:
                lines = result.stdout.split('\n')[:50]  # Limit to 50 lines
                return f"Found matches:\n" + '\n'.join(lines)
            return "No matches found"
        except subprocess.TimeoutExpired:
            return "Search timed out"
        except FileNotFoundError:
            return "Search tool (rg) not available - skipping search"
        except Exception as e:
            return f"Search error: {str(e)}"
    
    @tool
    def find_files_by_pattern(patterns: str, exclude_dirs: str = "node_modules,.next,.git") -> str:
        """Find files matching glob patterns.
        
        Args:
            patterns: Comma-separated glob patterns (e.g., "**/Card*.tsx,**/*Button*.tsx")
            exclude_dirs: Comma-separated dirs to exclude (default: node_modules,.next,.git)
            
        Returns:
            List of matching file paths
            
        Example:
            find_files_by_pattern("**/Card*.tsx,**/*List*.tsx")
            → Lists all Card and List components
        """
        import subprocess
        
        pattern_list = [p.strip() for p in patterns.split(',')]
        exclude_list = [d.strip() for d in exclude_dirs.split(',')]
        
        try:
            all_files = []
            exclude_args = [f"--glob=!{d}/**" for d in exclude_list]
            
            for pattern in pattern_list:
                result = subprocess.run(
                    ["rg", "--files", "--glob", pattern, *exclude_args],
                    capture_output=True,
                    text=True,
                    cwd=workspace_path,
                    timeout=10
                )
                if result.stdout:
                    all_files.extend(result.stdout.strip().split('\n'))
            
            # Deduplicate and limit
            unique_files = sorted(set(f for f in all_files if f))[:100]
            
            if unique_files:
                return '\n'.join(unique_files)
            return "No files found matching patterns"
        except FileNotFoundError:
            # Fallback to os.walk if rg not available
            try:
                import fnmatch
                matches = []
                exclude_set = set(exclude_list)
                
                for root, dirs, files in os.walk(workspace_path):
                    dirs[:] = [d for d in dirs if d not in exclude_set]
                    for pattern in pattern_list:
                        for filename in files:
                            if fnmatch.fnmatch(filename, pattern.split('/')[-1]):
                                rel_path = os.path.relpath(os.path.join(root, filename), workspace_path)
                                matches.append(rel_path)
                                if len(matches) >= 100:
                                    break
                
                return '\n'.join(sorted(set(matches))) if matches else "No files found"
            except Exception as e:
                return f"File search error: {e}"
        except Exception as e:
            return f"Search error: {str(e)}"
    
    @tool
    def list_directory(path: str = "src") -> str:
        """List contents of a directory to understand structure.
        
        Args:
            path: Directory path relative to workspace (default: src)
            
        Returns:
            Directory tree structure (max depth 3)
            
        Example:
            list_directory("src/components")
            → Shows all files in components directory
        """
        full_path = os.path.join(workspace_path, path)
        if not os.path.exists(full_path):
            return f"Directory {path} not found"
        
        try:
            items = []
            max_depth = 3
            max_items = 100
            
            for root, dirs, files in os.walk(full_path):
                level = root.replace(full_path, '').count(os.sep)
                if level >= max_depth:
                    dirs[:] = []
                    continue
                
                # Skip hidden and build dirs
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'node_modules', '.next', 'dist', 'build'}]
                
                indent = '  ' * level
                rel_root = os.path.relpath(root, full_path)
                if rel_root != '.':
                    items.append(f"{indent}{os.path.basename(root)}/")
                
                subindent = '  ' * (level + 1)
                for f in sorted(files):
                    if not f.startswith('.'):
                        items.append(f"{subindent}{f}")
                        if len(items) >= max_items:
                            break
                
                if len(items) >= max_items:
                    break
            
            return '\n'.join(items[:max_items])
        except Exception as e:
            return f"Error listing directory: {e}"
    
    @tool
    def read_specific_file(file_path: str, max_lines: int = 50) -> str:
        """Read contents of a specific file to understand its implementation.
        
        Args:
            file_path: Path relative to workspace (e.g., "src/components/ui/Button.tsx")
            max_lines: Maximum lines to return (default: 50)
            
        Returns:
            File contents (truncated if too long)
            
        Example:
            read_specific_file("src/components/ui/Button.tsx")
            → Shows Button component implementation
        """
        full_path = os.path.join(workspace_path, file_path)
        if not os.path.exists(full_path):
            return f"File {file_path} not found"
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if len(lines) > max_lines:
                content = ''.join(lines[:max_lines])
                return f"{content}\n... ({len(lines) - max_lines} more lines)"
            return ''.join(lines)
        except Exception as e:
            return f"Error reading file: {e}"
    
    return [grep_file_contents, find_files_by_pattern, list_directory, read_specific_file]


def _build_logic_analysis(steps: list, state: dict) -> str:
    """Build design overview from implementation steps.
    
    Creates a high-level summary of all files being implemented
    to give agent context about the overall design when working on individual files.
    """
    if not steps:
        return ""
    
    story_title = state.get("story_title", "")
    story_desc = state.get("story_description", "")
    
    # Group steps by category
    schema_steps = [s for s in steps if "schema.prisma" in s.get("file_path", "")]
    api_steps = [s for s in steps if "/api/" in s.get("file_path", "")]
    component_steps = [s for s in steps if "/components/" in s.get("file_path", "")]
    page_steps = [s for s in steps if "/page.tsx" in s.get("file_path", "")]
    other_steps = [s for s in steps if s not in schema_steps + api_steps + component_steps + page_steps]
    
    parts = [f"**Story**: {story_title}"]
    if story_desc:
        parts.append(f"**Description**: {story_desc}")
    
    parts.append(f"\n**Implementation Plan** ({len(steps)} files):")
    
    if schema_steps:
        parts.append("\n**Database Schema:**")
        for s in schema_steps:
            parts.append(f"- {s.get('file_path')}: {s.get('task', '')}")
    
    if api_steps:
        parts.append("\n**API Routes:**")
        for s in api_steps:
            parts.append(f"- {s.get('file_path')}: {s.get('task', '')}")
    
    if component_steps:
        parts.append("\n**Components:**")
        for s in component_steps:
            parts.append(f"- {s.get('file_path')}: {s.get('task', '')}")
    
    if page_steps:
        parts.append("\n**Pages:**")
        for s in page_steps:
            parts.append(f"- {s.get('file_path')}: {s.get('task', '')}")
    
    if other_steps:
        parts.append("\n**Other:**")
        for s in other_steps:
            parts.append(f"- {s.get('file_path')}: {s.get('task', '')}")
    
    return "\n".join(parts)


@track_node("plan")
async def plan(state: DeveloperState, config: dict = None, agent=None) -> DeveloperState:
    """Zero-shot planning with FileRepository."""
  
    
    config = config or {}  # Ensure config is not None
    story_logger = StoryLogger.from_state(state, agent).with_node("plan")
    
    await story_logger.info("Analyzing requirements...")
    workspace_path = state.get("workspace_path", "")
    tech_stack = state.get("tech_stack", "nextjs")
    
    try:
        await story_logger.info("Scanning project files...")
        repo = FileRepository(workspace_path)
        context = repo.to_context()
        
        skills_dir = Path(__file__).parent.parent / "skills"
        plan_prompts = get_plan_prompts(tech_stack, skills_dir)
        system_prompt = plan_prompts.get('zero_shot_system', plan_prompts.get('system_prompt', ''))
        
        req_text = chr(10).join(f"- {r}" for r in state.get("story_requirements", []))
        ac_text = chr(10).join(f"- {ac}" for ac in state.get("acceptance_criteria", []))
        
        input_text = f"""## Project Context
        {context}

## Story
**Title**: {state.get('story_title', '')}
**Description**: {state.get('story_description', '')}
**Requirements**: {req_text}
**Acceptance**: {ac_text}

Create implementation plan."""

        await story_logger.info("Generating implementation plan with exploration tools...")
        
        # Create tools for LLM to explore workspace
        tools = create_planning_tools(workspace_path)
        
        # Bind tools to LLM for exploration
        fast_llm = get_llm("router")
        llm_with_tools = fast_llm.bind_tools(tools)
        
        # Get langfuse callbacks from runtime config
        llm_config = _cfg(config, "plan_zero_shot")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"✓ LANGFUSE: Config for LLM call: callbacks={llm_config.get('callbacks', []) if llm_config else []}")
        
        # Enhanced prompt to guide tool usage
        tool_guidance = """
TOOL USAGE STRATEGY (You have up to 7 exploration rounds):

Available tools:
1. list_directory(path) - See what's in a folder (ALWAYS START HERE)
2. find_files_by_pattern(patterns) - Find files by name pattern (e.g., "**/Card*.tsx")
3. grep_file_contents(pattern, path, file_extension) - Search file contents
4. read_specific_file(file_path, max_lines) - Read full file

EFFICIENT EXPLORATION WORKFLOW:
Round 1-2 (Structure): Understand architecture
  → list_directory("src/app") - See pages structure
  → list_directory("src/components") - See component organization
  → find_files_by_pattern("**/api/**/route.ts") - Find all API routes

Round 3-4 (Search): Find relevant existing code
  → grep_file_contents("BookCard") - Find if component exists
  → grep_file_contents("prisma.book") - Check database usage patterns
  → find_files_by_pattern("**/*Card*.tsx") - Find similar components

Round 5-7 (Deep dive): Understand implementation details
  → read_specific_file("src/components/ui/BookCard.tsx") - See exact implementation
  → read_specific_file("src/app/api/books/route.ts") - Check API pattern
  → grep_file_contents("useRouter") - Find navigation patterns

BEST PRACTICES:
✓ Start broad (list directories) → then narrow (grep/find) → then deep (read files)
✓ Look for existing patterns to reuse (components, APIs, styles)
✓ Check for navigation/header before planning new pages
✓ Stop early if you have enough info (don't use all 7 rounds)
✗ Don't read entire files if grep can answer your question
✗ Don't search randomly - have a specific question in mind

If initial context is sufficient, you can skip tools entirely and plan directly.
"""
        
        enhanced_input = input_text + "\n\n" + tool_guidance
        
        # ReAct loop: Allow LLM to use tools before generating plan
        from langchain_core.messages import AIMessage, ToolMessage
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=enhanced_input)]
        
        max_iterations = 7  # Allow thorough exploration for complex stories (LLM usually stops at 2-3)
        for iteration in range(max_iterations):
            response = await llm_with_tools.ainvoke(messages, config=llm_config)
            messages.append(response)
            
            # Check if LLM wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                await story_logger.info(f"🔍 Exploring codebase (tool {iteration + 1}/{max_iterations})...")
                
                # Execute tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get('name', '')
                    tool_args = tool_call.get('args', {})
                    
                    # Find and execute tool
                    tool_result = "Tool not found"
                    for tool in tools:
                        if tool.name == tool_name:
                            try:
                                tool_result = tool.invoke(tool_args)
                            except Exception as e:
                                tool_result = f"Tool error: {str(e)}"
                            break
                    
                    # Add tool result to messages
                    messages.append(ToolMessage(
                        content=str(tool_result),
                        tool_call_id=tool_call.get('id', '')
                    ))
            else:
                # No more tools needed - break loop
                break
        
        # Now ask for final structured plan
        await story_logger.info("Creating structured implementation plan...")
        
        # Get final response content
        final_content = messages[-1].content if isinstance(messages[-1], AIMessage) else ""
        
        # Ask for structured output with all gathered context
        structured_llm = fast_llm.with_structured_output(SimplePlanOutput)
        
        plan_request = f"""Based on exploration, create implementation plan:

{final_content}

Story: {state.get('story_title', '')}
Requirements: {req_text}
Acceptance: {ac_text}

Output structured plan with steps."""
        
        result = await structured_llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=plan_request)], config=llm_config)
        flush_langfuse(config)
        
        # FIX #1: Removed post-LLM signal check - handled by _run_graph_with_signal_check()
        
        steps = result.model_dump().get("steps", [])
        
        if not steps:
            logger.warning("[plan] No steps generated, using fallback")
            steps = [{"order": 1, "task": f"Implement: {state.get('story_title', '')}", "file_path": "src/app/page.tsx", "action": "modify", "dependencies": []}]
        
        steps = [s for s in steps if s.get("file_path", "") not in BOILERPLATE_FILES]
        steps = _auto_fix_dependencies(steps)
        
        for i, step in enumerate(steps):
            step["order"] = i + 1
            step["description"] = step.get("task", "")
            step["skills"] = _auto_assign_skills(step.get("file_path", ""))
            llm_deps = step.get("dependencies", []) if isinstance(step.get("dependencies"), list) else []
            step["dependencies"] = list(set(llm_deps + _auto_detect_dependencies(step.get("file_path", ""), steps)))
        
        has_schema = any(s.get("file_path", "").endswith("schema.prisma") for s in steps)
        has_seed = any("seed.ts" in s.get("file_path", "").lower() for s in steps)
        if has_schema and not has_seed:
            seed_exists = workspace_path and (Path(workspace_path) / "prisma" / "seed.ts").exists()
            idx = next((i for i, s in enumerate(steps) if s.get("file_path", "").endswith("schema.prisma")), 0)
            steps.insert(idx + 1, {"order": idx + 2, "task": "Seed data", "description": "Seed database", "file_path": "prisma/seed.ts", "action": "modify" if seed_exists else "create", "skills": ["database-seed"], "dependencies": ["prisma/schema.prisma"]})
        
        for i, s in enumerate(steps):
            s["order"] = i + 1
        
        # Build logic analysis from steps
        logic_analysis = _build_logic_analysis(steps, state)
        
        SkillRegistry.load(tech_stack)
        deps_content = _preload_dependencies(workspace_path, steps)
        
        from app.agents.developer.src.nodes.parallel_utils import group_steps_by_layer, should_use_parallel
        layers = group_steps_by_layer(steps)
        can_parallel = should_use_parallel(steps)
        
        if steps:
            await story_logger.message(f"Kế hoạch: {len(steps)} files, {len(layers)} layers")
        
        return {**state, "implementation_plan": steps, "total_steps": len(steps), "dependencies_content": deps_content, "project_structure": context, "logic_analysis": logic_analysis, "current_step": 0, "parallel_layers": {float(k): [s.get("file_path") for s in v] for k, v in layers.items()}, "can_parallel": can_parallel, "action": "IMPLEMENT", "message": f"Plan: {len(steps)} steps ({len(layers)} layers)" + (" [PARALLEL]" if can_parallel else "")}
    except Exception as e:
        from langgraph.errors import GraphInterrupt
        if isinstance(e, GraphInterrupt):
            raise
        logger.error(f"[plan] Error: {e}", exc_info=True)
        return {**state, "error": str(e), "action": "RESPOND"}
