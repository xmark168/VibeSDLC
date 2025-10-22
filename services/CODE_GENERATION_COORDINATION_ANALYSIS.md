# Code Generation Coordination Analysis Report

## 🎯 Problem Statement

**Issue**: LLM generate code không có coordination giữa các files trong Express.js layered architecture, dẫn đến API contract mismatches.

**Specific Problems Identified**:

### Problem 1: Return Type Mismatch (Service → Controller)

**File**: `src/services/authService.js` (lines 36-43)
```javascript
// Service returns {user, token}
return {
  user: {
    id: newUser.id,
    name: newUser.name,
    email: newUser.email,
  },
  token,
};
```

**File**: `src/controllers/authController.js` (line 15)
```javascript
// ❌ Controller expects only user object
const user = await AuthService.registerUser({ name, email, password });
return res.status(201).json({ message: 'User registered successfully', user });
```

**Expected**:
```javascript
// ✅ Should destructure {user, token}
const { user, token } = await AuthService.registerUser({ name, email, password });
return res.status(201).json({ message: 'User registered successfully', user, token });
```

### Problem 2: Method Name Mismatch (Repository → Service)

**File**: `src/repositories/userRepository.js` (line 24)
```javascript
// Repository method is named createUser
async createUser(userData) {
  // ...
}
```

**File**: `src/services/authService.js` (line 23)
```javascript
// ❌ Service calls 'create' (doesn't exist)
const newUser = await userRepository.create({
  name: userData.name,
  email: userData.email,
  password: hashedPassword,
});
```

**Expected**:
```javascript
// ✅ Should call createUser
const newUser = await userRepository.createUser({
  name: userData.name,
  email: userData.email,
  password: hashedPassword,
});
```

---

## 🔍 Root Cause Analysis

### Investigation Results

#### 1. Code Generation Flow

**File**: `execute_step.py` (lines 198-350)

**Current Flow**:
```
FOR EACH file in files_affected:
  1. Build context for THIS file only
  2. Generate code for THIS file
  3. Implement THIS file immediately
  4. Move to NEXT file
```

**Problem**: Each file is generated **independently** without context about previously generated files.

#### 2. Context Building Function

**File**: `execute_step.py` (lines 577-622)

**Current Implementation**:
```python
def _build_file_context(state, sub_step, file_path, is_creation, existing_content=""):
    context = f"Task: {state.task_description}\n"
    context += f"Tech Stack: {state.tech_stack}\n"
    context += f"File: {file_path}\n"
    
    # ❌ ONLY lists file NAMES, not CONTENT
    if state.files_created:
        context += "Files already created in previous sub-steps:\n"
        for created_file in state.files_created[-5:]:
            context += f"- {created_file}\n"  # ❌ Just file path, no API details
```

**Problem**: 
- Only passes **file paths** of previously created files
- Does NOT pass **file content** or **API signatures**
- LLM cannot see what methods/functions were defined in previous files

#### 3. Prompt Instructions

**File**: `utils/prompts.py` (lines 8-124)

**Current Prompt** (BACKEND_FILE_CREATION_PROMPT):
```python
BACKEND BEST PRACTICES:

1. API DESIGN PATTERNS:
   - Follow REST conventions
   - Use appropriate HTTP status codes
   ...

2. DATABASE OPERATIONS:
   - Use ORM best practices
   ...
```

**Problem**:
- Generic best practices only
- NO instructions about **maintaining API contract consistency**
- NO instructions about **checking dependencies' API signatures**
- NO instructions about **coordinating with previously generated files**

---

## 📊 Current vs Expected Behavior

### Current Behavior

**Step 1: Generate Model** (`src/models/User.js`)
```
Context:
- Task: Add user authentication
- Tech Stack: nodejs
- File: src/models/User.js
- Files already created: []
```

**Step 2: Generate Repository** (`src/repositories/userRepository.js`)
```
Context:
- Task: Add user authentication
- Tech Stack: nodejs
- File: src/repositories/userRepository.js
- Files already created: ['src/models/User.js']  ❌ Just path, no content
```

**Result**: Repository generates `createUser()` method without knowing Model structure.

**Step 3: Generate Service** (`src/services/authService.js`)
```
Context:
- Task: Add user authentication
- Tech Stack: nodejs
- File: src/services/authService.js
- Files already created: ['src/models/User.js', 'src/repositories/userRepository.js']  ❌ Just paths
```

**Result**: Service calls `userRepository.create()` instead of `createUser()` because it doesn't know the actual method name.

### Expected Behavior

**Step 1: Generate Model** (same as current)

**Step 2: Generate Repository**
```
Context:
- Task: Add user authentication
- Tech Stack: nodejs
- File: src/repositories/userRepository.js
- Files already created: ['src/models/User.js']

✅ DEPENDENCY CONTEXT:
File: src/models/User.js
```javascript
const mongoose = require('mongoose');
const userSchema = new mongoose.Schema({
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
});
module.exports = mongoose.model('User', userSchema);
```
```

**Result**: Repository knows Model structure and generates appropriate methods.

**Step 3: Generate Service**
```
Context:
- Task: Add user authentication
- Tech Stack: nodejs
- File: src/services/authService.js

✅ DEPENDENCY CONTEXT:
File: src/repositories/userRepository.js
```javascript
class UserRepository {
  async findByEmail(email) { ... }
  async createUser(userData) { ... }  ✅ LLM sees method name
}
module.exports = new UserRepository();
```
```

**Result**: Service calls correct method `userRepository.createUser()`.

---

## 🛠️ Solution Design

### Fix 1: Enhanced Context Building

**Modify**: `execute_step.py` - `_build_file_context()` function

**Changes**:
1. Read content of dependency files (not just paths)
2. Extract API signatures (classes, methods, return types)
3. Pass dependency content to LLM

**Implementation**:
```python
def _build_file_context(state, sub_step, file_path, is_creation, existing_content=""):
    # ... existing code ...
    
    # ✅ NEW: Add dependency files content
    dependency_files = _identify_dependency_files(file_path, state.files_created)
    if dependency_files:
        context += "\n📚 DEPENDENCY FILES (for API contract reference):\n\n"
        for dep_file in dependency_files:
            dep_content = _read_file_content(dep_file, state.codebase_path)
            if dep_content:
                context += f"File: {dep_file}\n"
                context += f"```\n{dep_content}\n```\n\n"
    
    return context
```

### Fix 2: Enhanced Prompts

**Modify**: `utils/prompts.py` - Add API contract instructions

**Changes**:
1. Add explicit instructions about API contract consistency
2. Add instructions to check dependency files
3. Add validation requirements

**Implementation**:
```python
BACKEND_FILE_CREATION_PROMPT = """
...

🔗 API CONTRACT CONSISTENCY (CRITICAL):

1. DEPENDENCY COORDINATION:
   - ALWAYS check dependency files provided in context
   - Use EXACT method names from dependency classes
   - Match EXACT return types from dependency methods
   - Match EXACT parameter structures from dependency signatures

2. LAYERED ARCHITECTURE CONTRACTS:
   - Repository methods: Return domain objects or null
   - Service methods: Return {data, metadata} or throw errors
   - Controller methods: Return HTTP responses with proper status codes
   
3. METHOD NAMING CONSISTENCY:
   - If Repository has createUser(), Service MUST call createUser()
   - If Service returns {user, token}, Controller MUST destructure {user, token}
   - NEVER assume method names - use what's defined in dependencies

4. VALIDATION REQUIREMENTS:
   - Before calling a method, verify it exists in dependency file
   - Before using a return value, verify its structure from dependency
   - If dependency file is provided, it is the SOURCE OF TRUTH

...
"""
```

### Fix 3: Dependency Identification

**Add**: Helper function to identify dependencies

**Implementation**:
```python
def _identify_dependency_files(current_file: str, created_files: list) -> list:
    """
    Identify which previously created files are dependencies of current file.
    
    Express.js layered architecture:
    - Controllers depend on Services
    - Services depend on Repositories
    - Repositories depend on Models
    """
    dependencies = []
    
    if "controllers" in current_file:
        # Controllers depend on Services
        service_name = current_file.replace("controllers", "services").replace("Controller", "Service")
        if service_name in created_files:
            dependencies.append(service_name)
    
    elif "services" in current_file:
        # Services depend on Repositories
        repo_name = current_file.replace("services", "repositories").replace("Service", "Repository")
        if repo_name in created_files:
            dependencies.append(repo_name)
    
    elif "repositories" in current_file:
        # Repositories depend on Models
        model_name = current_file.replace("repositories", "models").replace("Repository", "")
        if model_name in created_files:
            dependencies.append(model_name)
    
    return dependencies
```

---

## 📝 Implementation Plan

### Phase 1: Core Fixes (High Priority)

1. ✅ **Add dependency identification logic**
   - File: `execute_step.py`
   - Function: `_identify_dependency_files()`
   - Lines: Add after line 622

2. ✅ **Add file content reading helper**
   - File: `execute_step.py`
   - Function: `_read_dependency_file_content()`
   - Lines: Add after dependency identification

3. ✅ **Enhance context building**
   - File: `execute_step.py`
   - Function: `_build_file_context()`
   - Lines: 577-622 (modify)

4. ✅ **Update prompts with API contract instructions**
   - File: `utils/prompts.py`
   - Section: BACKEND_FILE_CREATION_PROMPT
   - Lines: 8-124 (add new section)

### Phase 2: Testing & Validation

5. ✅ **Create test script**
   - Generate sample feature with full layers
   - Verify API contracts match

6. ✅ **Validate generated code**
   - Check method names match
   - Check return types match
   - Check parameter structures match

---

## 🎯 Expected Outcomes

After implementing fixes:

1. ✅ **Controllers will use correct Service return types**
   ```javascript
   const { user, token } = await AuthService.registerUser(...);
   ```

2. ✅ **Services will call correct Repository methods**
   ```javascript
   const newUser = await userRepository.createUser(...);
   ```

3. ✅ **API contracts will be consistent across layers**
   - Method names match
   - Return types match
   - Parameter structures match

4. ✅ **Generated code will run without errors**
   - No "method not found" errors
   - No "undefined property" errors
   - Proper data flow through layers

---

**Status**: Analysis Complete - Ready for Implementation
**Priority**: HIGH - Affects code quality and runtime errors
**Estimated Effort**: 2-3 hours

