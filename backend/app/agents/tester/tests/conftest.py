"""Pytest configuration and fixtures for Tester agent tests."""
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

# Load .env
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")


@pytest.fixture
def has_api_key():
    """Check if API key is available."""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


@pytest.fixture
def workspace(tmp_path):
    """Create a temporary workspace for tests."""
    workspace = tmp_path / "test_project"
    workspace.mkdir()
    (workspace / "src" / "app" / "api").mkdir(parents=True)
    (workspace / "src" / "components").mkdir(parents=True)
    (workspace / "src" / "__tests__" / "integration").mkdir(parents=True)
    (workspace / "e2e").mkdir()
    
    # Create package.json
    (workspace / "package.json").write_text("""{
  "name": "test-project",
  "version": "1.0.0",
  "scripts": {
    "test": "jest",
    "test:integration": "jest --testPathPattern=__tests__"
  }
}
""")
    
    # Create jest.config.ts
    (workspace / "jest.config.ts").write_text("""
import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
};

export default config;
""")
    
    return workspace


@pytest.fixture
def mock_source_file(workspace):
    """Create a mock source file for testing."""
    api_dir = workspace / "src" / "app" / "api" / "users"
    api_dir.mkdir(parents=True, exist_ok=True)
    
    route_file = api_dir / "route.ts"
    route_file.write_text("""
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';

export async function GET() {
    const users = await prisma.user.findMany();
    return NextResponse.json(users);
}

export async function POST(request: Request) {
    const { email, name } = await request.json();
    
    if (!email) {
        return NextResponse.json({ error: 'Email required' }, { status: 400 });
    }
    
    const user = await prisma.user.create({
        data: { email, name }
    });
    
    return NextResponse.json(user, { status: 201 });
}
""")
    
    return route_file


@pytest.fixture
def mock_state(workspace, mock_source_file):
    """Create a mock TesterState for tests."""
    return {
        "workspace_path": str(workspace),
        "project_id": str(uuid4()),
        "story_id": str(uuid4()),
        "tech_stack": "nextjs",
        "current_step": 0,
        "total_steps": 1,
        "review_stories": [{
            "id": str(uuid4()),
            "title": "User management API",
            "description": "As an admin, I want to manage users via API",
            "acceptance_criteria": ["List users", "Create user", "Validate email required"]
        }],
        "test_plan": [{
            "type": "integration",
            "file_path": "src/__tests__/integration/story-user-management.test.ts",
            "title": "Users API Tests",
            "scenarios": ["GET returns users", "POST creates user", "POST validates email"],
            "skills": ["integration-test"],
            "dependencies": ["src/app/api/users/route.ts"]
        }],
        "dependencies_content": {
            "src/app/api/users/route.ts": mock_source_file.read_text(),
            "jest.config.ts": (workspace / "jest.config.ts").read_text(),
        },
        "files_modified": [],
        "review_count": 0,
        "debug_count": 0,
        "run_status": None,
        "test_results": [],
    }
