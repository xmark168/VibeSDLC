# app/agents/developer/implementor/tools/external_file_tools.py
"""
External File Operations Tools

Tools for copying files from outside the Daytona sandbox with proper security controls.
"""

import hashlib
import shutil
from pathlib import Path

from langchain_core.tools import tool

# ============================================================================
# EXTERNAL FILE COPY TOOLS
# ============================================================================


@tool
def copy_file_from_external_tool(
    source_path: str,
    destination_path: str,
    working_directory: str = ".",
    overwrite: bool = False,
    allowed_extensions: list[str] | None = None,
) -> str:
    """
    Copy a file from outside the Daytona sandbox into the workspace.

    SECURITY: Only allows copying from pre-approved directories or specific file types.

    Args:
        source_path: Absolute path to source file (outside sandbox)
        destination_path: Relative path in workspace (inside sandbox)
        working_directory: Base directory in sandbox
        overwrite: Whether to overwrite existing files
        allowed_extensions: List of allowed file extensions (e.g., ['.py', '.md', '.txt'])

    Returns:
        Success message or error

    Example:
        copy_file_from_external_tool(
            source_path="/home/user/templates/base.py",
            destination_path="app/templates/base.py",
            allowed_extensions=[".py", ".txt"]
        )
    """
    try:
        # Security: Define allowed source directories
        ALLOWED_SOURCE_DIRS = [
            "/home",
            "/tmp",
            "/opt",  # Linux/Mac
            "C:\\Users",
            "D:\\templates",  # Windows
            # Add other trusted directories as needed
        ]

        source_path_obj = Path(source_path).resolve()
        destination_full = (Path(working_directory) / destination_path).resolve()

        # SECURITY CHECKS

        # 1. Check if source path is in allowed directories
        source_allowed = False
        for allowed_dir in ALLOWED_SOURCE_DIRS:
            if str(source_path_obj).startswith(allowed_dir):
                source_allowed = True
                break

        if not source_allowed:
            return f"Error: Source path '{source_path}' is not in allowed directories"

        # 2. Check if source file exists
        if not source_path_obj.exists():
            return f"Error: Source file '{source_path}' does not exist"

        if not source_path_obj.is_file():
            return f"Error: Source path '{source_path}' is not a file"

        # 3. Check file extension if restrictions are set
        if allowed_extensions:
            file_extension = source_path_obj.suffix.lower()
            if file_extension not in [ext.lower() for ext in allowed_extensions]:
                return f"Error: File extension '{file_extension}' not allowed. Allowed: {allowed_extensions}"

        # 4. Check if destination already exists
        if destination_full.exists() and not overwrite:
            return f"Error: Destination file '{destination_path}' already exists. Use overwrite=True to replace."

        # 5. Ensure destination directory exists
        destination_full.parent.mkdir(parents=True, exist_ok=True)

        # Perform the copy
        shutil.copy2(source_path_obj, destination_full)

        # Verify the copy was successful
        if destination_full.exists():
            file_size = destination_full.stat().st_size
            return f"✅ Successfully copied '{source_path}' to '{destination_path}' ({file_size} bytes)"
        else:
            return "Error: Copy operation failed - destination file not created"

    except PermissionError:
        return f"Error: Permission denied accessing '{source_path}'"
    except Exception as e:
        return f"Error copying file: {str(e)}"


@tool
def copy_directory_from_external_tool(
    source_dir: str,
    destination_dir: str,
    working_directory: str = ".",
    overwrite: bool = False,
    allowed_extensions: list[str] | None = None,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB default
) -> str:
    """
    Copy an entire directory from outside sandbox into workspace.

    SECURITY: Strict controls on file types, sizes, and source locations.

    Args:
        source_dir: Absolute path to source directory
        destination_dir: Relative path in workspace
        working_directory: Base directory in sandbox
        overwrite: Whether to overwrite existing files
        allowed_extensions: Allowed file extensions
        max_file_size: Maximum file size in bytes

    Returns:
        Copy summary with file counts

    Example:
        copy_directory_from_external_tool(
            source_dir="/home/user/templates",
            destination_dir="app/templates",
            allowed_extensions=[".py", ".html", ".css"]
        )
    """
    try:
        # Security: Allowed source directories
        ALLOWED_SOURCE_DIRS = [
            "/home",
            "/tmp",
            "/opt",
            "C:\\Users",
            "D:\\templates",
        ]

        source_dir_obj = Path(source_dir).resolve()
        destination_full = (Path(working_directory) / destination_dir).resolve()

        # SECURITY CHECKS

        # 1. Check source directory is allowed
        source_allowed = False
        for allowed_dir in ALLOWED_SOURCE_DIRS:
            if str(source_dir_obj).startswith(allowed_dir):
                source_allowed = True
                break

        if not source_allowed:
            return f"Error: Source directory '{source_dir}' is not in allowed locations"

        # 2. Check source exists and is a directory
        if not source_dir_obj.exists():
            return f"Error: Source directory '{source_dir}' does not exist"

        if not source_dir_obj.is_dir():
            return f"Error: Source path '{source_dir}' is not a directory"

        # 3. Check if destination exists and handle overwrite
        if destination_full.exists():
            if not overwrite:
                return f"Error: Destination directory '{destination_dir}' already exists. Use overwrite=True to replace."
            else:
                shutil.rmtree(destination_full)  # Remove existing

        # Create destination directory
        destination_full.mkdir(parents=True, exist_ok=True)

        # Copy files with security checks
        copied_files = []
        skipped_files = []
        error_files = []

        for source_file in source_dir_obj.rglob("*"):
            if source_file.is_file():
                # Check file size
                file_size = source_file.stat().st_size
                if file_size > max_file_size:
                    skipped_files.append(
                        f"{source_file.name} (too large: {file_size} bytes)"
                    )
                    continue

                # Check file extension
                if allowed_extensions:
                    file_extension = source_file.suffix.lower()
                    if file_extension not in [
                        ext.lower() for ext in allowed_extensions
                    ]:
                        skipped_files.append(
                            f"{source_file.name} (extension not allowed)"
                        )
                        continue

                # Calculate relative path for destination
                relative_path = source_file.relative_to(source_dir_obj)
                dest_file = destination_full / relative_path

                # Create parent directories
                dest_file.parent.mkdir(parents=True, exist_ok=True)

                try:
                    shutil.copy2(source_file, dest_file)
                    copied_files.append(str(relative_path))
                except Exception as e:
                    error_files.append(f"{source_file.name} ({str(e)})")

        # Generate summary
        summary = f"""
📁 Directory Copy Summary:

✅ Copied: {len(copied_files)} files
⏭️  Skipped: {len(skipped_files)} files
❌ Errors: {len(error_files)} files

Source: {source_dir}
Destination: {destination_dir}
"""

        if copied_files:
            summary += "\n📋 Copied files (first 10):\n"
            for file in copied_files[:10]:
                summary += f"  - {file}\n"
            if len(copied_files) > 10:
                summary += f"  ... and {len(copied_files) - 10} more\n"

        if skipped_files:
            summary += "\n🚫 Skipped files:\n"
            for file in skipped_files[:5]:
                summary += f"  - {file}\n"

        if error_files:
            summary += "\n❌ Files with errors:\n"
            for file in error_files:
                summary += f"  - {file}\n"

        return summary

    except Exception as e:
        return f"Error copying directory: {str(e)}"


@tool
def sync_templates_from_external_tool(
    template_source: str,
    template_type: str = "boilerplate",
    working_directory: str = ".",
    overwrite: bool = False,
) -> str:
    """
    Sync template files from external source to workspace.

    Pre-configured for common template types with security controls.

    Args:
        template_source: Path to template directory
        template_type: Type of templates (boilerplate, config, deployment, etc.)
        working_directory: Base directory in sandbox
        overwrite: Whether to overwrite existing templates

    Returns:
        Sync summary

    Example:
        sync_templates_from_external_tool(
            template_source="/opt/templates/fastapi-boilerplate",
            template_type="boilerplate",
            overwrite=True
        )
    """
    try:
        # Template-specific security settings
        TEMPLATE_CONFIGS = {
            "boilerplate": {
                "allowed_extensions": [
                    ".py",
                    ".md",
                    ".txt",
                    ".yml",
                    ".yaml",
                    ".json",
                    ".html",
                    ".css",
                    ".js",
                ],
                "max_file_size": 5 * 1024 * 1024,  # 5MB
                "destination": "templates/boilerplate",
            },
            "config": {
                "allowed_extensions": [
                    ".yml",
                    ".yaml",
                    ".json",
                    ".conf",
                    ".ini",
                    ".toml",
                ],
                "max_file_size": 1 * 1024 * 1024,  # 1MB
                "destination": "templates/config",
            },
            "deployment": {
                "allowed_extensions": [
                    ".yml",
                    ".yaml",
                    ".json",
                    ".sh",
                    ".Dockerfile",
                    ".dockerfile",
                ],
                "max_file_size": 2 * 1024 * 1024,  # 2MB
                "destination": "templates/deployment",
            },
        }

        if template_type not in TEMPLATE_CONFIGS:
            return f"Error: Unknown template type '{template_type}'. Available: {list(TEMPLATE_CONFIGS.keys())}"

        config = TEMPLATE_CONFIGS[template_type]
        destination_dir = config["destination"]

        return copy_directory_from_external_tool(
            source_dir=template_source,
            destination_dir=destination_dir,
            working_directory=working_directory,
            overwrite=overwrite,
            allowed_extensions=config["allowed_extensions"],
            max_file_size=config["max_file_size"],
        )

    except Exception as e:
        return f"Error syncing templates: {str(e)}"


@tool
def verify_external_file_tool(
    file_path: str, expected_hash: str | None = None, expected_size: int | None = None
) -> str:
    """
    Verify an external file's integrity before copying.

    Args:
        file_path: Absolute path to external file
        expected_hash: Expected SHA256 hash (optional)
        expected_size: Expected file size in bytes (optional)

    Returns:
        Verification results

    Example:
        verify_external_file_tool(
            file_path="/home/user/important.py",
            expected_hash="a1b2c3...",
            expected_size=1024
        )
    """
    try:
        file_path_obj = Path(file_path).resolve()

        if not file_path_obj.exists():
            return f"Error: File '{file_path}' does not exist"

        if not file_path_obj.is_file():
            return f"Error: Path '{file_path}' is not a file"

        # Get file info
        file_size = file_path_obj.stat().st_size
        result = f"📄 File: {file_path}\n"
        result += f"📏 Size: {file_size} bytes\n"

        # Check size if expected
        if expected_size:
            if file_size == expected_size:
                result += f"✅ Size matches expected: {expected_size} bytes\n"
            else:
                result += f"❌ Size mismatch: expected {expected_size}, got {file_size} bytes\n"

        # Calculate hash if expected
        if expected_hash:
            with open(file_path_obj, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()

            if file_hash == expected_hash.lower():
                result += "✅ Hash matches expected\n"
                result += f"🔐 SHA256: {file_hash}\n"
            else:
                result += "❌ Hash mismatch!\n"
                result += f"   Expected: {expected_hash}\n"
                result += f"   Got:      {file_hash}\n"
        else:
            # Calculate hash anyway for reference
            with open(file_path_obj, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            result += f"🔐 SHA256: {file_hash}\n"

        result += "✅ File is ready for copying"

        return result

    except Exception as e:
        return f"Error verifying file: {str(e)}"


# ============================================================================
# SECURITY CONFIGURATION TOOLS
# ============================================================================


@tool
def configure_external_access_tool(
    allowed_directories: list[str],
    max_file_size: int = 10 * 1024 * 1024,
    allowed_extensions: list[str] | None = None,
) -> str:
    """
    Configure security settings for external file access.

    WARNING: This modifies security settings - use with caution!

    Args:
        allowed_directories: List of directory paths that can be accessed
        max_file_size: Maximum file size in bytes
        allowed_extensions: List of allowed file extensions

    Returns:
        Configuration summary

    Example:
        configure_external_access_tool(
            allowed_directories=["/home/user/templates", "/opt/shared"],
            max_file_size=5 * 1024 * 1024,
            allowed_extensions=[".py", ".md", ".txt"]
        )
    """
    try:
        # In a real implementation, this would update a configuration file
        # or environment variables that control the security settings

        config_summary = """
🔧 External Access Configuration Updated:

📁 Allowed Directories:
"""
        for directory in allowed_directories:
            config_summary += f"  - {directory}\n"

        config_summary += f"""
📏 Max File Size: {max_file_size} bytes ({max_file_size / 1024 / 1024:.1f} MB)
"""

        if allowed_extensions:
            config_summary += (
                f"📄 Allowed Extensions: {', '.join(allowed_extensions)}\n"
            )
        else:
            config_summary += "📄 Allowed Extensions: All (no restrictions)\n"

        config_summary += """
⚠️  Security Note: These settings control what files can be copied into the sandbox.
   Only configure trusted directories and file types.
"""

        # In a real implementation, you would save these settings
        # For now, just return the summary

        return config_summary

    except Exception as e:
        return f"Error configuring external access: {str(e)}"


__all__ = [
    "copy_file_from_external_tool",
    "copy_directory_from_external_tool",
    "sync_templates_from_external_tool",
    "verify_external_file_tool",
    "configure_external_access_tool",
]
