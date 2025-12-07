"""Test Code Quality after MetaGPT-style improvements.

Tests:
1. Code completeness (no TODOs, no placeholders)
2. Proper imports
3. Type safety
4. Null safety handling
5. 'use client' directive when needed
6. Following dependencies/types

Usage: cd backend && uv run python tests/test_implement_quality.py
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
from dataclasses import dataclass
from typing import List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("test_quality")

logging.getLogger("app.agents.developer_v2.src.nodes.implement").setLevel(logging.INFO)

for noisy in ["httpx", "opentelemetry", "langfuse", "httpcore", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


@dataclass
class QualityCheck:
    name: str
    passed: bool
    details: str


@dataclass  
class TestCase:
    name: str
    file_path: str
    action: str
    task: str
    dependencies: List[str]
    skills: List[str]
    expected_patterns: List[str]  # Must contain these
    forbidden_patterns: List[str]  # Must NOT contain these


class CodeQualityTester:
    """Test code quality of generated files."""
    
    def __init__(self):
        self.workspace = None
        self.results = []
        
    def setup_workspace(self):
        """Create temp workspace with sample files."""
        self.workspace = Path(tempfile.mkdtemp(prefix="test_quality_"))
        
        # Create directory structure
        (self.workspace / "src" / "components").mkdir(parents=True)
        (self.workspace / "src" / "lib").mkdir(parents=True)
        (self.workspace / "src" / "app" / "api" / "books").mkdir(parents=True)
        (self.workspace / "prisma").mkdir(parents=True)
        
        # Types file
        (self.workspace / "src" / "lib" / "types.ts").write_text("""
export interface Book {
  id: string;
  title: string;
  author: string;
  price: number;
  description?: string;
  tags?: string[];
}

export interface User {
  id: string;
  name: string;
  email: string;
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
}
""")
        
        # API client
        (self.workspace / "src" / "lib" / "api.ts").write_text("""
import axios from 'axios';
import { Book, ApiResponse } from './types';

const api = axios.create({ baseURL: '/api' });

export async function getBooks(): Promise<Book[]> {
  const response = await api.get<ApiResponse<Book[]>>('/books');
  return response.data.data;
}

export async function getBook(id: string): Promise<Book | null> {
  const response = await api.get<ApiResponse<Book>>(`/books/${id}`);
  return response.data.data;
}
""")
        
        # Prisma schema
        (self.workspace / "prisma" / "schema.prisma").write_text("""
model Book {
  id          String   @id @default(cuid())
  title       String
  author      String
  price       Float
  description String?
  tags        String[]
  createdAt   DateTime @default(now())
}
""")
        
        # Layout
        (self.workspace / "src" / "app" / "layout.tsx").write_text("""
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html><body>{children}</body></html>
  );
}
""")
        
        logger.info(f"Created workspace: {self.workspace}")
        return self.workspace
        
    def cleanup(self):
        if self.workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)
    
    def check_code_quality(self, content: str, test_case: TestCase) -> List[QualityCheck]:
        """Run quality checks on generated code."""
        checks = []
        
        # 1. No TODOs or placeholders
        todo_patterns = ["TODO", "FIXME", "// ...", "/* ... */", "// rest of", "implement later"]
        has_todo = any(p.lower() in content.lower() for p in todo_patterns)
        checks.append(QualityCheck(
            "No TODOs/placeholders",
            not has_todo,
            f"Found: {[p for p in todo_patterns if p.lower() in content.lower()]}" if has_todo else "Clean"
        ))
        
        # 2. Has exports
        has_export = "export " in content
        checks.append(QualityCheck(
            "Has exports",
            has_export,
            "Found export statement" if has_export else "Missing export"
        ))
        
        # 3. Expected patterns present
        missing_patterns = [p for p in test_case.expected_patterns if p not in content]
        checks.append(QualityCheck(
            "Expected patterns",
            len(missing_patterns) == 0,
            f"Missing: {missing_patterns}" if missing_patterns else f"All {len(test_case.expected_patterns)} found"
        ))
        
        # 4. Forbidden patterns absent
        found_forbidden = [p for p in test_case.forbidden_patterns if p in content]
        checks.append(QualityCheck(
            "No forbidden patterns",
            len(found_forbidden) == 0,
            f"Found: {found_forbidden}" if found_forbidden else "Clean"
        ))
        
        # 5. TypeScript specific checks
        if test_case.file_path.endswith(('.ts', '.tsx')):
            # Check for 'any' type (bad practice)
            has_any = ": any" in content or "as any" in content
            checks.append(QualityCheck(
                "No 'any' type",
                not has_any,
                "Uses 'any' type" if has_any else "Strong types"
            ))
            
            # Check for proper imports
            has_imports = "import " in content
            checks.append(QualityCheck(
                "Has imports",
                has_imports,
                "Has import statements" if has_imports else "Missing imports"
            ))
        
        # 6. React component checks
        if test_case.file_path.endswith('.tsx'):
            # Check for 'use client' if has hooks
            needs_client = any(h in content for h in ["useState", "useEffect", "onClick", "onChange"])
            has_client = "'use client'" in content or '"use client"' in content
            if needs_client:
                checks.append(QualityCheck(
                    "'use client' directive",
                    has_client,
                    "Has directive" if has_client else "Missing 'use client'"
                ))
            
            # Check for null safety patterns
            has_map = ".map(" in content
            has_safe_map = "?.map(" in content or "?? []" in content or "|| []" in content
            if has_map:
                checks.append(QualityCheck(
                    "Null-safe array operations",
                    has_safe_map or not has_map,
                    "Safe patterns used" if has_safe_map else "Potential null issue with .map()"
                ))
        
        # 7. Code length check (not too short)
        line_count = len(content.strip().split('\n'))
        checks.append(QualityCheck(
            "Sufficient code length",
            line_count >= 10,
            f"{line_count} lines" + (" (too short!)" if line_count < 10 else "")
        ))
        
        return checks
    
    async def run_test_case(self, test_case: TestCase) -> Tuple[bool, List[QualityCheck], float]:
        """Run a single test case and check code quality."""
        from app.agents.developer_v2.src.nodes.implement import implement
        from app.agents.developer_v2.src.skills import SkillRegistry
        
        # Load dependencies content
        dependencies_content = {}
        for dep in test_case.dependencies:
            dep_path = self.workspace / dep
            if dep_path.exists():
                dependencies_content[dep] = dep_path.read_text()
        
        state = {
            "workspace_path": str(self.workspace),
            "project_id": "test-quality",
            "task_id": "test-task",
            "tech_stack": "nextjs",
            "current_step": 0,
            "total_steps": 1,
            "implementation_plan": [{
                "file_path": test_case.file_path,
                "action": test_case.action,
                "task": test_case.task,
                "dependencies": test_case.dependencies,
                "skills": test_case.skills
            }],
            "dependencies_content": dependencies_content,
            "logic_analysis": [
                [test_case.file_path, test_case.task]
            ],
            "skill_registry": SkillRegistry.load("nextjs"),
            "files_modified": [],
        }
        
        start = datetime.now()
        result = await implement(state)
        elapsed = (datetime.now() - start).total_seconds()
        
        # Check if file was created
        created_file = self.workspace / test_case.file_path
        if not created_file.exists():
            return False, [QualityCheck("File created", False, "File not created")], elapsed
        
        content = created_file.read_text()
        checks = self.check_code_quality(content, test_case)
        
        # Add file creation check
        checks.insert(0, QualityCheck("File created", True, f"{len(content)} chars"))
        
        all_passed = all(c.passed for c in checks)
        return all_passed, checks, elapsed
    
    async def run_all_tests(self):
        """Run all quality test cases."""
        print("\n" + "="*70)
        print("CODE QUALITY TEST - MetaGPT-style Implementation")
        print("="*70)
        
        self.setup_workspace()
        
        test_cases = [
            TestCase(
                name="Simple Component",
                file_path="src/components/BookCard.tsx",
                action="create",
                task="Create a BookCard component that displays book title, author, and price. Use the Book interface from types.ts.",
                dependencies=["src/lib/types.ts"],
                skills=["frontend-component"],
                expected_patterns=["Book", "title", "author", "price", "export"],
                forbidden_patterns=["TODO", "FIXME", "// ..."]
            ),
            TestCase(
                name="Component with State",
                file_path="src/components/BookList.tsx",
                action="create",
                task="Create a BookList component that fetches and displays a list of books. Use useState for loading state and the getBooks function from api.ts.",
                dependencies=["src/lib/types.ts", "src/lib/api.ts"],
                skills=["frontend-component"],
                expected_patterns=["useState", "Book", "getBooks", "export", "'use client'"],
                forbidden_patterns=["TODO", ": any"]
            ),
            TestCase(
                name="API Route",
                file_path="src/app/api/books/route.ts",
                action="create",
                task="Create a GET API route that returns all books from the database using Prisma.",
                dependencies=["prisma/schema.prisma"],
                skills=["api-routes"],
                expected_patterns=["GET", "prisma", "NextResponse", "export"],
                forbidden_patterns=["TODO"]
            ),
        ]
        
        total_passed = 0
        total_time = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*70}")
            print(f"Test {i}/{len(test_cases)}: {test_case.name}")
            print(f"File: {test_case.file_path}")
            print("-"*70)
            
            try:
                passed, checks, elapsed = await self.run_test_case(test_case)
                total_time += elapsed
                
                for check in checks:
                    status = "[OK]" if check.passed else "[FAIL]"
                    print(f"  {status} {check.name}: {check.details}")
                
                # Show generated code
                created_file = self.workspace / test_case.file_path
                if created_file.exists():
                    content = created_file.read_text()
                    print(f"\n  --- GENERATED CODE ({len(content)} chars) ---")
                    # Show first 60 lines
                    lines = content.split('\n')[:60]
                    for line in lines:
                        print(f"  | {line}")
                    if len(content.split('\n')) > 60:
                        print(f"  | ... ({len(content.split(chr(10)))} total lines)")
                    print("  --- END CODE ---")
                
                if passed:
                    total_passed += 1
                    print(f"\n  Result: PASSED ({elapsed:.1f}s)")
                else:
                    print(f"\n  Result: FAILED ({elapsed:.1f}s)")
                    
            except Exception as e:
                logger.error(f"  [ERROR] {e}")
                print(f"\n  Result: ERROR - {e}")
        
        self.cleanup()
        
        # Summary
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        print(f"  Tests passed: {total_passed}/{len(test_cases)}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Avg time per test: {total_time/len(test_cases):.1f}s")
        print("="*70)
        
        return total_passed == len(test_cases)


async def main():
    tester = CodeQualityTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
