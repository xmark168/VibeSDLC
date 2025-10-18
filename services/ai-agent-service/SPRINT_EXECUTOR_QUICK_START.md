# ⚡ Sprint Task Executor - Quick Start

Chạy Sprint Task Executor trong 2 phút!

---

## 🚀 Cách Nhanh Nhất

```bash
cd ai-agent-service

# Preview tasks
python run_sprint_advanced.py --preview

# Execute tasks
python run_sprint_advanced.py --execute
```

**Done! 🎉**

---

## 📋 3 Cách Chạy Sprint Executor

### 1️⃣ Script Đơn Giản (Beginners)

```bash
python run_sprint_executor.py
```

**Pros:** Đơn giản, không cần arguments  
**Cons:** Phải sửa code để customize

---

### 2️⃣ Script Advanced (Recommended)

```bash
# Preview
python run_sprint_advanced.py --preview

# Execute với defaults
python run_sprint_advanced.py --execute

# Execute với custom settings
python run_sprint_advanced.py --execute \
  --sprint sprint-2 \
  --model gpt-4o \
  --working-dir "D:\my-project"
```

**Pros:** Flexible, nhiều options  
**Cons:** Cần nhớ arguments

---

### 3️⃣ CLI Tool (Original)

```bash
# Preview
python test_sprint_execution.py sprint-1 --preview

# Execute
python test_sprint_execution.py sprint-1 --execute \
  --working-dir "D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
```

**Pros:** Original tool, well-tested  
**Cons:** Verbose arguments

---

## ⚙️ Common Options

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `--sprint` | sprint-1, sprint-2, ... | sprint-1 | Sprint ID |
| `--model` | gpt-4o-mini, gpt-4o | gpt-4o-mini | LLM model |
| `--working-dir` | Any path | Current dir | Code output |
| `--no-pgvector` | Flag | Enabled | Disable indexing |
| `--stop-on-error` | Flag | Continue | Stop on fail |

---

## 📊 What Happens?

```
1. 📂 Load sprint.json + backlog.json
2. 🔍 Filter Development/Infrastructure tasks
3. 🔗 Resolve dependencies
4. 🏃 Execute each task with Developer Agent
5. 📊 Show summary
```

---

## 🎯 Example Output

```
🚀 Sprint Task Executor Started
   Sprint ID: sprint-1
   Working Directory: D:\...\demo
   Model: gpt-4o-mini

📂 Loading sprint and backlog data...
   Found 8 tasks to execute

🔗 Resolving task dependencies...
   Execution order:
   1. TASK-001: Implement User Registration API
   2. TASK-002: Create Login Endpoint (depends on: TASK-001)
   ...

🏃 Executing tasks...
================================================================================
📋 Task 1/8: Implement User Registration API
================================================================================
[Developer Agent logs...]
✅ Task TASK-001 completed successfully

...

📊 Sprint Execution Summary
   Total Tasks: 8
   ✅ Succeeded: 8
   ❌ Failed: 0
   ⏱️  Duration: 1234.56s

🎉 All tasks completed successfully!
```

---

## 🔧 Customize Working Directory

**Trong script:**
```python
# run_sprint_executor.py
working_directory = r"D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
```

**Trong CLI:**
```bash
python run_sprint_advanced.py --execute \
  --working-dir "D:\capstone project\VibeSDLC\services\ai-agent-service\app\agents\demo"
```

---

## 🐛 Common Issues

### `ModuleNotFoundError: No module named 'deepagents'`
```bash
pip install -r requirements.txt
```

### `FileNotFoundError: Backlog file not found`
- Check: `app/agents/product_owner/backlog.json` exists
- Check: `app/agents/product_owner/sprint.json` exists

### `No Development/Infrastructure tasks found`
- Check `task_type` field in backlog items
- Only "Development" and "Infrastructure" tasks are executed

---

## 📚 Full Documentation

- **How to Run:** `HOW_TO_RUN_SPRINT_EXECUTOR.md`
- **Full Guide:** `SPRINT_EXECUTOR_GUIDE.md`
- **Implementation:** `SPRINT_EXECUTOR_IMPLEMENTATION.md`

---

## 💡 Pro Tips

1. **Always preview first:**
   ```bash
   python run_sprint_advanced.py --preview
   ```

2. **Use gpt-4o for complex tasks:**
   ```bash
   python run_sprint_advanced.py --execute --model gpt-4o
   ```

3. **Stop on error for debugging:**
   ```bash
   python run_sprint_advanced.py --execute --stop-on-error
   ```

4. **Check Langfuse for traces:**
   - Session ID: `sprint-{sprint_id}-{task_id}`
   - User ID: `sprint-executor`

---

## 🎉 That's It!

Bạn đã sẵn sàng để chạy Sprint Task Executor!

```bash
python run_sprint_advanced.py --preview
python run_sprint_advanced.py --execute
```

**Happy Coding! 🚀**

