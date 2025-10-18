# Orchestrators Module

## 📖 Tổng Quan

Module **Orchestrators** cung cấp các orchestration layers để điều phối giữa các agents khác nhau và tự động hóa các workflows phức tạp.

### Orchestrators hiện có:

1. **Sprint Task Executor** - Tự động thực thi Development/Infrastructure tasks từ sprint backlog

---

## 🎯 Sprint Task Executor

### Mục đích

Nối kết giữa **Product Owner Agent** (planning) và **Developer Agent** (implementation) bằng cách:

- Đọc output từ Product Owner Agent (`sprint.json` + `backlog.json`)
- Filter tasks theo `task_type` (Development/Infrastructure)
- Tự động execute Developer Agent cho mỗi task
- Track progress và báo cáo kết quả

### Kiến trúc

```
Product Owner Agent
    ↓
    ├── backlog.json (All backlog items)
    └── sprint.json (Sprint planning)
         ↓
Sprint Task Executor
    ↓
    ├── Filter: task_type = Development/Infrastructure
    ├── Resolve dependencies
    └── For each task:
         ↓
    Developer Agent
         ↓
    Code Generation → Commit → PR
```

### Quick Start

#### 1. Preview Tasks

```bash
cd services/ai-agent-service
python test_sprint_execution.py sprint-1 --preview
```

#### 2. Execute Sprint

```bash
python test_sprint_execution.py sprint-1 --execute --working-dir ./target_project
```

#### 3. Programmatic Usage

```python
from app.agents.developer.orchestrators import execute_sprint

result = await execute_sprint(
    sprint_id="sprint-1",
    working_directory="./target_project"
)

print(f"Tasks Succeeded: {result['tasks_succeeded']}")
print(f"Tasks Failed: {result['tasks_failed']}")
```

### Features

✅ **Automatic Task Filtering**
- Chỉ execute tasks có `task_type` = "Development" hoặc "Infrastructure"
- Bỏ qua Testing, Documentation, Research tasks

✅ **Dependency Resolution**
- Topological sort để đảm bảo thứ tự đúng
- Tasks với dependencies được execute sau dependencies của chúng

✅ **Langfuse Tracing**
- Mỗi task có session ID riêng: `sprint-{sprint_id}-{task_id}`
- Track execution flow, timing, errors

✅ **Error Handling**
- Continue on error (default) hoặc stop on first error
- Detailed error reporting

✅ **Progress Tracking**
- Real-time console output
- Saved results to JSON file
- Langfuse dashboard monitoring

### API Reference

#### `execute_sprint()`

```python
async def execute_sprint(
    sprint_id: str,              # Sprint ID (e.g., "sprint-1")
    working_directory: str = ".", # Working directory for Developer Agent
    backlog_path: str = None,    # Path to backlog.json (auto-detect if None)
    sprint_path: str = None,     # Path to sprint.json (auto-detect if None)
    model_name: str = "gpt-4o-mini",  # LLM model
    enable_pgvector: bool = True,     # Enable pgvector indexing
    continue_on_error: bool = True,   # Continue if task fails
) -> Dict[str, Any]
```

**Returns:**
```python
{
    "sprint_id": "sprint-1",
    "status": "completed",  # or "partial" if some tasks failed
    "tasks_total": 2,
    "tasks_executed": 2,
    "tasks_succeeded": 2,
    "tasks_failed": 0,
    "duration_seconds": 245.67,
    "results": [...]
}
```

#### `filter_development_tasks()`

```python
def filter_development_tasks(
    sprint_id: str,
    backlog_path: str = None,
    sprint_path: str = None,
) -> List[Dict[str, Any]]
```

Preview which tasks would be executed without actually executing them.

#### `format_task_as_request()`

```python
def format_task_as_request(task: Dict[str, Any]) -> str
```

Format a backlog task as a `user_request` for Developer Agent.

#### `SprintTaskExecutor` Class

```python
class SprintTaskExecutor:
    def __init__(
        self,
        backlog_path: str = None,
        sprint_path: str = None,
        working_directory: str = ".",
        model_name: str = "gpt-4o-mini",
        enable_pgvector: bool = True,
    )
    
    async def execute_sprint(
        self,
        sprint_id: str,
        continue_on_error: bool = True,
    ) -> Dict[str, Any]
    
    async def execute_task(
        self,
        task: Dict[str, Any],
        sprint_id: str,
        task_index: int,
        total_tasks: int,
    ) -> Dict[str, Any]
```

### Examples

Xem thêm examples trong:
- `examples/sprint_executor_example.py` - 6 examples chi tiết
- `test_sprint_execution.py` - CLI tool

### Configuration

#### Environment Variables

Sprint Executor sử dụng các environment variables từ Developer Agent:

```env
# OpenAI/LLM Configuration
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-api-key

# PGVector (optional)
PGVECTOR_CONNECTION_STRING=postgresql://user:pass@host:port/db

# Langfuse (optional)
LANGFUSE_HOST=https://langfuse.vibesdlc.com
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

#### Command Line Options

```bash
python test_sprint_execution.py <sprint_id> [OPTIONS]

Options:
  --preview              Preview tasks without executing
  --execute              Execute all Development/Infrastructure tasks
  --working-dir PATH     Working directory for Developer Agent
  --model MODEL          LLM model to use (default: gpt-4o-mini)
  --no-pgvector          Disable pgvector indexing
  --stop-on-error        Stop execution if a task fails
```

### Data Flow

#### Input: sprint.json

```json
[
  {
    "sprint_id": "sprint-1",
    "assigned_items": ["US-004", "TASK-002", "TASK-001", ...]
  }
]
```

#### Input: backlog.json

```json
[
  {
    "id": "TASK-001",
    "type": "Task",
    "title": "Integrate with Google Calendar",
    "task_type": "Development",
    "description": "...",
    "acceptance_criteria": [...],
    "dependencies": []
  },
  {
    "id": "TASK-002",
    "type": "Task",
    "title": "Implement data encryption",
    "task_type": "Infrastructure",
    ...
  }
]
```

#### Processing

1. **Load Data:** Read sprint.json and backlog.json
2. **Filter:** Get items in sprint with task_type = Development/Infrastructure
3. **Sort:** Topological sort by dependencies
4. **Execute:** For each task, call Developer Agent

#### Output: Execution Results

```json
{
  "sprint_id": "sprint-1",
  "status": "completed",
  "tasks_succeeded": 2,
  "results": [
    {
      "task_id": "TASK-001",
      "status": "success",
      "result": {
        "implementation_status": "completed",
        "generated_files": [...],
        "commit_history": [...]
      }
    }
  ]
}
```

### Monitoring

#### Langfuse Tracing

Mỗi task execution được trace với:
- **Session ID:** `sprint-{sprint_id}-{task_id}`
- **User ID:** `sprint-executor`

View traces tại: https://langfuse.vibesdlc.com

#### Console Output

Real-time progress tracking:

```
🚀 Sprint Task Executor Started
📂 Loading sprint and backlog data...
🔍 Filtering Development/Infrastructure tasks...
   Found 2 tasks to execute
🔗 Resolving task dependencies...
🏃 Executing tasks...
📋 Task 1/2: Integrate with Google Calendar
   ✅ Task TASK-001 completed successfully
📋 Task 2/2: Implement data encryption
   ✅ Task TASK-002 completed successfully
📊 Sprint Execution Summary
   ✅ Succeeded: 2
   ❌ Failed: 0
```

### Troubleshooting

#### No Tasks Found

**Problem:** `No Development/Infrastructure tasks found in sprint`

**Solution:** Check sprint.json và backlog.json:
```bash
# Check assigned items
cat sprint.json | jq '.[] | select(.sprint_id=="sprint-1") | .assigned_items'

# Check task types
cat backlog.json | jq '.[] | select(.task_type=="Development" or .task_type=="Infrastructure")'
```

#### Task Execution Failed

**Problem:** Task fails during execution

**Solution:**
1. Check Langfuse traces for detailed error
2. Check saved results file: `sprint_execution_results_sprint-1.json`
3. Review console output for error messages

---

## 📚 Documentation

- [Sprint Executor Guide](../../SPRINT_EXECUTOR_GUIDE.md) - Hướng dẫn chi tiết
- [Developer Agent README](../agents/developer/README.md) - Developer Agent docs
- [Langfuse Integration](../../LANGFUSE_INTEGRATION_SUMMARY.md) - Tracing setup

---

## 🔮 Future Enhancements

- [ ] Parallel task execution
- [ ] Automatic rollback on failure
- [ ] Database integration (thay vì JSON files)
- [ ] Real-time progress updates via WebSocket
- [ ] Task status synchronization
- [ ] Retry mechanism
- [ ] Web UI

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

---

**Happy Orchestrating! 🚀**

