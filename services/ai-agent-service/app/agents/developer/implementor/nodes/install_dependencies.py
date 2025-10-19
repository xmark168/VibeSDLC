"""
Install Dependencies Node

Cài đặt external dependencies từ implementation plan được tạo bởi Planner Agent.
"""

import time
from typing import Any

from langchain_core.messages import AIMessage

from ..state import DependencyInstallation, ImplementorState
from ..tool.shell_tools import shell_execute_tool


def install_dependencies(state: ImplementorState) -> ImplementorState:
    """
    Install Dependencies node - Cài đặt external dependencies từ implementation plan.

    Tasks:
    1. Đọc external_dependencies từ implementation_plan.infrastructure
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

        # Get external dependencies from implementation plan
        implementation_plan = state.implementation_plan
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
            dep for dep in external_deps 
            if not dep.get("already_installed", False)
        ]

        print(f"🔧 Need to install {len(deps_to_install)} dependencies")
        print(f"✅ Already installed: {len(external_deps) - len(deps_to_install)} dependencies")

        # Install each dependency
        installation_results = []
        successful_installs = 0
        failed_installs = 0

        for i, dep in enumerate(deps_to_install, 1):
            package = dep.get("package", "unknown-package")
            version = dep.get("version", "")
            install_command = dep.get("install_command", "")
            purpose = dep.get("purpose", "")

            print(f"\n📦 Installing dependency {i}/{len(deps_to_install)}: {package}")
            print(f"   Version: {version}")
            print(f"   Purpose: {purpose}")
            print(f"   Command: {install_command}")

            if not install_command or install_command == "Already installed":
                print("   ⚠️ No install command provided, skipping")
                continue

            # Execute installation command
            start_time = time.time()
            
            try:
                result = shell_execute_tool(
                    command=install_command,
                    working_directory=state.codebase_path or ".",
                    timeout=300,  # 5 minutes timeout for package installation
                    allow_dangerous=False
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
                    error_message="" if success else result[:500]
                )
                
                installation_results.append(install_result)

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                
                print(f"   ❌ Exception during installation of {package} ({duration:.1f}s)")
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
                    error_message=error_msg[:500]
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
                    error_message=""
                )
                installation_results.append(install_result)

        # Update state with results
        state.dependency_installations = installation_results
        state.dependencies_installed = failed_installs == 0

        # Update status
        if failed_installs == 0:
            state.status = "dependencies_complete"
            print(f"\n✅ All dependencies installed successfully!")
        else:
            state.status = "dependencies_partial"
            print(f"\n⚠️ {failed_installs} dependencies failed to install")

        # Create summary
        summary = {
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
                    "error": result.error_message if not result.success else None
                }
                for result in installation_results
            ]
        }

        # Store in tools_output
        state.tools_output["dependency_installation"] = summary

        # Add AI message
        ai_message = AIMessage(
            content=f"""Install Dependencies - COMPLETED

Summary:
- Total dependencies: {len(external_deps)}
- Already installed: {len(external_deps) - len(deps_to_install)}
- Successfully installed: {successful_installs}
- Failed installations: {failed_installs}

Status: {"✅ All dependencies ready" if failed_installs == 0 else "⚠️ Some dependencies failed"}

Ready to proceed to Code Generation."""
        )

        state.messages.append(ai_message)

        print("SUCCESS: Dependencies installation completed")
        print(f"DEPS: Total: {len(external_deps)}, Installed: {successful_installs}, Failed: {failed_installs}")
        print(f"STATUS: {state.status}")
        print(f"NEXT: Next Phase: generate_code")
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
