# 📚 OpenSWE Prompt Integration Guide

Guide để tích hợp OpenSWE prompt vào Implementor Subagent của VibeSDLC.

---

## 🎯 Mục Tiêu

Kết hợp điểm mạnh của:
- **OpenSWE**: Coding standards, tool usage best practices, communication guidelines
- **VibeSDLC Current**: Virtual FS workflow, PGVector indexing, Sprint/Scrum context

---

## ✅ CÓ THỂ SỬ DỤNG - Với Điều Kiện

**Câu trả lời:** **CÓ**, nhưng cần **merge** và **customize** thay vì thay thế hoàn toàn.

### ⚠️ Lý Do Không Thể Thay Thế Trực Tiếp

1. **Virtual FS Concept** - OpenSWE không có, VibeSDLC CRITICAL
2. **Tool Names** - OpenSWE dùng tools khác (grep, view, str_replace vs write_file, edit_file)
3. **Workflow** - OpenSWE auto-commits, VibeSDLC cần explicit sync
4. **Context** - OpenSWE terminal-based, VibeSDLC Sprint/Scrum-based

---

## 📊 So Sánh Chi Tiết

### **Sections Nên Lấy từ OpenSWE**

| Section | Lines | Value | Priority |
|---------|-------|-------|----------|
| CORE_BEHAVIOR_PROMPT | 15-19 | Persistence, Accuracy, Planning | ⭐⭐⭐ HIGH |
| CODING_STANDARDS_PROMPT | 52-71 | Read before write, Fix root causes, No backups | ⭐⭐⭐ HIGH |
| TOOL_USE_BEST_PRACTICES | 38-50 | Search patterns, Dependencies, Parallel calls | ⭐⭐⭐ HIGH |
| COMMUNICATION_GUIDELINES | 73-78 | Markdown formatting, Brief summaries | ⭐⭐ MEDIUM |
| LANGGRAPH_SPECIFIC_PATTERNS | 310-784 | LangGraph code generation | ⭐ LOW (Optional) |

### **Sections KHÔNG Nên Lấy**

| Section | Lines | Reason |
|---------|-------|--------|
| IDENTITY_PROMPT | 4-6 | "terminal-based... built by LangChain" - Wrong context |
| FILE_CODE_MANAGEMENT | 30-36 | "Auto-committed" - Conflicts with Virtual FS |
| MARK_TASK_COMPLETED | 89-96 | OpenSWE-specific task system |
| Tool-specific instructions | Various | Tools don't exist in DeepAgents |

---

## 🎨 Implementation Strategy

### **Phase 1: Create Enhanced Instructions** ✅ DONE

**File:** `app/agents/developer/instructions_enhanced.py`

**Structure:**
```python
IDENTITY_PROMPT                    # VibeSDLC-specific
CORE_BEHAVIOR_PROMPT              # From OpenSWE
VIRTUAL_FS_WORKFLOW_PROMPT        # VibeSDLC CRITICAL
CODING_STANDARDS_PROMPT           # From OpenSWE
TOOL_USE_BEST_PRACTICES_PROMPT    # From OpenSWE
COMMUNICATION_GUIDELINES_PROMPT   # From OpenSWE

def get_enhanced_implementor_instructions(...):
    # Combines all sections with dynamic content
    return f"""..."""
```

---

### **Phase 2: Update Subagent Configuration**

**File:** `app/agents/developer/implementor/subagents.py`

**Before:**
```python
from ..instructions import get_implementor_instructions

code_generator_subagent = {
    "name": "code_generator",
    "prompt": """# CODE GENERATOR SUBAGENT
    
    You are an expert code generator...
    """,
    "tools": [...]
}
```

**After:**
```python
from ..instructions_enhanced import get_enhanced_implementor_instructions

code_generator_subagent = {
    "name": "code_generator",
    "prompt": get_enhanced_implementor_instructions(
        working_directory=".",  # Will be set dynamically
        project_type="existing",
        enable_pgvector=True
    ),
    "tools": [...]
}
```

---

### **Phase 3: Update Agent Creation**

**File:** `app/agents/developer/agent.py`

**Update `run_developer()` function:**

```python
from .instructions_enhanced import get_enhanced_implementor_instructions

async def run_developer(
    user_request: str,
    working_directory: str = ".",
    project_type: str = "existing",
    enable_pgvector: bool = True,
    ...
):
    # Generate enhanced instructions
    instructions = get_enhanced_implementor_instructions(
        working_directory=working_directory,
        project_type=project_type,
        enable_pgvector=enable_pgvector,
        boilerplate_templates_path=str(Path(__file__).parent.parent.parent / "templates" / "boilerplate")
    )
    
    # Create agent with enhanced instructions
    agent = create_deep_agent(
        tools=tools,
        instructions=instructions,  # Use enhanced instructions
        subagents=subagents,
        model=llm,
        ...
    )
    
    ...
```

---

## 🔧 Migration Steps

### **Step 1: Backup Current Instructions**

```bash
cd ai-agent-service/app/agents/developer
cp instructions.py instructions_backup.py
```

### **Step 2: Test Enhanced Instructions**

```python
# Test script
from app.agents.developer.instructions_enhanced import get_enhanced_implementor_instructions

instructions = get_enhanced_implementor_instructions(
    working_directory="./test",
    project_type="existing",
    enable_pgvector=True
)

print(instructions)
print(f"\nLength: {len(instructions)} characters")
```

### **Step 3: Update Subagent**

```bash
# Edit subagents.py
# Change import from instructions to instructions_enhanced
```

### **Step 4: Update Agent**

```bash
# Edit agent.py
# Use get_enhanced_implementor_instructions() instead of get_implementor_instructions()
```

### **Step 5: Test with Simple Task**

```python
result = await run_developer(
    user_request="Add a health check endpoint to the API",
    working_directory="./test_project"
)
```

### **Step 6: Compare Results**

- Check if code quality improved
- Verify Virtual FS workflow still works
- Ensure PGVector indexing still functions
- Test Sprint Task Executor integration

---

## 📋 Checklist

### **Before Migration**

- [ ] Backup current instructions.py
- [ ] Review enhanced instructions
- [ ] Understand Virtual FS workflow
- [ ] Test current implementation

### **During Migration**

- [ ] Create instructions_enhanced.py
- [ ] Update subagents.py imports
- [ ] Update agent.py to use enhanced instructions
- [ ] Test with simple task
- [ ] Verify Virtual FS sync works

### **After Migration**

- [ ] Test with complex task
- [ ] Verify Sprint Task Executor works
- [ ] Check Langfuse tracing
- [ ] Monitor code quality
- [ ] Collect feedback

---

## 🎯 Expected Benefits

### **Improved Code Quality**

- ✅ Better coding standards enforcement
- ✅ More consistent code style
- ✅ Fewer unnecessary comments
- ✅ Better error handling

### **Better Tool Usage**

- ✅ More efficient search patterns
- ✅ Parallel tool calling
- ✅ Better dependency management
- ✅ Pre-commit hook integration

### **Improved Communication**

- ✅ Better markdown formatting
- ✅ More concise summaries
- ✅ Clearer output

### **Maintained Functionality**

- ✅ Virtual FS workflow preserved
- ✅ PGVector indexing still works
- ✅ Sprint/Scrum context maintained
- ✅ Boilerplate management intact

---

## ⚠️ Potential Issues

### **Issue 1: Prompt Too Long**

**Symptom:** Token limit exceeded  
**Solution:** Remove optional sections (e.g., LangGraph patterns)

### **Issue 2: Virtual FS Not Working**

**Symptom:** Files not syncing to disk  
**Solution:** Verify VIRTUAL_FS_WORKFLOW_PROMPT is included

### **Issue 3: Tool Names Mismatch**

**Symptom:** Agent tries to call non-existent tools  
**Solution:** Ensure tool names are adapted for DeepAgents

### **Issue 4: Context Loss**

**Symptom:** Agent doesn't understand Sprint context  
**Solution:** Verify IDENTITY_PROMPT includes VibeSDLC context

---

## 🔍 Testing Strategy

### **Unit Tests**

```python
def test_enhanced_instructions_generation():
    instructions = get_enhanced_implementor_instructions()
    assert "VIRTUAL FS" in instructions
    assert "sync_virtual_to_disk_tool" in instructions
    assert "write_file()" in instructions

def test_pgvector_instructions_included():
    instructions = get_enhanced_implementor_instructions(enable_pgvector=True)
    assert "pgvector" in instructions
    assert "index_codebase_tool" in instructions

def test_boilerplate_instructions_for_new_project():
    instructions = get_enhanced_implementor_instructions(project_type="new")
    assert "boilerplate" in instructions
    assert "detect_stack_tool" in instructions
```

### **Integration Tests**

```python
async def test_simple_code_generation():
    result = await run_developer(
        user_request="Add a health check endpoint",
        working_directory="./test_project"
    )
    assert result["implementation_status"] == "completed"
    assert len(result["generated_files"]) > 0

async def test_virtual_fs_sync():
    result = await run_developer(
        user_request="Create a new file test.py",
        working_directory="./test_project"
    )
    # Verify file exists on disk
    assert Path("./test_project/test.py").exists()
```

---

## 📚 References

- **OpenSWE Prompt:** `services/open-swe/apps/open-swe/src/graphs/programmer/nodes/generate-message/prompt.ts`
- **Current Instructions:** `services/ai-agent-service/app/agents/developer/instructions.py`
- **Enhanced Instructions:** `services/ai-agent-service/app/agents/developer/instructions_enhanced.py`
- **Subagents Config:** `services/ai-agent-service/app/agents/developer/implementor/subagents.py`
- **Agent Entry Point:** `services/ai-agent-service/app/agents/developer/agent.py`

---

## 🎉 Next Steps

1. **Review** enhanced instructions file
2. **Test** with simple tasks
3. **Migrate** subagent configuration
4. **Update** agent entry point
5. **Test** with Sprint Task Executor
6. **Monitor** code quality improvements
7. **Iterate** based on feedback

---

**Status:** ✅ Enhanced instructions created, ready for integration

