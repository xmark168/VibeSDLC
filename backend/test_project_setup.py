"""Test: Create project and verify workspace is copied correctly."""

import asyncio
import logging
import sys
from pathlib import Path
from uuid import UUID

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_create_project_with_boilerplate():
    """Test creating a project and verify boilerplate is copied."""
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import User, Project
    from app.schemas import ProjectCreate
    from app.services import ProjectService
    
    print("=" * 60)
    print("TEST: Create Project with Boilerplate")
    print("=" * 60)
    
    with Session(engine) as session:
        # Get first user as owner
        user = session.query(User).first()
        if not user:
            print("[ERROR] No user found in database!")
            return False
        
        print(f"\n[1/4] Using owner: {user.email}")
        
        # Create project
        project_in = ProjectCreate(
            name="Test Boilerplate Project",
            description="Testing boilerplate copy mechanism",
            tech_stack=["nextjs"],
        )
        
        print(f"[2/4] Creating project with tech_stack: nextjs")
        
        service = ProjectService(session)
        project = service.create(project_in, user.id)
        
        print(f"      Project ID: {project.id}")
        print(f"      Project Code: {project.code}")
        print(f"      Project Path: {project.project_path}")
        
        # Verify project path
        if not project.project_path:
            print("[ERROR] project_path is empty!")
            return False
        
        # Check if directory exists
        backend_root = Path(__file__).parent
        project_dir = backend_root / project.project_path
        
        print(f"\n[3/4] Checking workspace at: {project_dir}")
        
        if not project_dir.exists():
            print(f"[ERROR] Project directory does not exist: {project_dir}")
            return False
        
        print(f"      Directory exists: YES")
        
        # Check for key boilerplate files
        expected_files = [
            "package.json",
            "tsconfig.json",
            "next.config.ts",
            "src/app/page.tsx",
            "src/app/layout.tsx",
        ]
        
        print(f"\n[4/4] Verifying boilerplate files:")
        all_found = True
        for file in expected_files:
            file_path = project_dir / file
            exists = file_path.exists()
            status = "OK" if exists else "MISSING"
            print(f"      {file}: {status}")
            if not exists:
                all_found = False
        
        # Check git repo
        git_dir = project_dir / ".git"
        git_exists = git_dir.exists()
        print(f"\n      .git directory: {'OK' if git_exists else 'MISSING'}")
        
        # Summary
        print("\n" + "=" * 60)
        if all_found and git_exists:
            print("RESULT: SUCCESS - Boilerplate copied correctly!")
            print("=" * 60)
            print(f"\nProject ready at: {project_dir}")
            return True
        else:
            print("RESULT: FAILED - Some files missing!")
            print("=" * 60)
            return False


async def cleanup_test_projects():
    """Optional: Clean up test projects."""
    import shutil
    import stat
    import os
    from sqlmodel import Session
    from app.core.db import engine
    from app.models import Project
    
    def remove_readonly(func, path, excinfo):
        """Handle Windows readonly files (e.g., .git objects)."""
        os.chmod(path, stat.S_IWRITE)
        func(path)
    
    with Session(engine) as session:
        # Find test projects
        test_projects = session.query(Project).filter(
            Project.name.like("%Test Boilerplate%")
        ).all()
        
        for project in test_projects:
            if project.project_path:
                backend_root = Path(__file__).parent
                project_dir = backend_root / project.project_path
                if project_dir.exists():
                    shutil.rmtree(project_dir, onerror=remove_readonly)
                    print(f"Deleted: {project_dir}")
            
            session.delete(project)
        
        session.commit()
        print(f"Cleaned up {len(test_projects)} test projects")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        asyncio.run(cleanup_test_projects())
    else:
        success = asyncio.run(test_create_project_with_boilerplate())
        sys.exit(0 if success else 1)
