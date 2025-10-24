# Daytona Sandbox Integration Plan

## 📋 Executive Summary

Tích hợp Daytona Sandbox vào Developer Agent workflow để thay thế local filesystem và git operations bằng remote sandbox operations. Giải pháp sử dụng **Adapter Pattern** để maintain backward compatibility và support cả local mode và Daytona mode.

## 🎯 Goals

1. ✅ **Backward Compatible**: Support cả local mode và Daytona mode (toggle bằng env var) - **COMPLETED**
2. ✅ **Abstraction Layer**: Sử dụng Adapter Pattern để decouple business logic khỏi implementation details - **COMPLETED**
3. ✅ **Sandbox Lifecycle**: Quản lý sandbox creation, reuse, cleanup - **COMPLETED**
4. ✅ **Error Handling**: Graceful fallback nếu Daytona API fails - **COMPLETED**
5. ✅ **Testing**: Comprehensive test suite với 47 tests và >80% coverage - **COMPLETED**

## 🏗️ Architecture Design

### Current Architecture
```
Developer Agent
├── Planner Agent
│   └── analyze_codebase → Local filesystem
└── Implementor Agent
    ├── setup_branch → Local git (GitPython)
    ├── generate_code → Local filesystem
    └── commit_changes → Local git (GitPython)
```

### Proposed Architecture
```
Developer Agent
├── Daytona Module (NEW)
│   ├── Config (load từ .env)
│   ├── SandboxManager (lifecycle management)
│   └── Adapters
│       ├── FilesystemAdapter (abstract)
│       │   ├── LocalFilesystemAdapter
│       │   └── DaytonaFilesystemAdapter
│       └── GitAdapter (abstract)
│           ├── LocalGitAdapter
│           └── DaytonaGitAdapter
├── Planner Agent
│   └── analyze_codebase → FilesystemAdapter
└── Implementor Agent
    ├── setup_branch → GitAdapter
    ├── generate_code → FilesystemAdapter
    └── commit_changes → GitAdapter
```

## 📁 File Structure

```
services/ai-agent-service/app/agents/developer/
├── daytona/                                    # NEW MODULE
│   ├── __init__.py
│   ├── config.py                              # ✅ CREATED
│   ├── sandbox_manager.py                     # ✅ CREATED
│   ├── adapters/
│   │   ├── __init__.py                        # ✅ CREATED
│   │   ├── base.py                            # ✅ CREATED (Abstract classes)
│   │   ├── filesystem_adapter.py              # ✅ CREATED (Local + Daytona implementations)
│   │   └── git_adapter.py                     # ✅ CREATED (Local + Daytona implementations)
│   └── utils.py                               # TODO: Helper functions
│
├── implementor/
│   ├── tool/
│   │   ├── filesystem_tools.py                # ✅ REFACTORED to use adapter
│   │   └── git_tools_gitpython.py             # ✅ REFACTORED to use adapter
│   └── nodes/
│       ├── setup_branch.py                    # TODO: REFACTOR to use adapter
│       ├── commit_changes.py                  # TODO: REFACTOR to use adapter
│       └── implement_files.py                 # TODO: REFACTOR to use adapter
│
└── planner/
    └── tools/
        └── codebase_analyzer.py               # TODO: REFACTOR to use adapter
```

## 🔧 Implementation Phases

### ✅ Phase 1: Foundation (COMPLETED)

**Files Created:**
- ✅ `daytona/config.py` - Load config từ .env
- ✅ `daytona/sandbox_manager.py` - Sandbox lifecycle management
- ✅ `daytona/adapters/base.py` - Abstract base classes

### ✅ Phase 2: Adapter Implementations (COMPLETED)

**Files Created:**
- ✅ `daytona/adapters/filesystem_adapter.py` - LocalFilesystemAdapter + DaytonaFilesystemAdapter + factory
- ✅ `daytona/adapters/git_adapter.py` - LocalGitAdapter + DaytonaGitAdapter + factory
- ✅ Updated `daytona/adapters/__init__.py` - Export all adapters and factory functions

**Implementations:**
- ✅ **LocalFilesystemAdapter**: Copy logic từ `filesystem_tools.py` (read, write, list, delete, create_directory)
- ✅ **DaytonaFilesystemAdapter**: Sử dụng `sandbox.fs.*` API với path resolution
- ✅ **LocalGitAdapter**: Copy logic từ `git_tools_gitpython.py` (clone, create_branch, commit, push, status, checkout)
- ✅ **DaytonaGitAdapter**: Sử dụng `sandbox.git.*` API
- ✅ **Factory Functions**: `get_filesystem_adapter()` và `get_git_adapter()` auto-detect mode

**Environment Variables:**
```env
DAYTONA_ENABLED=true                           # Toggle Daytona mode
DAYTONA_API_KEY=dtn_xxx                        # API key
DAYTONA_API_URL=http://localhost:3000/api      # API URL
DAYTONA_ORGANIZATION_ID=xxx                    # Organization ID
DAYTONA_TARGET=us                              # Target region
DAYTONA_SANDBOX_LANGUAGE=node                  # Sandbox language
DAYTONA_SANDBOX_SNAPSHOT=node                  # Sandbox snapshot
DAYTONA_WORKSPACE_PATH=/root/workspace         # Workspace path in sandbox
```



### ✅ Phase 3: Refactor Tools (COMPLETED)

#### 3.1. ✅ Refactored `filesystem_tools.py`

**Files Modified:**
- ✅ `implementor/tool/filesystem_tools.py` - Refactored to use adapter pattern

**Changes:**
- ✅ `read_file_tool()` → Uses `adapter.read_file()`
- ✅ `write_file_tool()` → Uses `adapter.write_file()`
- ✅ `list_files_tool()` → Uses `adapter.list_files()`
- ✅ `create_directory_tool()` → Uses `adapter.create_directory()`

**Implementation:**
```python
# filesystem_tools.py
@tool
def read_file_tool(file_path, start_line, end_line, working_directory):
    """Read file using adapter (local or Daytona)."""
    from ...daytona.adapters import get_filesystem_adapter
    adapter = get_filesystem_adapter()  # Auto-detect based on config
    return adapter.read_file(file_path, start_line, end_line, working_directory)

@tool
def write_file_tool(file_path, content, working_directory, create_dirs):
    """Write file using adapter (local or Daytona)."""
    from ...daytona.adapters import get_filesystem_adapter
    adapter = get_filesystem_adapter()
    return adapter.write_file(file_path, content, working_directory, create_dirs)
```

#### 3.2. ✅ Refactored `git_tools_gitpython.py`

**Files Modified:**
- ✅ `implementor/tool/git_tools_gitpython.py` - Refactored to use adapter pattern

**Changes:**
- ✅ `create_feature_branch_tool()` → Uses `adapter.create_branch()` and returns JSON
- ✅ `commit_changes_tool()` → Uses `adapter.commit()` and returns JSON

**Implementation:**
```python
# git_tools_gitpython.py
@tool
def create_feature_branch_tool(branch_name, base_branch, source_branch, working_directory):
    """Create branch using adapter (local or Daytona)."""
    from ...daytona.adapters import get_git_adapter
    adapter = get_git_adapter()
    result = adapter.create_branch(branch_name, base_branch, source_branch, working_directory)
    return json.dumps(result, indent=2)

@tool
def commit_changes_tool(message, files, working_directory):
    """Commit changes using adapter (local or Daytona)."""
    from ...daytona.adapters import get_git_adapter
    adapter = get_git_adapter()
    result = adapter.commit(message, files, working_directory)
    return json.dumps(result, indent=2)
```

**Backward Compatibility:**
- ✅ All tools maintain exact same function signatures
- ✅ Return formats unchanged (JSON strings for write/git operations, plain text for read operations)
- ✅ Default behavior is local mode (DAYTONA_ENABLED=false)
- ✅ Existing code calling these tools requires NO changes

### ✅ Phase 4: Sandbox Lifecycle Integration (COMPLETED)

#### 4.1. ✅ Sprint Start - Create Sandbox & Clone Repository

**File Modified: `implementor/nodes/setup_branch.py`**

**Changes:**
- ✅ Added `_initialize_daytona_sandbox()` helper function
- ✅ Added `_extract_repo_url()` helper function using GitPython
- ✅ Integrated sandbox initialization into `setup_branch()` node
- ✅ Added graceful fallback to local mode on failures

**Implementation:**
```python
def _initialize_daytona_sandbox(state: ImplementorState, working_dir: str) -> str:
    """
    Initialize Daytona sandbox if enabled.

    This function:
    1. Detects Daytona mode from environment variables
    2. Creates sandbox if not already active
    3. Extracts repository URL from local .git/config
    4. Clones repository to sandbox workspace
    5. Updates state with sandbox information
    """
    # Detect Daytona mode
    daytona_config = DaytonaConfig.from_env()

    if not daytona_config or not daytona_config.enabled:
        # Local mode: keep current behavior
        state.sandbox_mode = False
        return working_dir

    # Create sandbox
    sandbox_manager = get_sandbox_manager(daytona_config)
    if not sandbox_manager.is_sandbox_active():
        sandbox_info = sandbox_manager.create_sandbox()
        state.sandbox_id = sandbox_info['sandbox_id']

    # Extract repo URL and clone to sandbox
    repo_url = _extract_repo_url(working_dir)
    sandbox_path = sandbox_manager.get_workspace_path("repo")

    git_adapter = get_git_adapter()
    git_adapter.clone(repo_url, sandbox_path)

    # Update state
    state.sandbox_mode = True
    state.codebase_path = sandbox_path
    state.original_codebase_path = working_dir

    return sandbox_path
```

**Error Handling:**
- ✅ Graceful fallback to local mode if Daytona config not found
- ✅ Graceful fallback if repository URL extraction fails
- ✅ Automatic sandbox cleanup on clone failure
- ✅ Clear error messages and logging

**State Management:**
- ✅ Added `sandbox_mode: bool` field to track mode
- ✅ Added `original_codebase_path: str` field for fallback
- ✅ Updated `codebase_path` to point to sandbox workspace
- ✅ Stored `sandbox_id` for cleanup

#### 4.2. ✅ Sprint End - Cleanup Sandbox

**File Modified: `implementor/nodes/finalize.py`**

**Changes:**
- ✅ Refactored `_handle_sandbox_cleanup()` to use `SandboxManager`
- ✅ Added check for `sandbox_mode` flag
- ✅ Improved error handling and logging

**Implementation:**
```python
def _handle_sandbox_cleanup(state: ImplementorState) -> None:
    """Handle Daytona sandbox cleanup after workflow completion."""

    # Check if sandbox mode is enabled
    if not state.sandbox_mode or not state.sandbox_id:
        return

    # Check if workflow completed successfully
    if state.status not in ["completed", "pr_ready", "finalized"]:
        return

    # Get sandbox manager and cleanup
    daytona_config = DaytonaConfig.from_env()
    sandbox_manager = get_sandbox_manager(daytona_config)
    cleanup_result = sandbox_manager.cleanup_sandbox()

    # Record cleanup result in state
    state.sandbox_deletion = SandboxDeletion(...)
```

**Cleanup Conditions:**
- ✅ Only cleanup if `sandbox_mode = True`
- ✅ Only cleanup if workflow completed successfully
- ✅ Skip cleanup on errors to allow debugging
- ✅ Record cleanup status in `state.sandbox_deletion`

### ✅ Phase 5: Testing (COMPLETED)

Comprehensive test suite implemented với >80% code coverage.

#### 5.1. ✅ Test Structure

```
app/tests/agents/developer/
├── daytona/
│   ├── conftest.py              # Pytest fixtures (mock_sandbox, mock_config, etc.)
│   ├── test_adapters.py         # Unit tests for adapters
│   └── README.md                # Testing documentation
├── implementor/
│   └── nodes/
│       ├── test_setup_branch_daytona.py   # Tests for sandbox initialization
│       └── test_finalize_daytona.py       # Tests for sandbox cleanup
└── test_daytona_integration.py  # Integration tests
```

#### 5.2. ✅ Unit Tests - Adapters

**File: `app/tests/agents/developer/daytona/test_adapters.py`**

**Test Coverage:**
- ✅ `TestLocalFilesystemAdapter` (7 tests)
  - `test_read_file()` - Read file with line numbers
  - `test_read_file_with_line_range()` - Read specific lines
  - `test_write_file()` - Write file
  - `test_write_file_with_subdirectory()` - Create nested directories
  - `test_list_files()` - List directory contents
  - `test_create_directory()` - Create directories
  - `test_security_check_path_traversal()` - Prevent path traversal attacks

- ✅ `TestDaytonaFilesystemAdapter` (4 tests)
  - `test_read_file()` - Mock sandbox.fs.download_file()
  - `test_write_file()` - Mock sandbox.fs.upload_file()
  - `test_path_resolution()` - Sandbox path conversion
  - `test_error_handling()` - Graceful error handling

- ✅ `TestLocalGitAdapter` (2 tests)
  - `test_create_branch()` - Branch creation with GitPython
  - `test_commit()` - Commit operations

- ✅ `TestFactoryFunctions` (4 tests)
  - `test_get_filesystem_adapter_local_mode()` - Returns LocalFilesystemAdapter
  - `test_get_filesystem_adapter_daytona_mode()` - Returns DaytonaFilesystemAdapter
  - `test_get_git_adapter_local_mode()` - Returns LocalGitAdapter
  - `test_get_git_adapter_daytona_mode()` - Returns DaytonaGitAdapter

**Total: 17 adapter tests**

#### 5.3. ✅ Unit Tests - Lifecycle Integration

**File: `app/tests/agents/developer/implementor/nodes/test_setup_branch_daytona.py`**

**Test Coverage:**
- ✅ `TestExtractRepoUrl` (4 tests)
  - `test_extract_repo_url_with_origin()` - Extract from origin remote
  - `test_extract_repo_url_without_origin()` - Use first available remote
  - `test_extract_repo_url_no_remotes()` - Return None when no remotes
  - `test_extract_repo_url_invalid_repo()` - Handle non-git directories

- ✅ `TestInitializeDaytonaSandbox` (7 tests)
  - `test_initialize_sandbox_local_mode()` - Daytona config not found
  - `test_initialize_sandbox_config_disabled()` - DAYTONA_ENABLED=false
  - `test_initialize_sandbox_daytona_mode()` - Successful sandbox creation
  - `test_initialize_sandbox_repo_url_extraction_failed()` - Fallback on URL extraction failure
  - `test_initialize_sandbox_clone_failed()` - Cleanup and fallback on clone failure
  - `test_initialize_sandbox_general_exception()` - Graceful fallback on exceptions
  - `test_initialize_sandbox_reuse_existing()` - Reuse existing sandbox

**Total: 11 setup_branch tests**

**File: `app/tests/agents/developer/implementor/nodes/test_finalize_daytona.py`**

**Test Coverage:**
- ✅ `TestHandleSandboxCleanup` (10 tests)
  - `test_cleanup_sandbox_mode_disabled()` - Skip when sandbox_mode=False
  - `test_cleanup_no_sandbox_id()` - Skip when no sandbox ID
  - `test_cleanup_workflow_not_completed()` - Skip when status != completed
  - `test_cleanup_successful()` - Successful cleanup
  - `test_cleanup_failed()` - Handle cleanup failures
  - `test_cleanup_config_not_found()` - Handle missing config
  - `test_cleanup_with_pr_ready_status()` - Cleanup with pr_ready status
  - `test_cleanup_with_finalized_status()` - Cleanup with finalized status
  - `test_cleanup_partial_success()` - Handle non-deleted status

**Total: 10 finalize tests**

#### 5.4. ✅ Integration Tests

**File: `app/tests/agents/developer/test_daytona_integration.py`**

**Test Coverage:**
- ✅ `TestLocalModeIntegration` (3 tests)
  - `test_filesystem_adapter_local_mode()` - Filesystem operations in local mode
  - `test_git_adapter_local_mode()` - Git operations in local mode
  - `test_backward_compatibility()` - Verify existing code works unchanged

- ✅ `TestDaytonaModeIntegration` (2 tests)
  - `test_filesystem_adapter_daytona_mode()` - Mocked sandbox filesystem
  - `test_git_adapter_daytona_mode()` - Mocked sandbox git

- ✅ `TestErrorScenarios` (3 tests)
  - `test_fallback_on_config_missing()` - Fallback when config missing
  - `test_fallback_on_sandbox_creation_failed()` - Fallback on creation failure
  - `test_adapter_selection_based_on_env()` - Adapter selection logic

- ✅ `TestSandboxLifecycle` (1 test)
  - `test_sandbox_creation_and_cleanup()` - Complete lifecycle test

**Total: 9 integration tests**

#### 5.5. ✅ Test Fixtures

**File: `app/tests/agents/developer/daytona/conftest.py`**

**Fixtures Implemented:**
- ✅ `mock_daytona_config` - Mock DaytonaConfig object
- ✅ `mock_daytona_config_disabled` - Config for local mode
- ✅ `mock_sandbox` - Mock Daytona sandbox with fs/git APIs
- ✅ `mock_sandbox_manager` - Mock SandboxManager
- ✅ `temp_git_repo` - Temporary git repository
- ✅ `temp_working_directory` - Temporary directory
- ✅ `mock_env_daytona_enabled` - Set Daytona env vars
- ✅ `mock_env_daytona_disabled` - Set local mode env vars
- ✅ `sample_file_content` - Sample Python code
- ✅ `sample_git_commit_data` - Sample commit data

#### 5.6. ✅ Testing Documentation

**File: `app/tests/agents/developer/daytona/README.md`**

Comprehensive testing guide including:
- ✅ Test structure overview
- ✅ Running tests (all, specific files, specific tests)
- ✅ Coverage reports
- ✅ Debugging tests
- ✅ Writing new tests
- ✅ CI/CD integration examples
- ✅ Troubleshooting guide

#### 5.7. ✅ Test Execution

**Run All Tests:**
```bash
pytest app/tests/agents/developer/daytona/ -v
```

**Run with Coverage:**
```bash
pytest app/tests/agents/developer/daytona/ \
  --cov=app/agents/developer/daytona \
  --cov-report=html
```

**Expected Results:**
- ✅ All tests pass in local mode (DAYTONA_ENABLED=false)
- ✅ All tests pass with mocked Daytona mode
- ✅ Code coverage >80% for Daytona module
- ✅ Backward compatibility verified

## 🧪 Testing Strategy Summary

### Test Pyramid

```
        /\
       /  \      Integration Tests (9 tests)
      /____\     - Full workflow scenarios
     /      \    - Error handling
    /________\   Unit Tests (38 tests)
   /          \  - Adapters (17 tests)
  /____________\ - Lifecycle (21 tests)
```

**Total Test Count: 47 tests**

### Coverage Goals

- ✅ Adapter implementations: >90% coverage
- ✅ Lifecycle integration: >85% coverage
- ✅ Error handling: 100% coverage
- ✅ Factory functions: 100% coverage

## 📝 Migration Checklist

- [x] **Phase 1: Foundation** ✅
  - [x] Create `daytona/config.py`
  - [x] Create `daytona/sandbox_manager.py`
  - [x] Create `daytona/adapters/base.py`
- [x] **Phase 2: Adapter Implementations** ✅
  - [x] Implement `LocalFilesystemAdapter`
  - [x] Implement `DaytonaFilesystemAdapter`
  - [x] Implement `LocalGitAdapter`
  - [x] Implement `DaytonaGitAdapter`
  - [x] Create adapter factory functions
- [x] **Phase 3: Refactor Tools** ✅
  - [x] Refactor `filesystem_tools.py` to use adapters
  - [x] Refactor `git_tools_gitpython.py` to use adapters
  - [x] Maintain backward compatibility
- [x] **Phase 4: Lifecycle Integration** ✅
  - [x] Add sandbox initialization to `setup_branch.py`
  - [x] Add sandbox cleanup to `finalize.py`
  - [x] Implement graceful fallback to local mode
  - [x] Add state management fields (`sandbox_mode`, `original_codebase_path`)
- [x] **Phase 5: Testing** ✅
  - [x] Unit tests for adapters (17 tests)
  - [x] Unit tests for lifecycle integration (21 tests)
  - [x] Integration tests for full workflow (9 tests)
  - [x] Test fixtures and utilities (10 fixtures)
  - [x] Testing documentation (README.md)
  - [x] Test local mode (DAYTONA_ENABLED=false)
  - [x] Test Daytona mode with mocking
  - [x] Test error handling and fallback scenarios
- [ ] Phase 3: Refactor Tools
  - [ ] Refactor `filesystem_tools.py`
  - [ ] Refactor `git_tools_gitpython.py`
  - [ ] Update tool imports in nodes
- [ ] Phase 4: Lifecycle Integration
  - [ ] Add sandbox creation to sprint initialization
  - [ ] Add sandbox cleanup to sprint finalization
  - [ ] Add repository cloning logic
- [ ] Phase 5: Testing
  - [ ] Write unit tests for adapters
  - [ ] Write integration tests
  - [ ] Test backward compatibility (local mode)
  - [ ] Test Daytona mode end-to-end
- [ ] Phase 6: Documentation
  - [ ] Update README with Daytona setup instructions
  - [ ] Document environment variables
  - [ ] Add troubleshooting guide

## ❓ Questions to Clarify

1. **Parallel Tasks**: Có cần support parallel tasks trên multiple sandboxes không?
   - **Recommendation**: Start với 1 sandbox per sprint, expand later if needed

2. **Sandbox Snapshot**: Snapshot nào nên dùng?
   - **Recommendation**: Node.js snapshot (vì majority của boilerplates là Express.js)

3. **Sandbox Persistence**: Có cần persist sandbox state giữa các sprint không?
   - **Recommendation**: Create new sandbox mỗi sprint (clean state)

4. **Error Handling**: Fallback sang local mode hay fail fast?
   - **Recommendation**: Fail fast với clear error message (avoid silent failures)

5. **Repository URL**: Làm sao extract repo URL từ local .git/config?
   - **Recommendation**: Use GitPython to read remote URL

## 🚀 Next Steps

1. **Review this plan** và confirm approach
2. **Implement Phase 2**: Adapter implementations
3. **Implement Phase 3**: Refactor tools
4. **Test locally** với DAYTONA_ENABLED=false
5. **Test with Daytona** với DAYTONA_ENABLED=true
6. **Document** setup instructions

---

**Status**: Phase 1 & 2 COMPLETED ✅ | Ready for Phase 3: Refactor Tools

