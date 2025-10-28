"""
Base Adapter Classes

Abstract base classes cho Filesystem và Git adapters.
"""

from abc import ABC, abstractmethod


class FilesystemAdapter(ABC):
    """
    Abstract base class cho filesystem operations.

    Implementations:
    - LocalFilesystemAdapter: Local filesystem operations
    - DaytonaFilesystemAdapter: Daytona sandbox filesystem operations
    """

    @abstractmethod
    def read_file(
        self,
        file_path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        working_directory: str = ".",
    ) -> str:
        """
        Read file content.

        Args:
            file_path: Path to file (relative to working_directory)
            start_line: Starting line number (1-based, inclusive)
            end_line: Ending line number (1-based, inclusive)
            working_directory: Base directory for relative paths

        Returns:
            File contents with line numbers (cat -n format)
        """
        pass

    @abstractmethod
    def write_file(
        self,
        file_path: str,
        content: str,
        working_directory: str = ".",
        create_dirs: bool = True,
    ) -> str:
        """
        Write file content.

        Args:
            file_path: Path to file (relative to working_directory)
            content: File content to write
            working_directory: Base directory for relative paths
            create_dirs: Create parent directories if needed

        Returns:
            Success message
        """
        pass

    @abstractmethod
    def list_files(
        self,
        directory: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        working_directory: str = ".",
    ) -> str:
        """
        List files in directory.

        Args:
            directory: Directory to list (relative to working_directory)
            pattern: Glob pattern (e.g., "*.py", "**/*.ts")
            recursive: Whether to search recursively
            working_directory: Base directory for relative paths

        Returns:
            List of files (one per line)
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str, working_directory: str = ".") -> str:
        """
        Delete file.

        Args:
            file_path: Path to file (relative to working_directory)
            working_directory: Base directory for relative paths

        Returns:
            Success message
        """
        pass

    @abstractmethod
    def create_directory(
        self, directory: str, working_directory: str = ".", mode: str = "755"
    ) -> str:
        """
        Create directory.

        Args:
            directory: Directory path (relative to working_directory)
            working_directory: Base directory for relative paths
            mode: Directory permissions (e.g., "755")

        Returns:
            Success message
        """
        pass

    @abstractmethod
    def edit_file(
        self,
        file_path: str,
        old_str: str,
        new_str: str,
        working_directory: str = ".",
        replace_all: bool = False,
    ) -> str:
        """
        Edit file by replacing old_str with new_str.

        Args:
            file_path: Path to file (relative to working_directory)
            old_str: String to search for (must match exactly)
            new_str: String to replace with
            working_directory: Base directory for relative paths
            replace_all: Whether to replace all occurrences (default: first only)

        Returns:
            Success message (JSON format)
        """
        pass

    @abstractmethod
    def grep_search(
        self,
        pattern: str,
        directory: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        context_lines: int = 0,
        working_directory: str = ".",
    ) -> str:
        """
        Search for pattern in files using grep/ripgrep.

        Args:
            pattern: Pattern to search for (regex supported)
            directory: Directory to search in (relative to working_directory)
            file_pattern: File glob pattern (e.g., "*.py", "*.ts")
            case_sensitive: Whether search is case-sensitive
            context_lines: Number of context lines before/after match
            working_directory: Base directory for relative paths

        Returns:
            Search results with file paths and line numbers
        """
        pass


class GitAdapter(ABC):
    """
    Abstract base class cho Git operations.

    Implementations:
    - LocalGitAdapter: Local git operations using GitPython
    - DaytonaGitAdapter: Daytona sandbox git operations
    """

    @abstractmethod
    def clone(self, url: str, path: str, working_directory: str = ".") -> dict:
        """
        Clone repository.

        Args:
            url: Git repository URL
            path: Destination path
            working_directory: Base directory for relative paths

        Returns:
            Dict with clone status
        """
        pass

    @abstractmethod
    def create_branch(
        self,
        branch_name: str,
        base_branch: str = "main",
        source_branch: str | None = None,
        working_directory: str = ".",
    ) -> dict:
        """
        Create and checkout new branch.

        Args:
            branch_name: Name of new branch
            base_branch: Base branch to branch from
            source_branch: Source branch for sequential branching (optional)
            working_directory: Git repository directory

        Returns:
            Dict with branch creation status
        """
        pass

    @abstractmethod
    def commit(
        self,
        message: str,
        files: list[str] | None = None,
        working_directory: str = ".",
    ) -> dict:
        """
        Commit changes.

        Args:
            message: Commit message
            files: List of specific files to commit (optional, commits all if None)
            working_directory: Git repository directory

        Returns:
            Dict with commit status
        """
        pass

    @abstractmethod
    def push(
        self,
        branch: str | None = None,
        remote: str = "origin",
        working_directory: str = ".",
    ) -> dict:
        """
        Push changes to remote.

        Args:
            branch: Branch to push (optional, pushes current branch if None)
            remote: Remote name (default: origin)
            working_directory: Git repository directory

        Returns:
            Dict with push status
        """
        pass

    @abstractmethod
    def status(self, working_directory: str = ".") -> dict:
        """
        Get git status.

        Args:
            working_directory: Git repository directory

        Returns:
            Dict with git status info
        """
        pass

    @abstractmethod
    def checkout(self, branch: str, working_directory: str = ".") -> dict:
        """
        Checkout branch.

        Args:
            branch: Branch name to checkout
            working_directory: Git repository directory

        Returns:
            Dict with checkout status
        """
        pass
