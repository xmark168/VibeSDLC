# Sprint Task Executor - Hướng Dẫn Sử Dụng

## 📖 Tổng Quan

**Sprint Task Executor** là một orchestrator layer tự động hóa việc thực thi các Development/Infrastructure tasks từ sprint backlog được tạo bởi Product Owner Agent.

### Chức năng chính:

1. ✅ Đọc dữ liệu từ `sprint.json` và `backlog.json`
2. ✅ Filter tasks theo `task_type` (Development/Infrastructure)
3. ✅ Resolve dependencies giữa các tasks
4. ✅ Tự động gọi Developer Agent cho mỗi task
5. ✅ Track progress với Langfuse tracing
6. ✅ Báo cáo kết quả chi tiết

---

## 🏗️ Kiến Trúc

```
Product Owner Agent
    ↓
    ├── backlog.json (All backlog items)
    └── sprint.json (Sprint planning)
         ↓
Sprint Task Executor ← YOU ARE HERE
    ↓
    ├── Filter: task_type = Development/Infrastructure
    ├── Resolve dependencies
    └── For each task:
         ↓
    Developer Agent
         ↓
    Code Generation → Commit → PR
```

---

## 📦 Installation

Không cần cài đặt thêm dependencies. Sprint Executor sử dụng các modules có sẵn:

- `app.agents.developer.agent` - Developer Agent
- `app.utils.langfuse_tracer` - Langfuse tracing (optional)

---

## 🚀 Quick Start

### 1. Preview Tasks

Xem trước các tasks sẽ được thực thi:

```bash
cd services/ai-agent-service
python test_sprint_execution.py sprint-1 --preview
```

**Output:**
```
📋 Preview: Development/Infrastructure Tasks in sprint-1

Found 2 tasks to execute:

1. TASK-001: Integrate with Google Calendar and Outlook
   Type: Task | Task Type: Development
   Status: Backlog

2. TASK-002: Implement user data encryption
   Type: Task | Task Type: Infrastructure
   Status: Backlog
```

### 2. Execute Sprint

Thực thi tất cả Development/Infrastructure tasks:

```bash
python test_sprint_execution.py sprint-1 --execute --working-dir ./target_project
```

**Output:**
```
🚀 Sprint Task Executor Started
   Sprint ID: sprint-1
   Working Directory: ./target_project
   Model: gpt-4o-mini

📂 Loading sprint and backlog data...
   Sprint: Sprint 1 deliverables
   Assigned Items: 12
   Total Backlog Items: 856

🔍 Filtering Development/Infrastructure tasks...
   Found 2 tasks to execute

🔗 Resolving task dependencies...
   Execution order:
   1. TASK-001: Integrate with Google Calendar and Outlook
   2. TASK-002: Implement user data encryption

🏃 Executing tasks...
📋 Task 1/2: Integrate with Google Calendar and Outlook
   ID: TASK-001
   Type: Development
...
```

---

## 💻 Programmatic Usage

### Basic Usage

```python
import asyncio
from app.agents.developer.agent import execute_sprint

async def main():
    result = await execute_sprint(
        sprint_id="sprint-1",
        working_directory="./target_project"
    )

    print(f"Status: {result['status']}")
    print(f"Tasks Succeeded: {result['tasks_succeeded']}")
    print(f"Tasks Failed: {result['tasks_failed']}")

asyncio.run(main())
```

### Advanced Usage

```python
from app.agents.developer.agent import SprintTaskExecutor

# Create executor with custom configuration
executor = SprintTaskExecutor(
    backlog_path="./custom/backlog.json",
    sprint_path="./custom/sprint.json",
    working_directory="./target_project",
    model_name="gpt-4o",  # Use more powerful model
    enable_pgvector=True,
)

# Execute sprint
result = await executor.execute_sprint(
    sprint_id="sprint-1",
    continue_on_error=False,  # Stop on first error
)

# Access detailed results
for task_result in result["results"]:
    task_id = task_result["task_id"]
    status = task_result["status"]
    
    if status == "success":
        dev_result = task_result["result"]
        print(f"✅ {task_id}: {len(dev_result['generated_files'])} files generated")
    else:
        print(f"❌ {task_id}: {task_result['error']}")
```

### Utility Functions

```python
from app.agents.developer.agent import (
    filter_development_tasks,
    format_task_as_request,
)

# Preview which tasks would be executed
tasks = filter_development_tasks("sprint-1")
print(f"Found {len(tasks)} Development/Infrastructure tasks")

# Preview how a task will be formatted
task = tasks[0]
user_request = format_task_as_request(task)
print(user_request)
```

---

## 🔧 Configuration

### Command Line Options

```bash
python test_sprint_execution.py <sprint_id> [OPTIONS]

Options:
  --preview              Preview tasks without executing
  --execute              Execute all Development/Infrastructure tasks
  --working-dir PATH     Working directory for Developer Agent (default: .)
  --model MODEL          LLM model to use (default: gpt-4o-mini)
  --no-pgvector          Disable pgvector indexing
  --stop-on-error        Stop execution if a task fails
```

### Python API Parameters

```python
execute_sprint(
    sprint_id: str,              # Sprint ID (e.g., "sprint-1")
    working_directory: str,      # Working directory for Developer Agent
    backlog_path: str = None,    # Path to backlog.json (auto-detect if None)
    sprint_path: str = None,     # Path to sprint.json (auto-detect if None)
    model_name: str = "gpt-4o-mini",  # LLM model
    enable_pgvector: bool = True,     # Enable pgvector indexing
    continue_on_error: bool = True,   # Continue if task fails
)
```

---

## 📊 Output Format

### Execution Result

```python
{
    "sprint_id": "sprint-1",
    "status": "completed",  # or "partial" if some tasks failed
    "tasks_total": 2,
    "tasks_executed": 2,
    "tasks_succeeded": 2,
    "tasks_failed": 0,
    "duration_seconds": 245.67,
    "start_time": "2025-10-17T10:00:00",
    "end_time": "2025-10-17T10:04:05",
    "results": [
        {
            "task_id": "TASK-001",
            "status": "success",
            "result": {
                "implementation_status": "completed",
                "generated_files": [...],
                "commit_history": [...],
                "todos": [...]
            }
        },
        {
            "task_id": "TASK-002",
            "status": "success",
            "result": {...}
        }
    ]
}
```

### Saved Results File

Results are automatically saved to `sprint_execution_results_{sprint_id}.json`:

```bash
ls -la sprint_execution_results_*.json
# sprint_execution_results_sprint-1.json
```

---

## 🔍 How It Works

### 1. Data Loading

```python
# Load sprint data
sprint_data = {
    "sprint_id": "sprint-1",
    "assigned_items": ["US-004", "TASK-002", "TASK-001", ...]
}

# Load backlog data
backlog_items = [
    {"id": "TASK-001", "task_type": "Development", ...},
    {"id": "TASK-002", "task_type": "Infrastructure", ...},
    ...
]
```

### 2. Task Filtering

```python
# Filter by:
# 1. Item is in sprint's assigned_items
# 2. task_type in ["Development", "Infrastructure"]
# 3. type in ["Task", "Sub-task"]

dev_tasks = [
    {"id": "TASK-001", "task_type": "Development", ...},
    {"id": "TASK-002", "task_type": "Infrastructure", ...},
]
```

### 3. Dependency Resolution

```python
# Topological sort based on dependencies field
# Example: SUB-010 depends on SUB-009
# Result: [SUB-009, SUB-010, TASK-001, TASK-002]

sorted_tasks = resolve_dependencies(dev_tasks)
```

### 4. Task Execution

```python
for task in sorted_tasks:
    # Format task as user_request
    user_request = f"""
    # {task['title']}
    
    ## Description
    {task['description']}
    
    ## Acceptance Criteria
    1. {criterion_1}
    2. {criterion_2}
    ...
    """
    
    # Execute Developer Agent
    result = await run_developer(
        user_request=user_request,
        working_directory=working_directory,
        session_id=f"sprint-{sprint_id}-{task_id}",
    )
```

---

## 🎯 Use Cases

### Use Case 1: Automated Sprint Execution

**Scenario:** Sprint planning hoàn tất, cần implement tất cả Development tasks

```bash
# Preview tasks
python test_sprint_execution.py sprint-1 --preview

# Execute all tasks
python test_sprint_execution.py sprint-1 --execute \
    --working-dir ./my_project \
    --model gpt-4o
```

### Use Case 2: Selective Task Execution

**Scenario:** Chỉ muốn execute một số tasks cụ thể

```python
from app.agents.developer.agent import SprintTaskExecutor

executor = SprintTaskExecutor(working_directory="./project")

# Get all tasks
sprint_data = executor.load_sprint("sprint-1")
backlog_items = executor.load_backlog()
all_tasks = executor.filter_development_tasks(sprint_data, backlog_items)

# Filter specific tasks
selected_tasks = [t for t in all_tasks if t['id'] in ['TASK-001', 'TASK-003']]

# Execute only selected tasks
for i, task in enumerate(selected_tasks, 1):
    result = await executor.execute_task(
        task=task,
        sprint_id="sprint-1",
        task_index=i,
        total_tasks=len(selected_tasks),
    )
```

### Use Case 3: Integration with CI/CD

**Scenario:** Tự động execute sprint tasks khi sprint start

```yaml
# .github/workflows/sprint-execution.yml
name: Sprint Execution

on:
  workflow_dispatch:
    inputs:
      sprint_id:
        description: 'Sprint ID to execute'
        required: true

jobs:
  execute-sprint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd services/ai-agent-service
          pip install -r requirements.txt
      
      - name: Execute Sprint
        run: |
          cd services/ai-agent-service
          python test_sprint_execution.py ${{ github.event.inputs.sprint_id }} \
            --execute \
            --working-dir ./target_project
      
      - name: Upload Results
        uses: actions/upload-artifact@v2
        with:
          name: sprint-results
          path: services/ai-agent-service/sprint_execution_results_*.json
```

---

## 🐛 Troubleshooting

### Issue 1: File Not Found

**Error:** `FileNotFoundError: Backlog file not found`

**Solution:**
```python
# Specify custom paths
executor = SprintTaskExecutor(
    backlog_path="./path/to/backlog.json",
    sprint_path="./path/to/sprint.json",
)
```

### Issue 2: No Tasks Found

**Error:** `No Development/Infrastructure tasks found in sprint`

**Cause:** Sprint không có tasks với `task_type` = Development/Infrastructure

**Solution:** Kiểm tra sprint.json và backlog.json:
```bash
# Check assigned items
cat sprint.json | jq '.[] | select(.sprint_id=="sprint-1") | .assigned_items'

# Check task types
cat backlog.json | jq '.[] | select(.task_type=="Development" or .task_type=="Infrastructure")'
```

### Issue 3: Task Execution Failed

**Error:** Task fails during execution

**Solution:**
```bash
# Check Langfuse traces for detailed error
# Visit: https://langfuse.vibesdlc.com

# Or check saved results file
cat sprint_execution_results_sprint-1.json | jq '.results[] | select(.status=="failed")'
```

---

## 📈 Monitoring với Langfuse

Mỗi task execution được trace tự động với Langfuse:

### Session ID Format

```
sprint-{sprint_id}-{task_id}
```

Example: `sprint-sprint-1-TASK-001`

### Viewing Traces

1. Mở Langfuse dashboard: https://langfuse.vibesdlc.com
2. Filter by session ID hoặc user ID (`sprint-executor`)
3. Xem chi tiết execution flow, timing, errors

### Trace Hierarchy

```
sprint-sprint-1-TASK-001
├── developer_agent_execution
│   ├── load_codebase
│   ├── write_todos
│   ├── generate_code
│   │   ├── code_generator_subagent
│   │   └── ...
│   ├── commit_changes
│   └── ...
```

---

## 🔐 Best Practices

### 1. Preview Before Execute

Luôn preview tasks trước khi execute:

```bash
python test_sprint_execution.py sprint-1 --preview
```

### 2. Use Appropriate Model

- `gpt-4o-mini`: Fast, cost-effective, good for simple tasks
- `gpt-4o`: More powerful, better for complex tasks

### 3. Handle Errors Gracefully

```python
result = await execute_sprint(
    sprint_id="sprint-1",
    continue_on_error=True,  # Continue even if some tasks fail
)

# Check which tasks failed
failed_tasks = [r for r in result["results"] if r["status"] == "failed"]
if failed_tasks:
    print(f"⚠️  {len(failed_tasks)} tasks failed. Review and retry.")
```

### 4. Version Control

Mỗi task tạo commits riêng, dễ dàng review và rollback:

```bash
# View commits created by Sprint Executor
git log --author="sprint-executor" --oneline

# Rollback specific task
git revert <commit-hash>
```

### 5. Monitor Progress

Sử dụng Langfuse để monitor real-time progress và debug issues.

---

## 🚧 Limitations

1. **Sequential Execution:** Tasks được execute tuần tự, không parallel (có thể improve trong tương lai)
2. **No Rollback:** Nếu task fail, không tự động rollback (cần manual intervention)
3. **JSON Files Only:** Hiện tại chỉ đọc từ JSON files, chưa support database
4. **No Task Status Update:** Không tự động update task status trong backlog.json

---

## 🔮 Future Enhancements

- [ ] Parallel task execution cho tasks không phụ thuộc nhau
- [ ] Automatic rollback on failure
- [ ] Database integration (thay vì JSON files)
- [ ] Real-time progress updates via WebSocket
- [ ] Task status synchronization với backlog
- [ ] Retry mechanism cho failed tasks
- [ ] Email/Slack notifications
- [ ] Web UI cho monitoring

---

## 📚 Related Documentation

- [Developer Agent README](./app/agents/developer/README.md)
- [Langfuse Integration Guide](./LANGFUSE_INTEGRATION_SUMMARY.md)
- [Product Owner Agent](./app/agents/product_owner/README.md)

---

## 🤝 Contributing

Nếu bạn muốn improve Sprint Executor, vui lòng:

1. Fork repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

---

## 📞 Support

Nếu gặp vấn đề, vui lòng:

1. Check Langfuse traces
2. Review saved results file
3. Check logs trong terminal
4. Open issue trên GitHub

---

**Happy Coding! 🚀**

