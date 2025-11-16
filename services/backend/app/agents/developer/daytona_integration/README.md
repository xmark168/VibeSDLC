# Daytona Sandbox Integration

Tích hợp Daytona Sandbox vào Developer Agent workflow để thay thế local filesystem và git operations bằng remote sandbox operations.

## 📋 Overview

Daytona module cung cấp abstraction layer cho filesystem và git operations, cho phép Developer Agent hoạt động trong cả **local mode** và **Daytona sandbox mode** mà không cần thay đổi business logic.

### Key Features

- ✅ **Backward Compatible**: Support cả local mode và Daytona mode
- ✅ **Adapter Pattern**: Decouple business logic khỏi implementation details
- ✅ **Sandbox Lifecycle Management**: Tự động create, reuse, cleanup sandbox
- ✅ **Error Handling**: Graceful error handling với clear messages
- ✅ **Configuration**: Toggle mode bằng environment variables

## 🏗️ Architecture

```
daytona/
├── config.py                    # Load config từ .env
├── sandbox_manager.py           # Sandbox lifecycle management
├── adapters/
│   ├── base.py                  # Abstract base classes
│   ├── filesystem_adapter.py    # Filesystem implementations (TODO)
│   └── git_adapter.py           # Git implementations (TODO)
└── utils.py                     # Helper functions (TODO)
```

### Adapter Pattern

```
FilesystemAdapter (Abstract)
├── LocalFilesystemAdapter → Path() operations
└── DaytonaFilesystemAdapter → sandbox.fs.* API

GitAdapter (Abstract)
├── LocalGitAdapter → GitPython
└── DaytonaGitAdapter → sandbox.git.* API
```

## 🚀 Quick Start

### 1. Enable Daytona Mode

Add to `.env`:

```env
DAYTONA_ENABLED=true
DAYTONA_API_KEY=dtn_xxx
DAYTONA_API_URL=http://localhost:3000/api
DAYTONA_ORGANIZATION_ID=xxx
DAYTONA_TARGET=us
DAYTONA_SANDBOX_LANGUAGE=node
DAYTONA_SANDBOX_SNAPSHOT=node
DAYTONA_WORKSPACE_PATH=/root/workspace
```

### 2. Initialize Sandbox Manager

```python
from app.agents.developer.daytona import DaytonaConfig, get_sandbox_manager

# Load config từ .env
config = DaytonaConfig.from_env()

if config and config.enabled:
    # Get sandbox manager (singleton)
    sandbox_manager = get_sandbox_manager(config)
    
    # Create sandbox
    sandbox_info = sandbox_manager.create_sandbox()
    print(f"Sandbox ID: {sandbox_info['sandbox_id']}")
    
    # Get sandbox instance
    sandbox = sandbox_manager.get_sandbox()
    
    # Use sandbox for operations
    # ...
    
    # Cleanup when done
    sandbox_manager.cleanup_sandbox()
```

### 3. Use Adapters (TODO - Phase 2)

```python
from app.agents.developer.daytona.adapters import get_filesystem_adapter, get_git_adapter

# Get adapters (auto-detect based on config)
fs_adapter = get_filesystem_adapter()
git_adapter = get_git_adapter()

# Filesystem operations
content = fs_adapter.read_file("app/main.py", working_directory="/root/workspace/repo")
fs_adapter.write_file("app/new.py", "print('hello')", working_directory="/root/workspace/repo")

# Git operations
git_adapter.create_branch("feature/new-feature", base_branch="main", working_directory="/root/workspace/repo")
git_adapter.commit("Add new feature", working_directory="/root/workspace/repo")
git_adapter.push(working_directory="/root/workspace/repo")
```

## 📚 API Reference

### DaytonaConfig

Load configuration từ environment variables.

```python
config = DaytonaConfig.from_env()

# Properties
config.api_key              # Daytona API key
config.api_url              # Daytona API URL
config.organization_id      # Organization ID
config.target               # Target region (us, eu, etc.)
config.enabled              # Whether Daytona is enabled
config.sandbox_language     # Sandbox language (node, python, etc.)
config.sandbox_snapshot     # Sandbox snapshot name
config.workspace_path       # Workspace path in sandbox

# Convert to Daytona SDK config
sdk_config = config.to_daytona_config()
```

### SandboxManager

Quản lý sandbox lifecycle.

```python
sandbox_manager = get_sandbox_manager(config)

# Create sandbox
sandbox_info = sandbox_manager.create_sandbox()
# Returns: {"sandbox_id": "...", "workspace_path": "...", "status": "created"}

# Get sandbox instance
sandbox = sandbox_manager.get_sandbox()

# Check if sandbox is active
is_active = sandbox_manager.is_sandbox_active()

# Get workspace path for repository
repo_path = sandbox_manager.get_workspace_path("my-repo")
# Returns: "/root/workspace/my-repo"

# Cleanup sandbox
cleanup_info = sandbox_manager.cleanup_sandbox()
# Returns: {"status": "deleted", "sandbox_id": "..."}
```

### FilesystemAdapter (Abstract)

```python
class FilesystemAdapter(ABC):
    def read_file(file_path, start_line, end_line, working_directory) -> str
    def write_file(file_path, content, working_directory, create_dirs) -> str
    def list_files(directory, pattern, recursive, working_directory) -> str
    def delete_file(file_path, working_directory) -> str
    def create_directory(directory, working_directory, mode) -> str
```

### GitAdapter (Abstract)

```python
class GitAdapter(ABC):
    def clone(url, path, working_directory) -> dict
    def create_branch(branch_name, base_branch, source_branch, working_directory) -> dict
    def commit(message, files, working_directory) -> dict
    def push(branch, remote, working_directory) -> dict
    def status(working_directory) -> dict
    def checkout(branch, working_directory) -> dict
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DAYTONA_ENABLED` | No | `false` | Enable/disable Daytona mode |
| `DAYTONA_API_KEY` | Yes* | - | Daytona API key |
| `DAYTONA_API_URL` | No | `http://localhost:3000/api` | Daytona API URL |
| `DAYTONA_ORGANIZATION_ID` | Yes* | - | Organization ID |
| `DAYTONA_TARGET` | No | `us` | Target region |
| `DAYTONA_SANDBOX_LANGUAGE` | No | `node` | Sandbox language |
| `DAYTONA_SANDBOX_SNAPSHOT` | No | `node` | Sandbox snapshot |
| `DAYTONA_WORKSPACE_PATH` | No | `/root/workspace` | Workspace path in sandbox |

*Required when `DAYTONA_ENABLED=true`

### Example `.env`

```env
# Daytona Configuration
DAYTONA_ENABLED=true
DAYTONA_API_KEY=dtn_11f95f46cd25f1318decec5fb6f0aee697229f55f1d27625d625519d4bfae5ec
DAYTONA_API_URL=http://localhost:3000/api
DAYTONA_ORGANIZATION_ID=31012942-b17d-46cd-989d-35d08e120265
DAYTONA_TARGET=us
DAYTONA_SANDBOX_LANGUAGE=node
DAYTONA_SANDBOX_SNAPSHOT=node
DAYTONA_WORKSPACE_PATH=/root/workspace
```

## 🧪 Testing

### Unit Tests

```python
# Test config loading
def test_daytona_config_from_env():
    os.environ["DAYTONA_ENABLED"] = "true"
    os.environ["DAYTONA_API_KEY"] = "test_key"
    os.environ["DAYTONA_ORGANIZATION_ID"] = "test_org"
    
    config = DaytonaConfig.from_env()
    assert config.enabled == True
    assert config.api_key == "test_key"

# Test sandbox manager
def test_sandbox_manager_create():
    config = DaytonaConfig(...)
    manager = SandboxManager(config)
    
    sandbox_info = manager.create_sandbox()
    assert sandbox_info["status"] == "created"
    assert manager.is_sandbox_active() == True
```

### Integration Tests

```python
# Test full workflow with Daytona
def test_developer_agent_with_daytona():
    os.environ["DAYTONA_ENABLED"] = "true"
    
    agent = DeveloperAgent(...)
    result = agent.run(sprint_id="test-sprint")
    
    assert result["status"] == "success"
```

## 📝 Implementation Status

### ✅ Phase 1: Foundation (COMPLETED)
- [x] `config.py` - Configuration loading
- [x] `sandbox_manager.py` - Sandbox lifecycle management
- [x] `adapters/base.py` - Abstract base classes

### 🚧 Phase 2: Adapter Implementations (TODO)
- [ ] `adapters/filesystem_adapter.py` - Filesystem implementations
- [ ] `adapters/git_adapter.py` - Git implementations
- [ ] Adapter factory functions

### 🚧 Phase 3: Tool Refactoring (TODO)
- [ ] Refactor `filesystem_tools.py` to use adapters
- [ ] Refactor `git_tools_gitpython.py` to use adapters

### 🚧 Phase 4: Lifecycle Integration (TODO)
- [ ] Sprint initialization with sandbox creation
- [ ] Sprint finalization with sandbox cleanup
- [ ] Repository cloning logic

## 🐛 Troubleshooting

### Daytona API Connection Failed

```
Error: Failed to create sandbox: Connection refused
```

**Solution**: Check if Daytona API is running at `DAYTONA_API_URL`

### Invalid API Key

```
Error: Sandbox creation failed: Unauthorized
```

**Solution**: Verify `DAYTONA_API_KEY` is correct

### Sandbox Creation Timeout

```
Error: Sandbox creation failed: Timeout
```

**Solution**: Check network connection and Daytona service status

## 📖 References

- [Daytona Python SDK Documentation](https://www.daytona.io/docs/en/python-sdk/)
- [Daytona Git API](https://www.daytona.io/docs/en/python-sdk/sync/git/)
- [Daytona Filesystem API](https://www.daytona.io/docs/en/python-sdk/sync/filesystem/)

---

**Status**: Phase 1 COMPLETED ✅ | See `DAYTONA_INTEGRATION_PLAN.md` for full implementation plan

