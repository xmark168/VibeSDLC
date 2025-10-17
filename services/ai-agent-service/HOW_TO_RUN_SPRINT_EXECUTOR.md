# 🚀 Hướng Dẫn Chạy Sprint Task Executor

Guide chi tiết để chạy Sprint Task Executor và tự động xử lý tasks từ sprint backlog.

---

## 📋 Tổng Quan

Sprint Task Executor tự động:
1. ✅ Đọc sprint backlog từ `app/agents/product_owner/sprint.json` và `backlog.json`
2. ✅ Filter ra Development/Infrastructure tasks
3. ✅ Resolve dependencies giữa các tasks
4. ✅ Execute từng task với Developer Agent
5. ✅ Track progress với Langfuse tracing
6. ✅ Báo cáo kết quả chi tiết

---

## 🎯 Phương Pháp 1: Script Đơn Giản (Khuyến Nghị Cho Beginners)

### File: `run_sprint_executor.py`

**Chạy trực tiếp:**
```bash
cd ai-agent-service
python run_sprint_executor.py
```

**Customize trong code:**
```python
# Mở file run_sprint_executor.py và sửa:
sprint_id = "sprint-1"  # Thay đổi sprint ID
working_directory = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
model_name = "gpt-4o-mini"  # Hoặc "gpt-4o"
enable_pgvector = True
continue_on_error = True
```

**Output mẫu:**
```
🚀 Starting Sprint Task Executor
================================================================================
📋 Sprint ID: sprint-1
📁 Working Directory: D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo
🤖 Model: gpt-4o-mini
🔍 PGVector: Enabled
⚙️  Continue on Error: True
================================================================================

📂 Loading sprint and backlog data...
   Sprint: Implement core authentication and user management features
   Assigned Items: 15
   Total Backlog Items: 50

🔍 Filtering Development/Infrastructure tasks...
   Found 8 tasks to execute

🔗 Resolving task dependencies...
   Execution order:
   1. TASK-001: Implement User Registration API
   2. TASK-002: Create Login Endpoint (depends on: TASK-001)
   ...

🏃 Executing tasks...
================================================================================
📋 Task 1/8: Implement User Registration API
   ID: TASK-001
   Type: Development
================================================================================
[Developer Agent execution logs...]
✅ Task TASK-001 completed successfully

...

================================================================================
📊 EXECUTION SUMMARY
================================================================================
Status: completed
Total Tasks: 8
Executed: 8
✅ Succeeded: 8
❌ Failed: 0
⏱️  Duration: 1234.56s
================================================================================

🎉 All tasks completed successfully!
```

---

## 🎯 Phương Pháp 2: Script Advanced (Nhiều Options)

### File: `run_sprint_advanced.py`

**Preview tasks trước:**
```bash
python run_sprint_advanced.py --preview
```

**Execute với default settings:**
```bash
python run_sprint_advanced.py --execute
```

**Execute với custom settings:**
```bash
python run_sprint_advanced.py --execute \
  --sprint sprint-2 \
  --working-dir "D:\my-project" \
  --model gpt-4o \
  --no-pgvector \
  --stop-on-error
```

**Tất cả options:**
```
--preview              Preview tasks without executing
--execute              Execute all tasks
--sprint SPRINT_ID     Sprint ID (default: sprint-1)
--working-dir PATH     Working directory for code generation
--model MODEL          LLM model: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
--no-pgvector          Disable pgvector indexing
--stop-on-error        Stop on first task failure
```

---

## 🎯 Phương Pháp 3: CLI Tool (Có Sẵn)

### File: `test_sprint_execution.py`

**Preview tasks:**
```bash
python test_sprint_execution.py sprint-1 --preview
```

**Execute tasks:**
```bash
python test_sprint_execution.py sprint-1 --execute \
  --working-dir "D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
```

**Với custom model:**
```bash
python test_sprint_execution.py sprint-1 --execute \
  --working-dir "D:\my-project" \
  --model gpt-4o \
  --no-pgvector
```

---

## 🎯 Phương Pháp 4: Python Code Trực Tiếp

### Sử dụng `execute_sprint()` function

```python
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

from agents.developer.agent import execute_sprint

async def main():
    result = await execute_sprint(
        sprint_id="sprint-1",
        working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
        model_name="gpt-4o-mini",
        enable_pgvector=True,
        continue_on_error=True,
    )
    
    print(f"Status: {result['status']}")
    print(f"Succeeded: {result['tasks_succeeded']}")
    print(f"Failed: {result['tasks_failed']}")

asyncio.run(main())
```

### Sử dụng `SprintTaskExecutor` class

```python
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "app"))

from agents.developer.agent import SprintTaskExecutor

async def main():
    # Create executor
    executor = SprintTaskExecutor(
        working_directory=r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo",
        model_name="gpt-4o-mini",
        enable_pgvector=True,
    )
    
    # Preview tasks
    sprint_data = executor.load_sprint("sprint-1")
    backlog_items = executor.load_backlog()
    tasks = executor.filter_development_tasks(sprint_data, backlog_items)
    
    print(f"Found {len(tasks)} tasks to execute")
    
    # Execute
    result = await executor.execute_sprint(
        sprint_id="sprint-1",
        continue_on_error=True,
    )
    
    print(f"Status: {result['status']}")

asyncio.run(main())
```

---

## ⚙️ Configuration Options

### Sprint ID
- **Default:** `sprint-1`
- **Format:** `sprint-{number}`
- **Location:** `app/agents/product_owner/sprint.json`

### Working Directory
- **Default:** Current directory (`.`)
- **Recommended:** `D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo`
- **Purpose:** Nơi Developer Agent sẽ generate code

### Model Name
- **Options:**
  - `gpt-4o-mini` (default) - Nhanh, rẻ, phù hợp cho simple tasks
  - `gpt-4o` - Mạnh hơn, chậm hơn, đắt hơn
  - `gpt-3.5-turbo` - Nhanh nhất, rẻ nhất, kém chất lượng

### PGVector Indexing
- **Default:** `True`
- **Purpose:** Index codebase để Developer Agent tìm kiếm nhanh hơn
- **Disable:** Nếu không có pgvector hoặc muốn chạy nhanh hơn

### Continue on Error
- **Default:** `True`
- **True:** Tiếp tục execute tasks tiếp theo nếu 1 task fail
- **False:** Dừng ngay khi có task fail

---

## 📊 Output và Results

### Console Output
- Real-time progress của từng task
- Dependency resolution order
- Success/failure status
- Execution summary

### Langfuse Tracing
- Mỗi task có session ID: `sprint-{sprint_id}-{task_id}`
- User ID: `sprint-executor`
- Xem traces tại Langfuse dashboard

### Generated Code
- Code được generate vào `working_directory`
- Mỗi task có commits riêng
- Review code trong Git history

---

## 🔍 Troubleshooting

### Error: `ModuleNotFoundError: No module named 'deepagents'`
```bash
# Cài đặt dependencies
pip install -r requirements.txt
```

### Error: `FileNotFoundError: Backlog file not found`
- Check file tồn tại: `app/agents/product_owner/backlog.json`
- Check file tồn tại: `app/agents/product_owner/sprint.json`

### Error: `ValueError: Sprint not found: sprint-X`
- Check sprint ID trong `sprint.json`
- Đảm bảo format đúng: `sprint-1`, `sprint-2`, etc.

### No tasks found
- Check `task_type` field trong backlog items
- Chỉ có tasks với `task_type` = "Development" hoặc "Infrastructure" được execute
- Check `assigned_items` trong sprint.json

---

## 📚 Xem Thêm

- **Full Guide:** `SPRINT_EXECUTOR_GUIDE.md`
- **Implementation Details:** `SPRINT_EXECUTOR_IMPLEMENTATION.md`
- **Examples:** `examples/sprint_executor_example.py`
- **Source Code:** `app/agents/developer/agent.py` (lines 438-969)

---

## 🎉 Quick Start

**Cách nhanh nhất để bắt đầu:**

```bash
# 1. Preview tasks
python run_sprint_advanced.py --preview

# 2. Execute tasks
python run_sprint_advanced.py --execute

# Done! 🎉
```

