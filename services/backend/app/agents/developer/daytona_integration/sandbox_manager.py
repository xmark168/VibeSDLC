"""
Daytona Sandbox Lifecycle Manager

Quản lý lifecycle của Daytona sandbox: create, reuse, cleanup.
"""

from typing import Optional

from daytona import CreateSandboxFromSnapshotParams, Daytona

from .config import DaytonaConfig


class SandboxManager:
    """
    Quản lý Daytona sandbox lifecycle.

    Responsibilities:
    - Create sandbox từ snapshot
    - Reuse sandbox cho multiple tasks trong cùng sprint
    - Cleanup sandbox khi kết thúc sprint
    - Track sandbox state
    """

    def __init__(self, config: DaytonaConfig):
        """
        Initialize SandboxManager.

        Args:
            config: DaytonaConfig instance
        """
        self.config = config
        self.daytona = Daytona(config.to_daytona_config())
        self.sandbox = None
        self.sandbox_id = None

    def create_sandbox(self) -> dict:
        """
        Create new Daytona sandbox từ snapshot.

        Returns:
            Dict với sandbox info:
                - sandbox_id: Sandbox ID
                - workspace_path: Workspace path trong sandbox
                - status: Creation status

        Raises:
            Exception: If sandbox creation fails
        """
        try:
            print(f"🚀 Creating Daytona sandbox...")
            print(f"   Language: {self.config.sandbox_language}")
            print(f"   Snapshot: {self.config.sandbox_snapshot}")

            # Create sandbox params
            params = CreateSandboxFromSnapshotParams(
                language=self.config.sandbox_language,
                snapshot=self.config.sandbox_snapshot,
            )

            # Create sandbox
            self.sandbox = self.daytona.create(params)
            self.sandbox_id = self.sandbox.id

            print(f"✅ Sandbox created: {self.sandbox_id}")

            return {
                "sandbox_id": self.sandbox_id,
                "workspace_path": self.config.workspace_path,
                "status": "created",
            }

        except Exception as e:
            print(f"❌ Failed to create sandbox: {e}")
            raise Exception(f"Sandbox creation failed: {e}")

    def get_sandbox(self):
        """
        Get current sandbox instance.

        Returns:
            Daytona Sandbox instance

        Raises:
            Exception: If no sandbox exists
        """
        if not self.sandbox:
            raise Exception("No sandbox exists. Call create_sandbox() first.")

        return self.sandbox

    def cleanup_sandbox(self) -> dict:
        """
        Cleanup and delete sandbox.

        Returns:
            Dict với cleanup status

        Raises:
            Exception: If cleanup fails
        """
        if not self.sandbox:
            print("⚠️ No sandbox to cleanup")
            return {"status": "no_sandbox"}

        try:
            print(f"🧹 Cleaning up sandbox: {self.sandbox_id}")

            # Delete sandbox
            self.sandbox.delete()

            print(f"✅ Sandbox deleted: {self.sandbox_id}")

            # Reset state
            self.sandbox = None
            self.sandbox_id = None

            return {"status": "deleted", "sandbox_id": self.sandbox_id}

        except Exception as e:
            print(f"❌ Failed to cleanup sandbox: {e}")
            raise Exception(f"Sandbox cleanup failed: {e}")

    def is_sandbox_active(self) -> bool:
        """
        Check if sandbox is active.

        Returns:
            True if sandbox exists and is active
        """
        return self.sandbox is not None

    def get_workspace_path(self, repo_name: str = "repo") -> str:
        """
        Get full workspace path for repository in sandbox.

        Args:
            repo_name: Repository name (default: "repo")

        Returns:
            Full path: /root/workspace/{repo_name}
        """
        return f"{self.config.workspace_path}/{repo_name}"


# Global sandbox manager instance (singleton pattern)
_sandbox_manager: Optional[SandboxManager] = None


def get_sandbox_manager(config: Optional[DaytonaConfig] = None) -> Optional[SandboxManager]:
    """
    Get global SandboxManager instance (singleton).

    Args:
        config: DaytonaConfig instance (required for first call)

    Returns:
        SandboxManager instance if Daytona is enabled, None otherwise
    """
    global _sandbox_manager

    # If Daytona is not enabled, return None
    if config is None:
        config = DaytonaConfig.from_env()

    if config is None:
        return None

    # Create singleton instance if not exists
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager(config)

    return _sandbox_manager


def reset_sandbox_manager():
    """Reset global sandbox manager (for testing)."""
    global _sandbox_manager
    _sandbox_manager = None

