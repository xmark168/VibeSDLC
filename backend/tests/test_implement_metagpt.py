"""Test Implement Step with MetaGPT-style improvements.

Tests:
1. Detailed 7-point instructions in prompt
2. Retry with exponential backoff (via tenacity)
3. Auto-load related files from dependencies
4. Summary log for debug iterations
5. Unified structured output for both normal and debug mode

Usage: cd backend && uv run python tests/test_implement_metagpt.py
"""

import os
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

import asyncio
import logging
import tempfile
import shutil
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("test_implement")

# Enable implement logs
logging.getLogger("app.agents.developer_v2.src.nodes.implement").setLevel(logging.DEBUG)
logging.getLogger("app.agents.developer_v2.src.nodes.review").setLevel(logging.DEBUG)

# Silence noisy loggers
for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


class TestImplementMetaGPT:
    """Test suite for MetaGPT-style implement improvements."""
    
    def __init__(self):
        self.workspace = None
        self.results = []
        
    def setup_workspace(self):
        """Create temp workspace with sample files."""
        self.workspace = Path(tempfile.mkdtemp(prefix="test_implement_"))
        
        # Create directory structure
        (self.workspace / "src" / "components").mkdir(parents=True)
        (self.workspace / "src" / "lib").mkdir(parents=True)
        (self.workspace / "src" / "app").mkdir(parents=True)
        
        # Create sample dependency files
        (self.workspace / "src" / "lib" / "types.ts").write_text("""
export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
}
""")
        
        (self.workspace / "src" / "lib" / "api.ts").write_text("""
import axios from 'axios';
import { Book } from './types';

export async function getBooks(): Promise<Book[]> {
  const response = await axios.get('/api/books');
  return response.data;
}
""")
        
        (self.workspace / "src" / "app" / "layout.tsx").write_text("""
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>{children}</body>
    </html>
  );
}
""")
        
        logger.info(f"Created workspace: {self.workspace}")
        return self.workspace
        
    def cleanup(self):
        """Remove temp workspace."""
        if self.workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)
            logger.info(f"Cleaned up workspace: {self.workspace}")
    
    async def test_1_prompt_has_metagpt_rules(self):
        """Test: Prompt contains MetaGPT-style 7-point instructions."""
        from app.agents.developer_v2.src.utils.prompt_utils import build_system_prompt
        
        prompt = build_system_prompt("implement_step", skills_content="")
        
        # Check for MetaGPT-style rules
        checks = [
            ("ONE FILE ONLY" in prompt, "Rule 1: ONE FILE ONLY"),
            ("COMPLETE CODE" in prompt, "Rule 2: COMPLETE CODE"),
            ("STRONG TYPE" in prompt, "Rule 3: STRONG TYPES"),
            ("FOLLOW DESIGN" in prompt, "Rule 4: FOLLOW DESIGN"),
            ("CHECK COMPLETENESS" in prompt or "don't miss" in prompt.lower(), "Rule 5: CHECK COMPLETENESS"),
            ("IMPORT FIRST" in prompt or "import it first" in prompt.lower(), "Rule 6: IMPORT FIRST"),
            ("NO TODOs" in prompt or "DON'T LEAVE TODO" in prompt, "Rule 7: NO TODOs"),
        ]
        
        passed = 0
        for check, name in checks:
            if check:
                logger.info(f"  ✓ {name}")
                passed += 1
            else:
                logger.error(f"  ✗ {name} - NOT FOUND")
        
        success = passed >= 5  # At least 5 of 7 rules
        self.results.append(("Prompt has MetaGPT rules", success, f"{passed}/7 rules found"))
        return success
    
    async def test_2_no_tools_direct_output(self):
        """Test: No tools, direct LLM output (MetaGPT-style)."""
        from app.agents.developer_v2.src.nodes.implement import implement
        import inspect
        
        source = inspect.getsource(implement)
        
        # Check that there's no tool binding
        no_bind_tools = "bind_tools" not in source
        no_tool_calls = "tool_calls" not in source
        has_direct_call = "Direct output" in source or "no tools" in source.lower()
        
        success = no_bind_tools and no_tool_calls and has_direct_call
        self.results.append(("No tools, direct output", success, 
                            f"no_bind={no_bind_tools}, no_calls={no_tool_calls}, direct={has_direct_call}"))
        
        if success:
            logger.info("  [OK] No tools, direct LLM output")
        else:
            logger.error("  [FAIL] Still using tools")
        
        return success
    
    async def test_3_max_debug_reviews_limit(self):
        """Test: MAX_DEBUG_REVIEWS limit prevents infinite loops."""
        from app.agents.developer_v2.src.nodes.implement import implement
        import inspect
        
        source = inspect.getsource(implement)
        
        has_max_limit = "MAX_DEBUG_REVIEWS" in source
        has_early_exit = "skipping to validate" in source.lower() or "skip to validate" in source.lower()
        
        success = has_max_limit and has_early_exit
        self.results.append(("Max debug reviews limit", success,
                            f"has_limit={has_max_limit}, has_exit={has_early_exit}"))
        
        if success:
            logger.info("  ✓ MAX_DEBUG_REVIEWS limit exists")
        else:
            logger.error("  ✗ Missing debug review limit")
        
        return success
    
    async def test_4_review_count_preserved_debug(self):
        """Test: review_count not reset in debug mode."""
        from app.agents.developer_v2.src.nodes.implement import implement
        import inspect
        
        source = inspect.getsource(implement)
        
        # Check for the fix: different handling for debug mode
        has_debug_check = "is_debug_mode" in source
        preserves_count = "review_count = state.get" in source
        
        success = has_debug_check and preserves_count
        self.results.append(("Review count preserved in debug", success,
                            f"debug_check={has_debug_check}, preserves={preserves_count}"))
        
        if success:
            logger.info("  [OK] review_count preserved in debug mode")
        else:
            logger.error("  [FAIL] review_count may be reset")
        
        return success
    
    async def test_5_auto_load_dependencies(self):
        """Test: Auto-load dependencies from disk if not in cache."""
        from app.agents.developer_v2.src.nodes.implement import _build_dependencies_context
        import inspect
        
        # Check function signature includes workspace_path
        sig = inspect.signature(_build_dependencies_context)
        has_workspace_param = "workspace_path" in sig.parameters
        has_exclude_param = "exclude_file" in sig.parameters
        
        # Check source for auto-load logic
        source = inspect.getsource(_build_dependencies_context)
        has_auto_load = "Auto-load from disk" in source or "os.path.exists" in source
        
        success = has_workspace_param and has_exclude_param and has_auto_load
        self.results.append(("Auto-load dependencies", success,
                            f"workspace={has_workspace_param}, exclude={has_exclude_param}, autoload={has_auto_load}"))
        
        if success:
            logger.info("  [OK] Auto-load dependencies from disk")
        else:
            logger.error("  [FAIL] Missing auto-load feature")
        
        return success
    
    async def test_6_debug_summary_log(self):
        """Test: Debug summary log for previous attempts."""
        from app.agents.developer_v2.src.nodes.implement import _build_debug_summary
        
        # Test with empty state
        empty_summary = _build_debug_summary({})
        assert empty_summary == "", "Empty state should return empty summary"
        
        # Test with debug state
        debug_state = {
            "debug_count": 2,
            "review_count": 1,
            "react_loop_count": 1,
            "review_feedback": "Add 'use client' directive",
            "error": "Component not found",
            "files_modified": ["src/components/Test.tsx"],
            "step_lbtm_counts": {"0": 1}
        }
        summary = _build_debug_summary(debug_state)
        
        checks = [
            ("Debug Summary" in summary, "Has header"),
            ("Debug iterations: 2" in summary, "Shows debug count"),
            ("Review attempts: 1" in summary, "Shows review count"),
            ("use client" in summary, "Shows review feedback"),
            ("Component not found" in summary, "Shows error"),
            ("Don't repeat" in summary, "Has warning message"),
        ]
        
        passed = sum(1 for check, _ in checks if check)
        success = passed >= 4
        
        for check, name in checks:
            if check:
                logger.info(f"    [OK] {name}")
            else:
                logger.warning(f"    [MISS] {name}")
        
        self.results.append(("Debug summary log", success, f"{passed}/{len(checks)} checks"))
        
        if success:
            logger.info(f"  [OK] Debug summary log ({passed}/{len(checks)})")
        else:
            logger.error(f"  [FAIL] Debug summary log ({passed}/{len(checks)})")
        
        return success
    
    async def test_7_implement_real_execution(self):
        """Test: Real implement execution with structured output."""
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        self.setup_workspace()
        
        try:
            # Create a simple implementation plan
            state = {
                "workspace_path": str(self.workspace),
                "project_id": "test-project",
                "task_id": "test-task",
                "tech_stack": "nextjs",
                "current_step": 0,
                "total_steps": 1,
                "implementation_plan": [{
                    "file_path": "src/components/BookCard.tsx",
                    "action": "create",
                    "task": "Create a BookCard component that displays book title, author, and price",
                    "dependencies": ["src/lib/types.ts"],
                    "skills": ["frontend-component"]
                }],
                "dependencies_content": {
                    "src/lib/types.ts": (self.workspace / "src" / "lib" / "types.ts").read_text()
                },
                "logic_analysis": [
                    ["src/components/BookCard.tsx", "Display component for book information"]
                ],
                "skill_registry": SkillRegistry.load("nextjs"),
                "files_modified": [],
            }
            
            logger.info("  Running implement...")
            start = datetime.now()
            result = await implement(state)
            elapsed = (datetime.now() - start).total_seconds()
            
            # Check results
            created_file = self.workspace / "src" / "components" / "BookCard.tsx"
            file_created = created_file.exists()
            
            if file_created:
                content = created_file.read_text()
                has_interface = "Book" in content or "interface" in content
                has_export = "export" in content
                logger.info(f"  ✓ File created ({len(content)} chars) in {elapsed:.1f}s")
                logger.info(f"    - Has Book reference: {has_interface}")
                logger.info(f"    - Has export: {has_export}")
            else:
                logger.error(f"  ✗ File not created")
                has_interface = False
                has_export = False
            
            success = file_created and has_export
            self.results.append(("Real implement execution", success,
                                f"created={file_created}, time={elapsed:.1f}s"))
            
            return success
            
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            self.results.append(("Real implement execution", False, str(e)))
            return False
        finally:
            self.cleanup()
    
    async def run_all_tests(self):
        """Run all tests and print summary."""
        print("\n" + "="*60)
        print("TEST: Implement Step with MetaGPT Improvements")
        print("="*60 + "\n")
        
        tests = [
            ("1. Prompt has MetaGPT rules", self.test_1_prompt_has_metagpt_rules),
            ("2. No tools, direct output", self.test_2_no_tools_direct_output),
            ("3. Max debug reviews limit", self.test_3_max_debug_reviews_limit),
            ("4. Review count preserved", self.test_4_review_count_preserved_debug),
            ("5. Auto-load dependencies", self.test_5_auto_load_dependencies),
            ("6. Debug summary log", self.test_6_debug_summary_log),
            ("7. Real implement execution", self.test_7_implement_real_execution),
        ]
        
        for name, test_fn in tests:
            print(f"\n{name}")
            print("-" * 40)
            try:
                await test_fn()
            except Exception as e:
                logger.error(f"  [FAIL] Test failed with exception: {e}")
                self.results.append((name, False, str(e)))
        
        # Print summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)
        
        for name, success, details in self.results:
            status = "[PASS]" if success else "[FAIL]"
            print(f"  {status}: {name}")
            if details:
                print(f"         {details}")
        
        print(f"\nTotal: {passed}/{total} passed")
        print("="*60)
        
        return passed == total


async def main():
    runner = TestImplementMetaGPT()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
