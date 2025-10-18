# 🔄 Migration Guide: Virtual FS → Direct Disk Tools

## 📋 Overview

This guide documents the migration from DeepAgents' Virtual FS tools to OpenSWE-style direct disk tools.

**Date:** 2024-01-XX  
**Status:** ⚠️ IN PROGRESS  
**Impact:** Major architectural change

---

## 🎯 Goals

1. **Replace Virtual FS tools** with direct disk operations
2. **Simplify workflow** - Remove sync step (Write → Commit instead of Write → Sync → Commit)
3. **Improve compatibility** - External tools can access files immediately
4. **Maintain DeepAgents framework** - Keep planning, subagents, state management

---

## 📦 What Changed

### **1. New Tools Created**

#### **Filesystem Tools** (`filesystem_tools.py`)
- ✅ `read_file_tool(file_path, start_line, end_line)` - Read from disk with line numbers
- ✅ `write_file_tool(file_path, content)` - Write directly to disk
- ✅ `edit_file_tool(file_path, old_str, new_str)` - Edit using str_replace pattern
- ✅ `list_files_tool(directory, pattern, recursive)` - List files with glob
- ✅ `grep_search_tool(pattern, directory, file_pattern)` - Search in files

#### **Shell Tools** (`shell_tools.py`)
- ✅ `shell_execute_tool(command, working_directory)` - Execute shell commands
- ✅ `shell_execute_safe_tool(command)` - Execute read-only commands

### **2. Deprecated Tools**

- ❌ `sync_virtual_to_disk_tool` - No longer needed
- ❌ `list_virtual_files_tool` - No longer needed
- ❌ DeepAgents built-in `write_file`, `edit_file`, `read_file`, `ls` - Replaced

### **3. Updated Instructions**

- ✅ `instructions_direct_disk.py` - New instructions without Virtual FS concepts
- ✅ `get_direct_disk_implementor_instructions()` - Function to generate instructions

### **4. Updated Subagents**

- ✅ `subagents.py` - Updated to use direct disk tools
- ✅ `get_code_generator_subagent()` - Function to create subagent with parameters

---

## 🔧 Migration Steps

### **Step 1: Update Imports in `agent.py`**

**BEFORE:**
```python
from agents.developer.implementor.tools import (
    load_codebase_tool,
    index_codebase_tool,
    search_similar_code_tool,
    sync_virtual_to_disk_tool,      # ❌ Remove
    list_virtual_files_tool,        # ❌ Remove
    # ... other tools
)
```

**AFTER:**
```python
from agents.developer.implementor.tools import (
    # Codebase operations
    load_codebase_tool,
    index_codebase_tool,
    search_similar_code_tool,
    # Direct filesystem operations (NEW)
    read_file_tool,
    write_file_tool,
    edit_file_tool,
    list_files_tool,
    grep_search_tool,
    # Shell execution (NEW)
    shell_execute_tool,
    shell_execute_safe_tool,
    # ... other tools (git, stack, generation, review)
)
```

**⚠️ IMPORTANT:** Update BOTH import blocks (lines ~95-110 and ~120-135) in `agent.py`

---

### **Step 2: Update Tools List in `create_developer_agent()`**

Find the `tools = [...]` list around line 200-230 and update:

**REMOVE:**
```python
tools = [
    sync_virtual_to_disk_tool,      # ❌ Remove
    list_virtual_files_tool,        # ❌ Remove
    # ...
]
```

**ADD:**
```python
tools = [
    # Direct filesystem operations
    read_file_tool,
    write_file_tool,
    edit_file_tool,
    list_files_tool,
    grep_search_tool,
    # Shell execution
    shell_execute_tool,
    shell_execute_safe_tool,
    # ... other tools
]
```

---

### **Step 3: Disable FilesystemMiddleware**

DeepAgents' `FilesystemMiddleware` adds Virtual FS tools. We need to bypass it.

**Option A: Don't include FilesystemMiddleware**

In `create_deep_agent()` call, check if there's a `middleware` parameter. If yes, exclude `FilesystemMiddleware`.

**Option B: Override with custom middleware**

Create custom middleware that provides direct disk tools instead of Virtual FS tools.

**Current status:** Need to investigate `create_deep_agent()` signature in DeepAgents.

---

### **Step 4: Update Instructions**

**BEFORE:**
```python
agent = create_deep_agent(
    tools=tools,
    instructions=instructions,  # Old instructions with Virtual FS
    subagents=subagents,
    model=llm,
)
```

**AFTER:**
```python
from agents.developer.instructions_direct_disk import get_direct_disk_implementor_instructions

agent = create_deep_agent(
    tools=tools,
    instructions=get_direct_disk_implementor_instructions(
        working_directory=working_directory,
        project_type="existing",
        enable_pgvector=True,
    ),
    subagents=subagents,
    model=llm,
)
```

---

### **Step 5: Update Subagent Configuration**

**BEFORE:**
```python
from agents.developer.implementor.subagents import code_generator_subagent

subagents = [code_generator_subagent]
```

**AFTER:**
```python
from agents.developer.implementor.subagents import get_code_generator_subagent

subagents = [
    get_code_generator_subagent(
        working_directory=working_directory,
        project_type="existing",
        enable_pgvector=True,
    )
]
```

---

## 🧪 Testing Checklist

### **Unit Tests**

- [ ] Test `read_file_tool` - Read existing file
- [ ] Test `write_file_tool` - Create new file
- [ ] Test `edit_file_tool` - Modify existing file with str_replace
- [ ] Test `list_files_tool` - List files with glob pattern
- [ ] Test `grep_search_tool` - Search for pattern in files
- [ ] Test `shell_execute_tool` - Execute command
- [ ] Test `shell_execute_safe_tool` - Execute read-only command

### **Integration Tests**

- [ ] Test simple task: Create new file → Commit
- [ ] Test edit task: Modify existing file → Commit
- [ ] Test search task: Grep search → Read file → Edit
- [ ] Test shell task: Run npm install → Verify node_modules
- [ ] Test Sprint Task Executor end-to-end
- [ ] Test Git operations work with direct disk files

### **Regression Tests**

- [ ] Verify existing functionality still works
- [ ] Check Langfuse tracing still works
- [ ] Check PGVector indexing still works
- [ ] Check boilerplate retrieval still works

---

## 🐛 Known Issues

### **Issue 1: Import Path Error**

**Symptom:**
```
ImportError: cannot import name 'shell_execute_tool' from 'agents.developer.implementor.tools'
```

**Cause:** Tools not exported in `__init__.py`

**Fix:** Verify `tools/__init__.py` exports all new tools:
```python
from .filesystem_tools import (
    read_file_tool,
    write_file_tool,
    edit_file_tool,
    list_files_tool,
    grep_search_tool,
)
from .shell_tools import (
    shell_execute_tool,
    shell_execute_safe_tool,
)

__all__ = [
    "read_file_tool",
    "write_file_tool",
    # ... etc
]
```

---

### **Issue 2: Agent Stuck on model_request**

**Symptom:** Agent shows "In progress..." for `model_request` indefinitely

**Possible causes:**
1. Import error causing agent initialization to fail silently
2. Instructions function not found (wrong import path)
3. Tool initialization error
4. LLM API timeout

**Debug steps:**
1. Check all imports resolve correctly
2. Verify `get_direct_disk_implementor_instructions()` is callable
3. Check LLM API key is valid
4. Add debug logging to see where it hangs

---

### **Issue 3: FilesystemMiddleware Conflict**

**Symptom:** Both Virtual FS and direct disk tools are available

**Cause:** DeepAgents automatically adds FilesystemMiddleware

**Fix:** Need to disable FilesystemMiddleware when creating agent

---

## 📊 Workflow Comparison

### **OLD Workflow (Virtual FS)**

```
1. write_todos([...])
2. load_codebase_tool(...)
3. FOR EACH TODO:
   a. write_file(...)              # → Virtual FS (State["files"])
   b. edit_file(...)               # → Virtual FS
   c. sync_virtual_to_disk_tool()  # → Real Disk
   d. commit_changes_tool(...)     # → Git
   e. Update todo → "completed"
4. create_pull_request_tool()
```

### **NEW Workflow (Direct Disk)**

```
1. write_todos([...])
2. load_codebase_tool(...)
3. FOR EACH TODO:
   a. write_file_tool(...)         # → Real Disk (direct)
   b. edit_file_tool(...)          # → Real Disk (direct)
   c. commit_changes_tool(...)     # → Git (no sync needed!)
   d. Update todo → "completed"
4. create_pull_request_tool()
```

**Key difference:** No sync step! Files go directly to disk.

---

## 🔄 Rollback Plan

If migration causes issues:

1. **Revert imports** in `agent.py`:
   - Remove new filesystem tools imports
   - Add back `sync_virtual_to_disk_tool`, `list_virtual_files_tool`

2. **Revert instructions**:
   - Use old `instructions.py` instead of `instructions_direct_disk.py`

3. **Revert subagents**:
   - Use `code_generator_subagent` dict instead of `get_code_generator_subagent()` function

4. **Revert tools list**:
   - Remove direct disk tools from `tools = [...]`
   - Add back Virtual FS sync tools

5. **Test** that old workflow works again

---

## 📝 Next Steps

1. ✅ Create filesystem tools - DONE
2. ✅ Create shell tools - DONE
3. ✅ Create direct disk instructions - DONE
4. ✅ Update subagents configuration - DONE
5. ⏳ Update `agent.py` imports - IN PROGRESS (IDE auto-format issues)
6. ⏳ Update `agent.py` tools list - PENDING
7. ⏳ Disable FilesystemMiddleware - PENDING
8. ⏳ Test simple task - PENDING
9. ⏳ Test Sprint Task Executor - PENDING
10. ⏳ Create comprehensive tests - PENDING

---

## 💡 Tips

- **Use grep_search_tool** instead of reading entire files
- **Use shell_execute_safe_tool** for read-only commands (safer)
- **Always verify files exist** after write_file_tool with read_file_tool
- **Check command output** from shell_execute_tool for errors
- **Use working_directory parameter** to ensure correct paths

---

## 📚 References

- OpenSWE text-editor tool: `services/open-swe/apps/open-swe/src/tools/builtin-tools/text-editor.ts`
- OpenSWE grep tool: `services/open-swe/apps/open-swe/src/tools/grep.ts`
- OpenSWE shell tool: `services/open-swe/apps/open-swe/src/tools/shell.ts`
- DeepAgents tools: `services/deepagents/src/deepagents/tools.py`
- DeepAgents middleware: `services/deepagents/src/deepagents/middleware.py`

---

**Last Updated:** 2024-01-XX  
**Status:** ⚠️ Migration in progress - Agent stuck on model_request, investigating import issues

