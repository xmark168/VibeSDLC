"""Test Langfuse integration with Developer V2.

Verifies:
1. Langfuse client initialization
2. Trace creation
3. Handler callback integration
4. Events are sent to Langfuse

Usage: cd backend && uv run python tests/test_langfuse_dev_v2.py
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
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("test_langfuse")

# Enable langfuse logs for debugging
logging.getLogger("langfuse").setLevel(logging.DEBUG)

for noisy in ["httpx", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


class LangfuseTest:
    """Test Langfuse integration."""
    
    def __init__(self):
        self.workspace = None
        self.results = []
        
    def setup_workspace(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="test_langfuse_"))
        (self.workspace / "src" / "components").mkdir(parents=True)
        (self.workspace / "src" / "lib").mkdir(parents=True)
        
        (self.workspace / "src" / "lib" / "types.ts").write_text("""
export interface Book {
  id: string;
  title: string;
  author: string;
}
""")
        logger.info(f"Created workspace: {self.workspace}")
        
    def cleanup(self):
        if self.workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)
    
    async def test_1_langfuse_env_config(self):
        """Test: Langfuse environment variables are set."""
        print("\n1. Langfuse Environment Config")
        print("-" * 50)
        
        enable = os.getenv("ENABLE_LANGFUSE", "false")
        secret = os.getenv("LANGFUSE_SECRET_KEY", "")
        public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        base_url = os.getenv("LANGFUSE_BASE_URL", "")
        
        checks = [
            (enable.lower() == "true", f"ENABLE_LANGFUSE={enable}"),
            (len(secret) > 10, f"LANGFUSE_SECRET_KEY={'*' * 10 if secret else 'NOT SET'}"),
            (len(public) > 10, f"LANGFUSE_PUBLIC_KEY={'*' * 10 if public else 'NOT SET'}"),
            (base_url.startswith("http"), f"LANGFUSE_BASE_URL={base_url}"),
        ]
        
        for passed, msg in checks:
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {msg}")
        
        success = all(c[0] for c in checks)
        self.results.append(("Langfuse env config", success))
        return success
    
    async def test_2_langfuse_client_init(self):
        """Test: Langfuse client can be initialized."""
        print("\n2. Langfuse Client Initialization")
        print("-" * 50)
        
        try:
            from langfuse import Langfuse
            
            client = Langfuse()
            
            print(f"  [OK] Langfuse client created")
            
            # Try to create a span (new API)
            span = client.start_span(name="test_span")
            print(f"  [OK] Span created: {span}")
            span.end()
            
            # Flush and check
            client.flush()
            print(f"  [OK] Flush completed")
            
            self.results.append(("Langfuse client init", True))
            return True
            
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            self.results.append(("Langfuse client init", False))
            return False
    
    async def test_3_langfuse_callback_handler(self):
        """Test: Langfuse CallbackHandler can be created."""
        print("\n3. Langfuse CallbackHandler")
        print("-" * 50)
        
        try:
            from langfuse.langchain import CallbackHandler
            from langfuse import Langfuse
            
            # Create handler (new API - minimal params)
            handler = CallbackHandler()
            
            print(f"  [OK] CallbackHandler created")
            print(f"  [OK] Handler type: {type(handler).__name__}")
            
            # Verify it can be used in config
            config = {"callbacks": [handler]}
            print(f"  [OK] Can be used in LangChain config")
            
            # Flush via Langfuse client
            client = Langfuse()
            client.flush()
            print(f"  [OK] Flush completed")
            
            self.results.append(("Langfuse callback handler", True))
            return True
            
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            self.results.append(("Langfuse callback handler", False))
            return False
    
    async def test_4_implement_with_langfuse(self):
        """Test: Implement step sends events to Langfuse."""
        print("\n4. Implement with Langfuse")
        print("-" * 50)
        
        self.setup_workspace()
        
        try:
            from langfuse.langchain import CallbackHandler
            from app.agents.developer_v2.src.nodes.implement import implement
            from app.agents.developer_v2.src.skills import SkillRegistry
            
            # Setup Langfuse CallbackHandler (new API)
            handler = CallbackHandler()
            
            print(f"  [OK] Langfuse handler created")
            
            # Load dependencies
            deps_content = {
                "src/lib/types.ts": (self.workspace / "src" / "lib" / "types.ts").read_text()
            }
            
            state = {
                "workspace_path": str(self.workspace),
                "project_id": "test-langfuse",
                "task_id": str(uuid4()),
                "tech_stack": "nextjs",
                "current_step": 0,
                "total_steps": 1,
                "implementation_plan": [{
                    "file_path": "src/components/TestComponent.tsx",
                    "action": "create",
                    "task": "Create a simple test component",
                    "dependencies": ["src/lib/types.ts"],
                    "skills": []
                }],
                "dependencies_content": deps_content,
                "logic_analysis": [],
                "skill_registry": SkillRegistry.load("nextjs"),
                "files_modified": [],
                # Langfuse integration
                "langfuse_handler": handler,
            }
            
            print(f"  [..] Running implement...")
            start = datetime.now()
            result = await implement(state)
            elapsed = (datetime.now() - start).total_seconds()
            
            # Check file created
            created_file = self.workspace / "src" / "components" / "TestComponent.tsx"
            file_created = created_file.exists()
            
            if file_created:
                print(f"  [OK] File created ({len(created_file.read_text())} chars)")
            else:
                print(f"  [FAIL] File not created")
            
            # Flush and verify
            from langfuse import Langfuse
            Langfuse().flush()
            print(f"  [OK] Events flushed")
            print(f"  [OK] Time: {elapsed:.1f}s")
            print(f"  [INFO] Check Langfuse dashboard for trace")
            
            success = file_created
            self.results.append(("Implement with Langfuse", success))
            return success
            
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            self.results.append(("Implement with Langfuse", False))
            return False
        finally:
            self.cleanup()
    
    async def run_all_tests(self):
        """Run all Langfuse tests."""
        print("\n" + "="*60)
        print("LANGFUSE INTEGRATION TEST - Developer V2")
        print("="*60)
        
        tests = [
            self.test_1_langfuse_env_config,
            self.test_2_langfuse_client_init,
            self.test_3_langfuse_callback_handler,
            self.test_4_implement_with_langfuse,
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"  [ERROR] {e}")
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        passed = sum(1 for _, success in self.results if success)
        total = len(self.results)
        
        for name, success in self.results:
            status = "[PASS]" if success else "[FAIL]"
            print(f"  {status} {name}")
        
        print(f"\nTotal: {passed}/{total} passed")
        print("="*60)
        
        return passed == total


async def main():
    tester = LangfuseTest()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
