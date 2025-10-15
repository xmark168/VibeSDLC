#!/usr/bin/env python3
"""
Setup script for AI Agent Service project
Handles virtual environment creation and dependency installation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run a command and return the result"""
    print(f"🔧 Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True if isinstance(cmd, str) else False,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if check:
            raise
        return e

def create_virtual_environment():
    """Create virtual environment if it doesn't exist"""
    venv_path = Path("venv")
    
    if venv_path.exists():
        print("✅ Virtual environment already exists")
        return True
    
    print("🏗️ Creating virtual environment...")
    try:
        run_command([sys.executable, "-m", "venv", "venv"])
        print("✅ Virtual environment created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create virtual environment: {e}")
        return False

def get_activation_command():
    """Get the command to activate virtual environment"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\activate"
    else:
        return "source venv/bin/activate"

def get_python_executable():
    """Get the Python executable in virtual environment"""
    if platform.system() == "Windows":
        return "venv\\Scripts\\python.exe"
    else:
        return "venv/bin/python"

def install_dependencies():
    """Install project dependencies"""
    python_exe = get_python_executable()
    
    if not Path(python_exe).exists():
        print("❌ Virtual environment not found. Please create it first.")
        return False
    
    print("📦 Installing project dependencies...")
    
    try:
        # Upgrade pip first
        print("⬆️ Upgrading pip...")
        run_command([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
        
        # Install project in editable mode
        print("📦 Installing project dependencies from pyproject.toml...")
        run_command([python_exe, "-m", "pip", "install", "-e", "."])
        
        # Install dev dependencies
        print("🛠️ Installing development dependencies...")
        run_command([python_exe, "-m", "pip", "install", "-e", ".[dev]"])
        
        print("✅ All dependencies installed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def verify_installation():
    """Verify that key packages are installed"""
    python_exe = get_python_executable()
    
    print("🧪 Verifying installation...")
    
    key_packages = [
        "deepagents",
        "fastapi", 
        "langchain",
        "langchain-core",
        "langchain-openai",
        "langchain-postgres",
        "psycopg"
    ]
    
    for package in key_packages:
        try:
            result = run_command([
                python_exe, "-c", 
                f"import {package.replace('-', '_')}; print(f'✅ {package} imported successfully')"
            ], check=False)
            
            if result.returncode != 0:
                print(f"⚠️ {package} import failed - this might be expected due to version conflicts")
        except Exception as e:
            print(f"⚠️ Could not verify {package}: {e}")
    
    print("🎉 Installation verification completed")

def show_next_steps():
    """Show next steps to user"""
    activation_cmd = get_activation_command()
    
    print("\n" + "="*60)
    print("🎉 Setup completed!")
    print("="*60)
    
    print(f"\n📋 Next steps:")
    print(f"1. Activate virtual environment:")
    print(f"   {activation_cmd}")
    
    print(f"\n2. Test the installation:")
    print(f"   python test_langchain_pgvector.py")
    
    print(f"\n3. Setup PostgreSQL with pgvector:")
    print(f"   python setup_langchain_pgvector.py")
    
    print(f"\n4. Run the service:")
    print(f"   python -m uvicorn app.main:app --reload")
    
    print(f"\n💡 Tips:")
    print(f"   - Always activate the virtual environment before working")
    print(f"   - Use 'pip list' to see installed packages")
    print(f"   - Use 'pip install -e .' to reinstall after changes")

def main():
    """Main setup function"""
    print("🚀 AI Agent Service Setup")
    print("="*60)
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    print(f"📁 Working directory: {project_dir.absolute()}")
    
    # Step 1: Create virtual environment
    if not create_virtual_environment():
        print("❌ Setup failed at virtual environment creation")
        return False
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False
    
    # Step 3: Verify installation
    verify_installation()
    
    # Step 4: Show next steps
    show_next_steps()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)
