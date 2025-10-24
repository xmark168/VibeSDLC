# Daytona Integration Tests

Comprehensive test suite for Daytona sandbox integration in Developer Agent.

## 📁 Test Structure

```
tests/agents/developer/
├── daytona/
│   ├── conftest.py              # Pytest fixtures and test utilities
│   ├── test_adapters.py         # Unit tests for filesystem and git adapters
│   └── README.md                # This file
├── implementor/
│   └── nodes/
│       ├── test_setup_branch_daytona.py   # Tests for sandbox initialization
│       └── test_finalize_daytona.py       # Tests for sandbox cleanup
└── test_daytona_integration.py  # Integration tests for full workflow
```

## 🧪 Test Coverage

### Unit Tests

#### 1. Adapter Tests (`test_adapters.py`)
- **LocalFilesystemAdapter**: Read, write, list, create directory operations
- **DaytonaFilesystemAdapter**: Mocked sandbox filesystem operations
- **LocalGitAdapter**: Branch creation, commits with GitPython
- **DaytonaGitAdapter**: Mocked sandbox git operations
- **Factory Functions**: Adapter selection based on environment config

#### 2. Lifecycle Tests (`test_setup_branch_daytona.py`)
- **`_initialize_daytona_sandbox()`**: Sandbox creation, clone, state updates
- **`_extract_repo_url()`**: Repository URL extraction from git config
- **Error Handling**: Fallback scenarios, cleanup on failures

#### 3. Cleanup Tests (`test_finalize_daytona.py`)
- **`_handle_sandbox_cleanup()`**: Sandbox deletion after workflow completion
- **Skip Conditions**: When to skip cleanup (local mode, errors, etc.)
- **Error Handling**: Cleanup failures, config missing

### Integration Tests

#### Full Workflow Tests (`test_daytona_integration.py`)
- **Local Mode**: Backward compatibility verification
- **Daytona Mode**: Mocked sandbox workflow
- **Error Scenarios**: Fallback behavior, config issues
- **Lifecycle**: Complete create -> use -> cleanup flow

## 🚀 Running Tests

### Prerequisites

```bash
# Install dependencies
cd services/ai-agent-service
pip install -e .
pip install pytest pytest-cov pytest-mock
```

### Run All Daytona Tests

```bash
# Run all Daytona-related tests
pytest app/tests/agents/developer/daytona/ -v

# Run with coverage report
pytest app/tests/agents/developer/daytona/ --cov=app/agents/developer/daytona --cov-report=html

# Run with detailed output
pytest app/tests/agents/developer/daytona/ -vv -s
```

### Run Specific Test Files

```bash
# Adapter tests only
pytest app/tests/agents/developer/daytona/test_adapters.py -v

# Lifecycle integration tests
pytest app/tests/agents/developer/implementor/nodes/test_setup_branch_daytona.py -v
pytest app/tests/agents/developer/implementor/nodes/test_finalize_daytona.py -v

# Integration tests
pytest app/tests/agents/developer/test_daytona_integration.py -v
```

### Run Specific Test Classes or Methods

```bash
# Run specific test class
pytest app/tests/agents/developer/daytona/test_adapters.py::TestLocalFilesystemAdapter -v

# Run specific test method
pytest app/tests/agents/developer/daytona/test_adapters.py::TestLocalFilesystemAdapter::test_read_file -v
```

### Run with Different Modes

```bash
# Local mode tests (default)
DAYTONA_ENABLED=false pytest app/tests/agents/developer/daytona/ -v

# Daytona mode tests (with mocking)
DAYTONA_ENABLED=true pytest app/tests/agents/developer/daytona/ -v
```

## 📊 Coverage Report

Generate HTML coverage report:

```bash
pytest app/tests/agents/developer/daytona/ \
  --cov=app/agents/developer/daytona \
  --cov=app/agents/developer/implementor/nodes/setup_branch \
  --cov=app/agents/developer/implementor/nodes/finalize \
  --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## 🔧 Test Fixtures

### Available Fixtures (from `conftest.py`)

- **`mock_daytona_config`**: Mock DaytonaConfig object
- **`mock_daytona_config_disabled`**: Config for local mode
- **`mock_sandbox`**: Mock Daytona sandbox with fs/git APIs
- **`mock_sandbox_manager`**: Mock SandboxManager
- **`temp_git_repo`**: Temporary git repository for testing
- **`temp_working_directory`**: Temporary directory
- **`mock_env_daytona_enabled`**: Set Daytona env vars
- **`mock_env_daytona_disabled`**: Set local mode env vars
- **`sample_file_content`**: Sample Python code
- **`sample_git_commit_data`**: Sample commit data

### Using Fixtures in Tests

```python
def test_example(temp_git_repo, mock_daytona_config):
    """Example test using fixtures."""
    # temp_git_repo is a Path object to temporary git repo
    # mock_daytona_config is a DaytonaConfig object
    pass
```

## 🐛 Debugging Tests

### Run with Debug Output

```bash
# Show print statements
pytest app/tests/agents/developer/daytona/ -v -s

# Show local variables on failure
pytest app/tests/agents/developer/daytona/ -v -l

# Drop into debugger on failure
pytest app/tests/agents/developer/daytona/ -v --pdb
```

### Run Failed Tests Only

```bash
# Run only tests that failed in last run
pytest app/tests/agents/developer/daytona/ --lf

# Run failed tests first, then others
pytest app/tests/agents/developer/daytona/ --ff
```

## ✅ Expected Results

All tests should pass with local mode (DAYTONA_ENABLED=false):

```
======================== test session starts =========================
collected 45 items

test_adapters.py::TestLocalFilesystemAdapter::test_read_file PASSED
test_adapters.py::TestLocalFilesystemAdapter::test_write_file PASSED
...
test_setup_branch_daytona.py::TestInitializeDaytonaSandbox::test_initialize_sandbox_local_mode PASSED
...
test_finalize_daytona.py::TestHandleSandboxCleanup::test_cleanup_successful PASSED
...
test_daytona_integration.py::TestLocalModeIntegration::test_backward_compatibility PASSED

======================== 45 passed in 2.34s ==========================
```

## 📝 Writing New Tests

### Test Template

```python
import pytest
from unittest.mock import MagicMock, patch

class TestMyFeature:
    """Test description."""
    
    def test_my_scenario(self, temp_working_directory):
        """Test specific scenario."""
        # Setup
        # ... prepare test data
        
        # Execute
        # ... call function under test
        
        # Verify
        # ... assert expected results
        assert True
```

### Best Practices

1. **Use descriptive test names**: `test_initialize_sandbox_local_mode` not `test_init`
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **Use fixtures**: Reuse common setup via fixtures
4. **Mock external dependencies**: Don't call real Daytona API in tests
5. **Test error cases**: Not just happy path
6. **Keep tests isolated**: Each test should be independent

## 🔗 Related Documentation

- [DAYTONA_INTEGRATION_PLAN.md](../../../../DAYTONA_INTEGRATION_PLAN.md) - Overall integration plan
- [Daytona SDK Documentation](https://github.com/daytonaio/sdk) - Daytona SDK reference
- [Pytest Documentation](https://docs.pytest.org/) - Pytest framework docs

## 🆘 Troubleshooting

### Import Errors

If you get import errors:
```bash
# Make sure you're in the right directory
cd services/ai-agent-service

# Install package in editable mode
pip install -e .
```

### Fixture Not Found

If pytest can't find fixtures:
```bash
# Make sure conftest.py is in the right location
# Fixtures are automatically discovered from conftest.py files
```

### Tests Fail with "No module named 'agents'"

```bash
# Add parent directory to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/app"

# Or run from correct directory
cd services/ai-agent-service
pytest app/tests/...
```

## 📈 CI/CD Integration

### GitHub Actions Example

```yaml
name: Daytona Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd services/ai-agent-service
          pip install -e .
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd services/ai-agent-service
          pytest app/tests/agents/developer/daytona/ --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

