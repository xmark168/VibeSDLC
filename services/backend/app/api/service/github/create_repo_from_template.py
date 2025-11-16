"""Service for creating repositories from GitHub templates."""

import logging
import requests
from typing import Optional, Dict, Any

from github import Github, GithubException

logger = logging.getLogger(__name__)


def create_repo_from_template(
    github_client: Github,
    template_repo_name: str,
    new_repo_name: str,
    description: Optional[str] = None,
    is_private: bool = False,
    target_owner: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Tạo repository mới từ template trên GitHub.

    Args:
        github_client: GitHub client instance (PyGithub)
        template_repo_name: Full name của template repository (e.g., 'owner/repo-name')
        new_repo_name: Tên của repository mới cần tạo
        description: Mô tả cho repository mới (optional)
        is_private: Có phải repository private hay không (default: False)
        target_owner: Owner (user/org) where to create the new repo. If None, uses template owner (for backward compatibility)

    Returns:
        Dict chứa thông tin repository đã tạo, hoặc None nếu có lỗi

    Raises:
        GithubException: Nếu có lỗi từ GitHub API
    """
    g = github_client

    try:
        logger.info(f"🔍 Đang tìm template repository: {template_repo_name}")
        template_repo = g.get_repo(template_repo_name)

        if not template_repo.is_template:
            logger.error(f"❌ Repository {template_repo_name} không phải là template")
            return None

        logger.info(f"✅ Tìm thấy template repository: {template_repo.full_name}")

        # Tạo repository mới từ template
        logger.info(f"🚀 Đang tạo repository mới: {new_repo_name}")

        # Use REST API directly since PyGithub may not have proper permissions
        # Get the access token from the Github client
        token = github_client._Github__requester._Requester__auth.token

        # Parse owner from template_repo_name
        template_owner_name = template_repo_name.split('/')[0]
        template_name = template_repo_name.split('/')[1]

        # Determine the actual owner for the new repository
        # If target_owner is provided, use it; otherwise fall back to template owner
        actual_owner = target_owner if target_owner else template_owner_name

        logger.info(f"📋 Will create repo in account: {actual_owner} (template from: {template_owner_name})")

        # Use GitHub REST API to create repo from template
        url = f"https://api.github.com/repos/{template_owner_name}/{template_name}/generate"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        payload = {
            "owner": actual_owner,  # Use the correct owner here
            "name": new_repo_name,
            "description": description or f"Created from template {template_repo_name}",
            "private": is_private,
            "include_all_branches": False
        }

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code not in [201, 200]:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('message', 'Unknown error')
            logger.error(f"❌ Failed to create repo: {response.status_code} - {error_msg}")
            return {
                "success": False,
                "message": f"GitHub API error: {error_msg}"
            }

        repo_data = response.json()
        logger.info(f"✅ Đã tạo repository thành công: {repo_data['full_name']}")

        # Return repository information
        return {
            "repository_id": repo_data['id'],
            "repository_name": repo_data['name'],
            "repository_full_name": repo_data['full_name'],
            "repository_url": repo_data['html_url'],
            "repository_description": repo_data.get('description', ''),
            "repository_private": repo_data['private'],
            "success": True,
            "message": f"Repository {repo_data['full_name']} created successfully from template {template_repo_name}",
        }

    except GithubException as e:
        error_msg = f"GitHub API error when creating repository: {e}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
        }
    except Exception as e:
        error_msg = f"Unexpected error when creating repository: {e}"
        logger.error(f"❌ {error_msg}")
        return {
            "success": False,
            "message": error_msg,
        }