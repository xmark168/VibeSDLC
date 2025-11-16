"""
Install Dependencies Node

Cài đặt external dependencies từ implementation plan được tạo bởi Planner Agent.
"""

import os
import time

from langchain_core.messages import AIMessage

from ..state import DependencyInstallation, ImplementorState
from ..tool.shell_tools import shell_execute_tool


def _process_install_command(
    install_command: str, package_file: str, package: str
) -> str:
    """
    Process install command to ensure correct directory navigation.

    Args:
        install_command: Original install command from plan
        package_file: Package file path (e.g., "be/package.json", "fe/package.json")
        package: Package name for logging

    Returns:
        Processed install command with correct directory navigation
    """
    # If command already has cd, use it as-is
    if install_command.startswith("cd ") or " && " in install_command:
        return install_command

    # If no package_file or it's root level, use command as-is
    if not package_file or package_file in [
        "package.json",
        "requirements.txt",
        "pyproject.toml",
    ]:
        return install_command

    # Extract directory from package_file
    directory = os.path.dirname(package_file)
    if directory:
        # Add cd command to navigate to correct directory
        return f"cd {directory} && {install_command}"

    return install_command


def _extract_target_directory(final_command: str, package_file: str) -> str:
    """
    Extract target directory from final command or package_file.

    Args:
        final_command: Final processed install command
        package_file: Package file path

    Returns:
        Target directory name or empty string for root
    """
    # Try to extract from cd command
    if final_command.startswith("cd "):
        parts = final_command.split(" && ")
        if len(parts) > 0:
            cd_part = parts[0]
            directory = cd_part.replace("cd ", "").strip()
            return directory

    # Try to extract from package_file
    if package_file and "/" in package_file:
        directory = os.path.dirname(package_file)
        return directory

    return ""


def _check_and_install_base_dependencies(codebase_path: str) -> dict:
    """
    Check and install base dependencies for backend and frontend directories.

    Args:
        codebase_path: Path to the codebase root

    Returns:
        Dict with installation results for backend and frontend
    """
    print("\n🔍 Checking base dependencies (node_modules)...")

    results = {
        "backend": {"checked": False, "installed": False, "error": None},
        "frontend": {"checked": False, "installed": False, "error": None},
    }

    # Define directories to check
    directories = [
        {"name": "backend", "paths": ["be", "backend"], "type": "Backend"},
        {"name": "frontend", "paths": ["fe", "frontend"], "type": "Frontend"},
    ]

    for dir_config in directories:
        dir_name = dir_config["name"]
        dir_paths = dir_config["paths"]
        dir_type = dir_config["type"]

        # Find which directory exists
        existing_dir = None
        package_json_path = None

        for path in dir_paths:
            full_path = os.path.join(codebase_path, path)
            package_json = os.path.join(full_path, "package.json")

            if os.path.exists(full_path) and os.path.exists(package_json):
                existing_dir = path
                package_json_path = package_json
                break

        if not existing_dir:
            print(
                f"   ⚠️ No {dir_type.lower()} directory found (checked: {', '.join(dir_paths)})"
            )
            continue

        results[dir_name]["checked"] = True

        # Check if node_modules exists
        node_modules_path = os.path.join(codebase_path, existing_dir, "node_modules")

        if os.path.exists(node_modules_path):
            print(
                f"   ✅ {dir_type} node_modules already exists: {existing_dir}/node_modules"
            )
            results[dir_name]["installed"] = True
            continue

        # node_modules doesn't exist, need to install
        print(
            f"   📦 {dir_type} node_modules not found, installing base dependencies..."
        )
        print(f"   📁 Directory: {existing_dir}")
        print(f"   📄 Package.json: {package_json_path}")

        # Run npm install
        install_command = f"cd {existing_dir} && npm install"
        print(f"   🔧 Running: {install_command}")

        try:
            result = shell_execute_tool(
                command=install_command,
                working_directory=codebase_path,
                timeout=300,  # 5 minutes timeout
                allow_dangerous=False,
            )

            # Check if installation was successful
            success = "Error:" not in result and "error:" not in result.lower()

            if success:
                print(f"   ✅ {dir_type} base dependencies installed successfully")
                results[dir_name]["installed"] = True
            else:
                error_msg = result[:200] + "..." if len(result) > 200 else result
                print(f"   ❌ {dir_type} base dependencies installation failed")
                print(f"   Error: {error_msg}")
                results[dir_name]["error"] = error_msg

        except Exception as e:
            error_msg = str(e)
            print(
                f"   ❌ Exception during {dir_type.lower()} base dependencies installation"
            )
            print(f"   Error: {error_msg}")
            results[dir_name]["error"] = error_msg

    return results


def install_dependencies(state: ImplementorState) -> ImplementorState:
    """
    Install Dependencies node - Cài đặt external dependencies từ implementation plan.

    Tasks:
    1. Đọc external_dependencies từ implementation_plan (top-level hoặc infrastructure)
    2. Lọc ra các dependencies chưa được cài đặt (already_installed: false)
    3. Thực thi install_command cho từng dependency
    4. Log kết quả cài đặt (thành công/thất bại)
    5. Cập nhật state với thông tin dependencies đã cài đặt

    Args:
        state: ImplementorState với implementation_plan

    Returns:
        Updated ImplementorState với dependency installation results
    """
    print("\n" + "=" * 80)
    print("IMPLEMENTOR: INSTALL DEPENDENCIES NODE")
    print("=" * 80)

    try:
        # Update current phase
        state.current_phase = "install_dependencies"
        state.status = "installing_dependencies"

        # Step 1: Check and install base dependencies (node_modules) first
        print("📋 Step 1: Checking base dependencies...")
        base_deps_results = _check_and_install_base_dependencies(
            state.codebase_path or "."
        )

        # Log base dependencies results
        backend_result = base_deps_results.get("backend", {})
        frontend_result = base_deps_results.get("frontend", {})

        if backend_result.get("checked"):
            if backend_result.get("installed"):
                print("   ✅ Backend base dependencies ready")
            elif backend_result.get("error"):
                print(
                    f"   ⚠️ Backend base dependencies failed: {backend_result['error'][:100]}..."
                )

        if frontend_result.get("checked"):
            if frontend_result.get("installed"):
                print("   ✅ Frontend base dependencies ready")
            elif frontend_result.get("error"):
                print(
                    f"   ⚠️ Frontend base dependencies failed: {frontend_result['error'][:100]}..."
                )

        print("📋 Step 2: Processing external dependencies from plan...")

        # Get external dependencies from implementation plan
        implementation_plan = state.implementation_plan

        # Try to get external_dependencies from top-level first (new format)
        # Fall back to infrastructure.external_dependencies (old format)
        external_deps = implementation_plan.get("external_dependencies", [])
        if not external_deps:
            infrastructure = implementation_plan.get("infrastructure", {})
            external_deps = infrastructure.get("external_dependencies", [])

        print(f"📦 Found {len(external_deps)} external dependencies in plan")

        if not external_deps:
            print("✅ No external dependencies to install")
            state.dependencies_installed = True
            state.status = "dependencies_complete"

            # Add AI message
            ai_message = AIMessage(
                content="Install Dependencies - COMPLETED\n\nNo external dependencies found in implementation plan."
            )
            state.messages.append(ai_message)

            return state

        # Filter dependencies that need installation
        deps_to_install = [
            dep for dep in external_deps if not dep.get("already_installed", False)
        ]

        print(f"🔧 Need to install {len(deps_to_install)} dependencies")
        print(
            f"✅ Already installed: {len(external_deps) - len(deps_to_install)} dependencies"
        )

        # Install each dependency
        installation_results = []
        successful_installs = 0
        failed_installs = 0

        for i, dep in enumerate(deps_to_install, 1):
            package = dep.get("package", "unknown-package")
            version = dep.get("version", "")
            install_command = dep.get("install_command", "")
            package_file = dep.get("package_file", "")
            category = dep.get("category", "")
            purpose = dep.get("purpose", "")

            print(f"\n📦 Installing dependency {i}/{len(deps_to_install)}: {package}")
            print(f"   Version: {version}")
            print(f"   Category: {category}")
            print(f"   Package file: {package_file}")
            print(f"   Purpose: {purpose}")
            print(f"   Original command: {install_command}")

            if not install_command or install_command == "Already installed":
                print("   ⚠️ No install command provided, skipping")
                continue

            # Process install command to ensure correct directory navigation
            final_command = _process_install_command(
                install_command, package_file, package
            )
            print(f"   Final command: {final_command}")

            # Extract target directory for logging
            target_dir = _extract_target_directory(final_command, package_file)
            if target_dir:
                print(f"   📁 Installing in directory: {target_dir}")
            else:
                print("   📁 Installing in root directory")

            # Execute installation command
            start_time = time.time()

            try:
                result = shell_execute_tool(
                    command=final_command,
                    working_directory=state.codebase_path or ".",
                    timeout=300,  # 5 minutes timeout for package installation
                    allow_dangerous=False,
                )

                duration = time.time() - start_time

                # Check if installation was successful
                # Most package managers return 0 on success
                success = "Error:" not in result and "error:" not in result.lower()

                if success:
                    print(f"   ✅ Successfully installed {package} ({duration:.1f}s)")
                    successful_installs += 1
                else:
                    print(f"   ❌ Failed to install {package} ({duration:.1f}s)")
                    print(f"   Error: {result[:200]}...")
                    failed_installs += 1

                # Create installation result
                install_result = DependencyInstallation(
                    package=package,
                    version=version,
                    install_command=install_command,
                    exit_code=0 if success else 1,
                    stdout=result if success else "",
                    stderr=result if not success else "",
                    success=success,
                    already_installed=False,
                    error_message="" if success else result[:500],
                )

                installation_results.append(install_result)

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)

                print(
                    f"   ❌ Exception during installation of {package} ({duration:.1f}s)"
                )
                print(f"   Error: {error_msg}")
                failed_installs += 1

                # Create failed installation result
                install_result = DependencyInstallation(
                    package=package,
                    version=version,
                    install_command=install_command,
                    exit_code=1,
                    stdout="",
                    stderr=error_msg,
                    success=False,
                    already_installed=False,
                    error_message=error_msg[:500],
                )

                installation_results.append(install_result)

        # Add already installed dependencies to results
        for dep in external_deps:
            if dep.get("already_installed", False):
                install_result = DependencyInstallation(
                    package=dep.get("package", "unknown-package"),
                    version=dep.get("version", ""),
                    install_command="Already installed",
                    exit_code=0,
                    stdout="Package already installed",
                    stderr="",
                    success=True,
                    already_installed=True,
                    error_message="",
                )
                installation_results.append(install_result)

        # Update state with results
        state.dependency_installations = installation_results
        state.dependencies_installed = failed_installs == 0

        # Update status
        if failed_installs == 0:
            state.status = "dependencies_complete"
            print("\n✅ All dependencies installed successfully!")
        else:
            state.status = "dependencies_partial"
            print(f"\n⚠️ {failed_installs} dependencies failed to install")

        # Create summary
        summary = {
            "base_dependencies": {
                "backend": {
                    "checked": backend_result.get("checked", False),
                    "installed": backend_result.get("installed", False),
                    "error": backend_result.get("error"),
                },
                "frontend": {
                    "checked": frontend_result.get("checked", False),
                    "installed": frontend_result.get("installed", False),
                    "error": frontend_result.get("error"),
                },
            },
            "external_dependencies": {
                "total_dependencies": len(external_deps),
                "already_installed": len(external_deps) - len(deps_to_install),
                "attempted_installs": len(deps_to_install),
                "successful_installs": successful_installs,
                "failed_installs": failed_installs,
                "installation_results": [
                    {
                        "package": result.package,
                        "success": result.success,
                        "already_installed": result.already_installed,
                        "error": result.error_message if not result.success else None,
                    }
                    for result in installation_results
                ],
            },
        }

        # Store in tools_output
        state.tools_output["dependency_installation"] = summary

        # Add AI message
        base_deps_status = []
        if backend_result.get("checked"):
            status = "✅ Ready" if backend_result.get("installed") else "❌ Failed"
            base_deps_status.append(f"Backend: {status}")
        if frontend_result.get("checked"):
            status = "✅ Ready" if frontend_result.get("installed") else "❌ Failed"
            base_deps_status.append(f"Frontend: {status}")

        base_deps_summary = (
            ", ".join(base_deps_status) if base_deps_status else "No directories found"
        )

        ai_message = AIMessage(
            content=f"""Install Dependencies - COMPLETED

Base Dependencies:
- {base_deps_summary}

External Dependencies:
- Total dependencies: {len(external_deps)}
- Already installed: {len(external_deps) - len(deps_to_install)}
- Successfully installed: {successful_installs}
- Failed installations: {failed_installs}

Status: {"✅ All dependencies ready" if failed_installs == 0 else "⚠️ Some dependencies failed"}

Ready to proceed to Code Generation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Dependencies installation completed")
        print(
            f"DEPS: Total: {len(external_deps)}, Installed: {successful_installs}, Failed: {failed_installs}"
        )
        print(f"STATUS: {state.status}")
        print("NEXT: Next Phase: generate_code")
        print("=" * 80 + "\n")

        return state

    except Exception as e:
        print(f"ERROR: Error in dependencies installation: {e}")
        state.status = "error_dependencies"
        state.error_message = f"Dependencies installation failed: {str(e)}"

        # Add error message
        ai_message = AIMessage(
            content=f"Install Dependencies - FAILED\n\nError: {str(e)}"
        )
        state.messages.append(ai_message)

        return state
