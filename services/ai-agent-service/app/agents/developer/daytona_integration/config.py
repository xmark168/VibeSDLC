"""
Daytona Configuration Module

Load Daytona configuration từ environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DaytonaConfig:
    """Daytona configuration từ environment variables."""

    api_key: str
    api_url: str
    organization_id: str
    target: str = "us"
    enabled: bool = True
    sandbox_language: str = "node"  # Default: Node.js sandbox
    sandbox_snapshot: str = "node"  # Default snapshot
    workspace_path: str = "/root/workspace"  # Default workspace path in sandbox

    @classmethod
    def from_env(cls) -> Optional["DaytonaConfig"]:
        """
        Load Daytona config từ environment variables.

        Environment variables:
            DAYTONA_ENABLED: Enable/disable Daytona mode (default: false)
            DAYTONA_API_KEY: Daytona API key (required if enabled)
            DAYTONA_API_URL: Daytona API URL (default: http://localhost:3000/api)
            DAYTONA_ORGANIZATION_ID: Organization ID (required if enabled)
            DAYTONA_TARGET: Target region (default: us)
            DAYTONA_SANDBOX_LANGUAGE: Sandbox language (default: node)
            DAYTONA_SANDBOX_SNAPSHOT: Sandbox snapshot (default: node)
            DAYTONA_WORKSPACE_PATH: Workspace path in sandbox (default: /root/workspace)

        Returns:
            DaytonaConfig instance if enabled, None otherwise
        """
        # Check if Daytona is enabled
        enabled = os.getenv("DAYTONA_ENABLED", "false").lower() == "true"

        if not enabled:
            return None

        # Load required config
        api_key = os.getenv("DAYTONA_API_KEY")
        organization_id = os.getenv("DAYTONA_ORGANIZATION_ID")

        if not api_key or not organization_id:
            raise ValueError(
                "DAYTONA_API_KEY and DAYTONA_ORGANIZATION_ID are required when DAYTONA_ENABLED=true"
            )

        # Load optional config with defaults
        api_url = os.getenv("DAYTONA_API_URL", "http://localhost:3000/api")
        target = os.getenv("DAYTONA_TARGET", "us")
        sandbox_language = os.getenv("DAYTONA_SANDBOX_LANGUAGE", "node")
        sandbox_snapshot = os.getenv("DAYTONA_SANDBOX_SNAPSHOT", "node")
        workspace_path = os.getenv("DAYTONA_WORKSPACE_PATH", "/root/workspace")

        return cls(
            api_key=api_key,
            api_url=api_url,
            organization_id=organization_id,
            target=target,
            enabled=enabled,
            sandbox_language=sandbox_language,
            sandbox_snapshot=sandbox_snapshot,
            workspace_path=workspace_path,
        )

    def to_daytona_config(self):
        """
        Convert to Daytona SDK DaytonaConfig object.

        Returns:
            DaytonaConfig instance for Daytona SDK
        """
        from daytona import DaytonaConfig as SDKConfig

        return SDKConfig(
            api_key=self.api_key,
            api_url=self.api_url,
            organization_id=self.organization_id,
            target=self.target,
        )

