# Implementor Tools Package

Tools được sử dụng trong Implementor Agent workflow.

## 📦 Overview

Package này chứa tất cả các tools cần thiết cho Implementor Agent:
- File operations (read, write, edit)
- Shell command execution
- Git operations
- Incremental code editing
- Stack detection & boilerplate retrieval

## 🛠️ Available Tools

### Filesystem Operations

#### `read_file_tool(file_path, start_line, end_line, working_directory)`
Đọc file từ disk với optional line range.

```python
from app.agents.developer.implementor.tool import read_file_tool

content = read_file_tool("app/main.py", start_line=10, end_line=20)
```

#### `write_file_tool(file_path, content, working_directory)`
Ghi file vào disk.

```python
from app.agents.developer.implementor.tool import write_file_tool

result = write_file_tool("app/config.py", "CONFIG = {}")
```

#### `edit_file_tool(file_path, old_str, new_str, working_directory)`
Edit file bằng cách replace old_str với new_str.

```python
from app.agents.developer.implementor.tool import edit_file_tool

result = edit_file_tool("app/main.py", "old_code", "new_code")
```

#### `list_files_tool(directory, pattern, working_directory)`
List files trong directory.

```python
from app.agents.developer.implementor.tool import list_files_tool

files = list_files_tool("app/", pattern="*.py")
```

#### `grep_search_tool(pattern, directory, working_directory)`
Search cho pattern trong files.

```python
from app.agents.developer.implementor.tool import grep_search_tool

results = grep_search_tool("def main", "app/")
```

#### `create_directory_tool(directory_path, working_directory)`
Tạo directory.

```python
from app.agents.developer.implementor.tool import create_directory_tool

result = create_directory_tool("app/utils/")
```

### External File Operations

#### `copy_directory_from_external_tool(source, destination, working_directory)`
Copy directory từ external source.

```python
from app.agents.developer.implementor.tool import copy_directory_from_external_tool

result = copy_directory_from_external_tool("/templates/fastapi", ".")
```

### Shell Execution

#### `shell_execute_tool(command, working_directory, timeout, allow_dangerous)`
Execute shell command.

```python
from app.agents.developer.implementor.tool import shell_execute_tool

output = shell_execute_tool("npm install", working_directory="./frontend")
```

#### `shell_execute_safe_tool(command, working_directory, timeout)`
Execute shell command safely (blocks dangerous commands).

```python
from app.agents.developer.implementor.tool import shell_execute_safe_tool

output = shell_execute_safe_tool("pytest tests/", timeout=120)
```

### Git Operations

#### `create_feature_branch_tool(branch_name, base_branch, working_directory)`
Tạo feature branch.

```python
from app.agents.developer.implementor.tool import create_feature_branch_tool

result = create_feature_branch_tool("feature/new-api", "main")
```

#### `commit_changes_tool(message, files, working_directory)`
Commit changes.

```python
from app.agents.developer.implementor.tool import commit_changes_tool

result = commit_changes_tool("Add new feature", files=["app/main.py"])
```

#### `create_pull_request_tool(title, description, base_branch, working_directory, draft)`
Tạo pull request.

```python
from app.agents.developer.implementor.tool import create_pull_request_tool

result = create_pull_request_tool(
    title="Add new feature",
    description="This PR adds...",
    base_branch="main"
)
```

### Incremental Code Editing

#### `add_function_tool(file_path, function_code, after_function, before_function, working_directory)`
Thêm function vào file.

```python
from app.agents.developer.implementor.tool import add_function_tool

result = add_function_tool(
    "app/utils.py",
    "def helper():\n    return 'result'",
    after_function="existing_func"
)
```

#### `add_import_tool(file_path, import_statement, working_directory)`
Thêm import statement.

```python
from app.agents.developer.implementor.tool import add_import_tool

result = add_import_tool("app/main.py", "from fastapi import Depends")
```

#### `create_method_tool(file_path, class_name, method_code, working_directory)`
Thêm method vào class.

```python
from app.agents.developer.implementor.tool import create_method_tool

result = create_method_tool(
    "app/models.py",
    "UserModel",
    "def get_name(self):\n    return self.name"
)
```

#### `modify_function_tool(file_path, function_name, changes, working_directory)`
Modify function.

```python
from app.agents.developer.implementor.tool import modify_function_tool

result = modify_function_tool(
    "app/main.py",
    "main",
    changes=[{"type": "add_line", "line": "    print('hello')"}]
)
```

### Stack Detection & Boilerplate

#### `detect_stack_tool(directory, working_directory)`
Detect project tech stack.

```python
from app.agents.developer.implementor.tool import detect_stack_tool

stack = detect_stack_tool(".")
# Returns: {"language": "python", "framework": "fastapi", ...}
```

#### `retrieve_boilerplate_tool(stack_type, template_name, destination, working_directory)`
Retrieve boilerplate template.

```python
from app.agents.developer.implementor.tool import retrieve_boilerplate_tool

result = retrieve_boilerplate_tool("fastapi", "basic", ".")
```

## 📚 Usage in Nodes

### Example: implement_files.py
```python
from ..tool.filesystem_tools import read_file_tool, write_file_tool
from ..tool.incremental_tools import add_function_tool

def implement_files(state):
    # Read existing file
    content = read_file_tool("app/main.py")
    
    # Add new function
    result = add_function_tool("app/utils.py", "def new_func(): pass")
    
    # Write new file
    write_file_tool("app/config.py", "CONFIG = {}")
```

## 🔒 Security

- All tools validate paths to prevent directory traversal
- Shell execution blocks dangerous commands by default
- File operations are restricted to working directory

## 📝 Error Handling

All tools return error messages on failure:

```python
result = read_file_tool("nonexistent.py")
# Returns: "Error: File 'nonexistent.py' does not exist"
```

## 🚀 Performance

- File operations use direct disk I/O
- Shell execution has configurable timeout (default: 60s)
- Git operations use GitPython for efficiency

## 📖 More Information

- See `TOOL_MIGRATION_COMPLETE.md` for migration details
- See individual tool files for implementation details
- See node files for usage examples

---

**Package**: `app.agents.developer.implementor.tool`
**Status**: ✅ Active
**Tools**: 18 total

