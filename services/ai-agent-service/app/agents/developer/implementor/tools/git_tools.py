# app/agents/developer/implementor/tools/git_tools.py
"""
Git workflow tools for branch management, commits, and pull requests
"""

import os
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
from langchain_core.tools import tool
from datetime import datetime


@tool
def create_feature_branch_tool(
    branch_name: str, 
    base_branch: str = "main",
    working_directory: str = "."
) -> str:
    """
    Create a new feature branch for implementation.
    
    This tool creates a new Git branch from the specified base branch
    and switches to it for development work.
    
    Args:
        branch_name: Name of the new feature branch (e.g., "feature/add-auth")
        base_branch: Base branch to create from (default: "main")
        working_directory: Git repository directory
        
    Returns:
        Status message about branch creation
        
    Example:
        create_feature_branch_tool("feature/add-user-auth", "main")
    """
    try:
        working_dir = Path(working_directory).resolve()
        
        if not working_dir.exists():
            return f"Error: Directory '{working_directory}' does not exist"
        
        # Check if it's a git repository
        git_dir = working_dir / ".git"
        if not git_dir.exists():
            return f"Error: '{working_directory}' is not a Git repository"
        
        # Sanitize branch name
        safe_branch_name = branch_name.replace(" ", "-").replace("_", "-").lower()
        if not safe_branch_name.startswith(("feature/", "fix/", "hotfix/", "chore/")):
            safe_branch_name = f"feature/{safe_branch_name}"
        
        # Change to working directory
        original_cwd = os.getcwd()
        os.chdir(working_dir)
        
        try:
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            # Check if branch already exists
            result = subprocess.run(
                ["git", "branch", "--list", safe_branch_name],
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                return f"Error: Branch '{safe_branch_name}' already exists"
            
            # Fetch latest changes
            subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True,
                text=True
            )
            
            # Switch to base branch and pull latest
            subprocess.run(
                ["git", "checkout", base_branch],
                capture_output=True,
                text=True,
                check=True
            )
            
            subprocess.run(
                ["git", "pull", "origin", base_branch],
                capture_output=True,
                text=True
            )
            
            # Create and switch to new branch
            subprocess.run(
                ["git", "checkout", "-b", safe_branch_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get commit info
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H %s"],
                capture_output=True,
                text=True,
                check=True
            )
            commit_info = result.stdout.strip()
            
            return json.dumps({
                "status": "success",
                "message": f"Created and switched to branch '{safe_branch_name}'",
                "branch_name": safe_branch_name,
                "base_branch": base_branch,
                "previous_branch": current_branch,
                "base_commit": commit_info,
                "timestamp": datetime.now().isoformat()
            }, indent=2)
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Error creating branch: {str(e)}"


@tool
def commit_changes_tool(
    message: str,
    files: List[str] = None,
    working_directory: str = "."
) -> str:
    """
    Commit changes to the current Git branch.
    
    This tool stages and commits changes with a descriptive message.
    If no files are specified, it commits all modified files.
    
    Args:
        message: Commit message describing the changes
        files: List of specific files to commit (optional, commits all if None)
        working_directory: Git repository directory
        
    Returns:
        Status message with commit information
        
    Example:
        commit_changes_tool("Add user authentication endpoints", ["auth.py", "routes.py"])
    """
    try:
        working_dir = Path(working_directory).resolve()
        
        if not working_dir.exists():
            return f"Error: Directory '{working_directory}' does not exist"
        
        # Check if it's a git repository
        git_dir = working_dir / ".git"
        if not git_dir.exists():
            return f"Error: '{working_directory}' is not a Git repository"
        
        # Change to working directory
        original_cwd = os.getcwd()
        os.chdir(working_dir)
        
        try:
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            # Check for changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                return json.dumps({
                    "status": "no_changes",
                    "message": "No changes to commit",
                    "branch": current_branch
                }, indent=2)
            
            # Stage files
            if files:
                # Stage specific files
                for file in files:
                    file_path = Path(file)
                    if file_path.exists():
                        subprocess.run(
                            ["git", "add", str(file_path)],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                    else:
                        return f"Error: File '{file}' does not exist"
            else:
                # Stage all changes
                subprocess.run(
                    ["git", "add", "."],
                    capture_output=True,
                    text=True,
                    check=True
                )
            
            # Check staged changes
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            staged_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            if not staged_files:
                return json.dumps({
                    "status": "no_staged_changes",
                    "message": "No staged changes to commit",
                    "branch": current_branch
                }, indent=2)
            
            # Commit changes
            subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get commit hash
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H"],
                capture_output=True,
                text=True,
                check=True
            )
            commit_hash = result.stdout.strip()
            
            # Get commit stats
            result = subprocess.run(
                ["git", "show", "--stat", "--format=", commit_hash],
                capture_output=True,
                text=True,
                check=True
            )
            commit_stats = result.stdout.strip()
            
            return json.dumps({
                "status": "success",
                "message": f"Successfully committed changes",
                "commit_hash": commit_hash,
                "commit_message": message,
                "branch": current_branch,
                "files_committed": staged_files,
                "stats": commit_stats,
                "timestamp": datetime.now().isoformat()
            }, indent=2)
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Error committing changes: {str(e)}"


@tool
def create_pull_request_tool(
    title: str,
    description: str,
    base_branch: str = "main",
    working_directory: str = ".",
    draft: bool = False
) -> str:
    """
    Create a pull request for code review.
    
    This tool pushes the current branch and creates a pull request.
    Note: This is a simplified implementation that pushes the branch.
    Actual PR creation would require GitHub/GitLab API integration.
    
    Args:
        title: Pull request title
        description: Pull request description
        base_branch: Target branch for the PR (default: "main")
        working_directory: Git repository directory
        draft: Whether to create as draft PR
        
    Returns:
        Status message with PR information
        
    Example:
        create_pull_request_tool(
            "Add user authentication",
            "Implements JWT-based authentication with login/logout endpoints"
        )
    """
    try:
        working_dir = Path(working_directory).resolve()
        
        if not working_dir.exists():
            return f"Error: Directory '{working_directory}' does not exist"
        
        # Check if it's a git repository
        git_dir = working_dir / ".git"
        if not git_dir.exists():
            return f"Error: '{working_directory}' is not a Git repository"
        
        # Change to working directory
        original_cwd = os.getcwd()
        os.chdir(working_dir)
        
        try:
            # Check current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            if current_branch == base_branch:
                return f"Error: Cannot create PR from base branch '{base_branch}'"
            
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                return "Error: You have uncommitted changes. Please commit them first."
            
            # Push current branch to origin
            try:
                subprocess.run(
                    ["git", "push", "origin", current_branch],
                    capture_output=True,
                    text=True,
                    check=True
                )
                push_status = "success"
            except subprocess.CalledProcessError:
                # Try to set upstream and push
                subprocess.run(
                    ["git", "push", "--set-upstream", "origin", current_branch],
                    capture_output=True,
                    text=True,
                    check=True
                )
                push_status = "success_with_upstream"
            
            # Get commit count
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{base_branch}..{current_branch}"],
                capture_output=True,
                text=True,
                check=True
            )
            commit_count = int(result.stdout.strip())
            
            # Get changed files
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_branch}..{current_branch}"],
                capture_output=True,
                text=True,
                check=True
            )
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Get remote URL for PR link generation
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else "unknown"
            
            pr_info = {
                "status": "branch_pushed",
                "message": f"Branch '{current_branch}' pushed successfully",
                "title": title,
                "description": description,
                "source_branch": current_branch,
                "target_branch": base_branch,
                "commit_count": commit_count,
                "changed_files": changed_files,
                "draft": draft,
                "remote_url": remote_url,
                "timestamp": datetime.now().isoformat(),
                "next_steps": [
                    "Visit your Git hosting platform (GitHub/GitLab) to create the PR",
                    f"Create PR from '{current_branch}' to '{base_branch}'",
                    "Use the provided title and description"
                ]
            }
            
            # Generate GitHub PR URL if it's a GitHub repo
            if "github.com" in remote_url:
                # Extract owner/repo from URL
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                if remote_url.startswith('git@github.com:'):
                    repo_path = remote_url.replace('git@github.com:', '')
                elif 'github.com/' in remote_url:
                    repo_path = remote_url.split('github.com/')[-1]
                else:
                    repo_path = None
                
                if repo_path:
                    pr_url = f"https://github.com/{repo_path}/compare/{base_branch}...{current_branch}"
                    pr_info["pr_url"] = pr_url
                    pr_info["next_steps"] = [f"Visit: {pr_url}"]
            
            return json.dumps(pr_info, indent=2)
            
        finally:
            os.chdir(original_cwd)
            
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Error creating pull request: {str(e)}"
