# 🎯 Planner Tech Stack Fix Summary

## 📋 Problem Identified

**Issue:** Planner was generating file paths with wrong extensions for tech stack.

**Specific Case:**
- Project: Node.js/Express 
- Expected: `.js` migration files (e.g., `migrations/add_new_feature_tables.js`)
- Actual: `.py` migration files (e.g., `migrations/add_new_feature_tables.py`)

## 🔍 Root Cause Analysis

### ❌ Issues Found:

1. **PlannerState missing tech_stack field**
   - Only ImplementorState had tech_stack field
   - Planner had no way to track detected tech stack

2. **Planner không detect tech stack**
   - Only Implementor detected tech stack in initialize.py
   - Planner generated file paths BEFORE tech stack detection

3. **Planner prompts có Python bias**
   - Hardcoded examples: `"exact/file/path.py"`
   - No explicit file extension requirements
   - No tech stack → file extension mapping

4. **Workflow timing issue**
   ```
   Current (problematic):
   Planner → Generate file paths (.py bias) → Implementor → Detect tech stack
   
   Fixed:
   Planner → Detect tech stack → Generate correct file paths → Implementor
   ```

## 🔧 Fixes Applied

### 1. Added tech_stack field to PlannerState

**File:** `services/ai-agent-service/app/agents/developer/planner/state.py`

```python
class PlannerState(BaseModel):
    # Input
    task_description: str = ""
    codebase_context: str = ""
    codebase_path: str = ""
    
    # Tech stack detection
    tech_stack: str = ""  # e.g., "nodejs", "fastapi", "react-vite"
```

### 2. Added tech stack detection to Planner initialize

**File:** `services/ai-agent-service/app/agents/developer/planner/nodes/initialize.py`

```python
def initialize(state: PlannerState) -> PlannerState:
    # Detect tech stack from codebase if path is provided
    if state.codebase_path:
        tech_stack = detect_tech_stack(state.codebase_path)
        state.tech_stack = tech_stack
        print(f"🔍 Detected tech stack: {tech_stack}")
    else:
        print("⚠️ No codebase path provided - tech stack detection skipped")

def detect_tech_stack(codebase_path: str) -> str:
    """
    Detect tech stack from codebase path.
    Same logic as Implementor's detection.
    """
    # Try detect_stack_tool first, then fallback to file-based detection
    # Node.js: package.json + express → "nodejs"
    # Python: .py files + requirements.txt → "fastapi"
```

### 3. Enhanced CODEBASE_ANALYSIS_PROMPT

**File:** `services/ai-agent-service/app/templates/prompts/developer/planner.py`

```
## CRITICAL FILE PATH REQUIREMENTS:
- ALWAYS match file extensions to the detected tech stack
- Node.js/Express projects: Use .js files (NOT .py files)
- Python/FastAPI projects: Use .py files  
- React/Next.js projects: Use .js/.jsx/.ts/.tsx files
- Database migrations: Match the tech stack's migration format
  * Node.js: Use Sequelize/Knex/Prisma migration files (.js)
  * Python: Use Alembic migration files (.py)
- NEVER generate .py files for Node.js projects
- NEVER generate .js files for Python projects

## Tech Stack:
{tech_stack}
```

### 4. Enhanced GENERATE_PLAN_PROMPT

```
## CRITICAL FILE PATH REQUIREMENTS:
- ALWAYS match file extensions to the tech stack
- Node.js/Express: Use .js files for implementation, .js migration files
- Python/FastAPI: Use .py files for implementation, .py migration files  
- Database migrations: Match tech stack format
  * Node.js: migrations/YYYYMMDD_description.js (Sequelize/Knex format)
  * Python: alembic/versions/YYYYMMDD_description.py (Alembic format)
- NEVER generate .py files for Node.js projects
- NEVER generate .js files for Python projects
```

### 5. Updated prompt formatting to include tech_stack

**analyze_codebase.py:**
```python
formatted_prompt = CODEBASE_ANALYSIS_PROMPT.format(
    task_requirements=task_requirements.model_dump_json(indent=2),
    tech_stack=state.tech_stack or "unknown",
    codebase_context=codebase_context,
)
```

**generate_plan.py:**
```python
plan_prompt = f"""{GENERATE_PLAN_PROMPT}

## TASK CONTEXT

Tech Stack: {state.tech_stack or "unknown"}

Task Requirements:
{task_requirements.model_dump_json(indent=2)}
```

### 6. Fixed hardcoded examples

Changed from:
```json
"path": "exact/file/path.py"
```

To:
```json
"path": "exact/file/path.ext"
```

## 📊 Expected Behavior After Fix

### Before Fix:
```json
{
  "execution_order": [
    {
      "step": 1,
      "action": "Create database migration",
      "files": ["migrations/add_new_feature_tables.py"]  // ❌ Wrong for Node.js
    }
  ]
}
```

### After Fix:
```json
{
  "execution_order": [
    {
      "step": 1,
      "action": "Create database migration", 
      "files": ["migrations/add_new_feature_tables.js"]  // ✅ Correct for Node.js
    }
  ]
}
```

## 🎯 Impact

### Node.js/Express Projects:
- ✅ Migration files: `migrations/YYYYMMDD_description.js`
- ✅ Implementation files: `src/utils/validation.js`
- ✅ Test files: `tests/validation.test.js`

### Python/FastAPI Projects:
- ✅ Migration files: `alembic/versions/YYYYMMDD_description.py`
- ✅ Implementation files: `app/services/validation.py`
- ✅ Test files: `tests/test_validation.py`

## 🚀 Workflow Now

```
1. Planner Initialize → Detect tech stack from codebase
2. Planner Analyze Codebase → Use tech stack for file paths
3. Planner Generate Plan → Create plan with correct extensions
4. Implementor → Receive plan with correct file paths
5. Implementor → Generate code in correct language
```

## 📝 Files Modified

1. **`planner/state.py`**: Added `tech_stack` field
2. **`planner/nodes/initialize.py`**: Added tech stack detection
3. **`prompts/developer/planner.py`**: Enhanced prompts with file extension requirements
4. **`planner/nodes/analyze_codebase.py`**: Pass tech_stack to prompt
5. **`planner/nodes/generate_plan.py`**: Pass tech_stack to prompt

## 🎉 Success Criteria Met

- ✅ **Root Cause Fixed**: Planner now detects tech stack before generating file paths
- ✅ **Prompts Enhanced**: Explicit file extension requirements added
- ✅ **Consistency Achieved**: Planner and Implementor both use same tech stack detection
- ✅ **Prevention Added**: "NEVER mix languages" warnings prevent future issues

## 🔄 Integration with Previous Fix

This fix complements the previous Implementor language fix:

1. **Planner Fix**: Generate correct file paths with right extensions
2. **Implementor Fix**: Generate correct code content in right language

Together they ensure:
- ✅ **File paths** match tech stack (Planner responsibility)
- ✅ **Code content** matches tech stack (Implementor responsibility)
- ✅ **End-to-end consistency** from planning to implementation

**The Developer Agent should now generate both correct file paths AND correct code content for each tech stack!** 🎯
