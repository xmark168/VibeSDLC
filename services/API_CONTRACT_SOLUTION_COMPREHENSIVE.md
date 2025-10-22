# 🛡️ Comprehensive Solution: API Contract Consistency for Implementor Agent

## 📋 Executive Summary

Giải pháp toàn diện để đảm bảo Implementor Agent generate code không gặp vấn đề API contract mismatch, bao gồm cả phần đã implement và các cải tiến bổ sung.

---

## ✅ Phần 1: Đã Implement (Current State)

### 1.1 Dependency File Identification ✅
```python
def _identify_dependency_files(current_file: str, created_files: list) -> list:
    """Identify which previously created files are dependencies"""
    # Logic to detect dependencies based on file patterns
    # E.g., Controllers depend on Services, Services depend on Repositories
```

**Status**: ✅ Implemented
**Location**: `execute_step.py` lines 641-705

### 1.2 Dependency Content Reading ✅
```python
def _read_dependency_file_content(file_path: str, working_dir: str) -> str | None:
    """Read content of a dependency file"""
    # Reads full content of dependency files
```

**Status**: ✅ Implemented
**Location**: `execute_step.py` lines 708-723

### 1.3 Enhanced Context Building ✅
```python
# In _build_implementation_context()
if dependency_files:
    context += "📚 DEPENDENCY FILES (API CONTRACT REFERENCE)\n"
    context += "⚠️ CRITICAL: Use EXACT method names, return types...\n"
    
    for dep_file in dependency_files:
        dep_content = _read_dependency_file_content(dep_file, state.codebase_path)
        context += f"📄 File: {dep_file}\n"
        context += f"```\n{dep_content}\n```\n"
```

**Status**: ✅ Implemented
**Location**: `execute_step.py` lines 615-629

### 1.4 Prompt Instructions ✅
```
🔗 API CONTRACT CONSISTENCY (CRITICAL - HIGHEST PRIORITY):

1. DEPENDENCY COORDINATION:
   - If DEPENDENCY FILES are provided, they are the SOURCE OF TRUTH
   - Use EXACT method names from dependency classes
   - Match EXACT return types from dependency methods
   - NEVER assume method names - check dependency files first
```

**Status**: ✅ Implemented
**Location**: `prompts.py` lines 64-96

---

## 🎯 Phần 2: Cải Tiến Bổ Sung (Proposed Enhancements)

### 2.1 Runtime API Contract Validation 🆕

**Problem**: Hiện tại chỉ pass context cho LLM, không validate generated code.

**Solution**: Add post-generation validation

```python
def _validate_api_contract(generated_code: str, dependency_files: list, working_dir: str) -> dict:
    """
    Validate API contract consistency in generated code.
    
    Returns:
        dict: {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str]
        }
    """
    import re
    
    errors = []
    warnings = []
    
    # 1. Extract method calls from generated code
    # Pattern for JS: serviceInstance.methodName()
    # Pattern for Python: service_instance.method_name()
    
    js_method_calls = re.findall(r'(\w+Service|\w+Repository)\.(\w+)\(', generated_code)
    py_method_calls = re.findall(r'(\w+_service|\w+_repository)\.(\w+)\(', generated_code)
    
    all_calls = js_method_calls + py_method_calls
    
    # 2. For each dependency file, extract available methods
    available_methods = {}
    for dep_file in dependency_files:
        dep_content = _read_dependency_file_content(dep_file, working_dir)
        if dep_content:
            # Extract class name and methods
            class_name = _extract_class_name(dep_file)
            methods = _extract_methods(dep_content)
            available_methods[class_name] = methods
    
    # 3. Validate each method call
    for service_name, method_name in all_calls:
        class_key = _normalize_class_name(service_name)
        if class_key in available_methods:
            if method_name not in available_methods[class_key]:
                errors.append(
                    f"❌ Method '{method_name}' not found in {class_key}. "
                    f"Available methods: {', '.join(available_methods[class_key])}"
                )
    
    # 4. Check return type destructuring
    # Pattern: const { token, user } = await authService.method()
    destructuring_patterns = re.findall(
        r'const\s*\{([^}]+)\}\s*=\s*await\s*(\w+)\.(\w+)\(',
        generated_code
    )
    
    for destructured_props, service, method in destructuring_patterns:
        # Validate that service method returns these properties
        actual_return = _get_method_return_type(service, method, available_methods)
        expected_props = [p.strip() for p in destructured_props.split(',')]
        
        for prop in expected_props:
            if prop not in actual_return:
                errors.append(
                    f"❌ Property '{prop}' not in return type of {service}.{method}(). "
                    f"Actual return: {actual_return}"
                )
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def _extract_methods(file_content: str) -> list:
    """Extract method names from class definition."""
    methods = []
    
    # JavaScript/TypeScript patterns
    js_patterns = [
        r'async\s+(\w+)\s*\([^)]*\)',  # async methodName()
        r'(\w+)\s*\([^)]*\)\s*{',       # methodName() {
    ]
    
    # Python patterns
    py_patterns = [
        r'def\s+(\w+)\s*\([^)]*\)',     # def method_name()
        r'async\s+def\s+(\w+)\s*\([^)]*\)',  # async def method_name()
    ]
    
    for pattern in js_patterns + py_patterns:
        methods.extend(re.findall(pattern, file_content))
    
    return list(set(methods))  # Remove duplicates
```

### 2.2 Auto-Fix Capability 🆕

**Problem**: Khi phát hiện API mismatch, cần fix tự động.

**Solution**: Implement auto-correction

```python
def _auto_fix_api_contract_issues(
    generated_code: str, 
    validation_result: dict,
    dependency_files: list,
    working_dir: str
) -> str:
    """
    Automatically fix API contract issues in generated code.
    
    Args:
        generated_code: The generated code with issues
        validation_result: Validation results with errors
        dependency_files: List of dependency files
        working_dir: Working directory
        
    Returns:
        str: Fixed code
    """
    fixed_code = generated_code
    
    for error in validation_result["errors"]:
        if "Method" in error and "not found" in error:
            # Extract method mismatch details
            wrong_method = _extract_wrong_method(error)
            correct_methods = _extract_available_methods(error)
            
            if correct_methods:
                # Use LLM to suggest best match
                best_match = _find_best_method_match(wrong_method, correct_methods)
                
                # Replace wrong method with correct one
                fixed_code = fixed_code.replace(
                    f".{wrong_method}(",
                    f".{best_match}("
                )
                
                print(f"🔧 Auto-fixed: {wrong_method} → {best_match}")
        
        elif "Property" in error and "not in return type" in error:
            # Fix destructuring issues
            wrong_props = _extract_wrong_properties(error)
            actual_return = _extract_actual_return(error)
            
            # Adjust destructuring to match actual return
            fixed_code = _fix_destructuring(fixed_code, wrong_props, actual_return)
            
            print(f"🔧 Auto-fixed destructuring: {wrong_props} → {actual_return}")
    
    return fixed_code


def _find_best_method_match(wrong_method: str, available_methods: list) -> str:
    """
    Use fuzzy matching or LLM to find best method match.
    
    Examples:
    - loginUser → validateUserCredentials
    - create → createUser
    - save → saveUser
    """
    # Simple heuristic matching
    for method in available_methods:
        # Check if core functionality matches
        if "login" in wrong_method.lower() and "validate" in method.lower():
            return method
        if "create" in wrong_method.lower() and "create" in method.lower():
            return method
        if "register" in wrong_method.lower() and "register" in method.lower():
            return method
    
    # If no match found, use first available method (or throw error)
    return available_methods[0] if available_methods else wrong_method
```

### 2.3 Enhanced Context with Method Signatures 🆕

**Problem**: Context hiện tại chỉ show full file content, LLM phải tự parse.

**Solution**: Extract và highlight method signatures

```python
def _build_enhanced_dependency_context(dependency_files: list, working_dir: str) -> str:
    """
    Build enhanced context with extracted method signatures.
    """
    context = "=" * 80 + "\n"
    context += "📚 DEPENDENCY API CONTRACTS\n"
    context += "=" * 80 + "\n\n"
    
    for dep_file in dependency_files:
        dep_content = _read_dependency_file_content(dep_file, working_dir)
        if dep_content:
            class_name = _extract_class_name(dep_file)
            methods = _extract_method_signatures(dep_content)
            
            context += f"📄 {class_name} ({dep_file})\n"
            context += "Available Methods:\n"
            
            for method in methods:
                context += f"  • {method['name']}({method['params']}) → {method['return_type']}\n"
            
            context += "\n"
            
            # Also include full file for reference
            context += f"Full Implementation:\n"
            context += f"```\n{dep_content}\n```\n\n"
    
    context += "⚠️ CRITICAL RULES:\n"
    context += "1. Use ONLY methods listed above\n"
    context += "2. Match EXACT method names (case-sensitive)\n"
    context += "3. Match EXACT parameter structures\n"
    context += "4. Match EXACT return types\n"
    context += "5. NEVER invent or assume method names\n\n"
    
    return context


def _extract_method_signatures(file_content: str) -> list:
    """
    Extract detailed method signatures with parameters and return types.
    """
    signatures = []
    
    # JavaScript async methods
    js_async_pattern = r'async\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*([^{]+))?\s*{'
    matches = re.findall(js_async_pattern, file_content)
    
    for name, params, return_type in matches:
        signatures.append({
            "name": name,
            "params": params.strip() or "none",
            "return_type": return_type.strip() if return_type else "Promise<any>"
        })
    
    # Python methods
    py_pattern = r'(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*([^:]+))?:'
    matches = re.findall(py_pattern, file_content)
    
    for name, params, return_type in matches:
        # Clean up params (remove self)
        params_clean = params.replace('self,', '').replace('self', '').strip()
        signatures.append({
            "name": name,
            "params": params_clean or "none",
            "return_type": return_type.strip() if return_type else "Any"
        })
    
    return signatures
```

### 2.4 Pre-Generation Contract Mapping 🆕

**Problem**: LLM generate code rồi mới validate, tốn token nếu phải regenerate.

**Solution**: Build contract map trước khi generate

```python
def _build_api_contract_map(state: ImplementorState) -> dict:
    """
    Build a complete API contract map before generation.
    
    Returns:
        dict: {
            "controllers": {
                "authController": {
                    "depends_on": ["authService"],
                    "available_services": {
                        "authService": ["registerUser", "validateUserCredentials"]
                    }
                }
            },
            "services": {
                "authService": {
                    "depends_on": ["userRepository"],
                    "available_repositories": {
                        "userRepository": ["findByEmail", "createUser", "updateUser"]
                    }
                }
            }
        }
    """
    contract_map = {
        "controllers": {},
        "services": {},
        "repositories": {},
        "models": {}
    }
    
    # Build map from all created files
    for file_path in state.files_created:
        file_type = _identify_file_type(file_path)  # controller, service, etc.
        file_name = _extract_file_name(file_path)
        
        if file_type:
            dependencies = _identify_dependency_files(file_path, state.files_created)
            
            contract_map[file_type][file_name] = {
                "depends_on": dependencies,
                "available_methods": {}
            }
            
            # Extract available methods from each dependency
            for dep in dependencies:
                dep_content = _read_dependency_file_content(dep, state.codebase_path)
                if dep_content:
                    dep_name = _extract_file_name(dep)
                    methods = _extract_methods(dep_content)
                    contract_map[file_type][file_name]["available_methods"][dep_name] = methods
    
    return contract_map
```

### 2.5 Integration into Execute Flow 🆕

**Updated execute_step.py flow:**

```python
def execute_step(state: ImplementorState) -> ImplementorState:
    """Execute current step with API contract validation."""
    
    # ... existing code ...
    
    for file_info in files_affected:
        file_path = file_info.get("path", "")
        
        # 1. Build enhanced context with contracts
        context = _build_implementation_context(
            file_path=file_path,
            sub_step=current_sub_step,
            tech_stack=state.tech_stack,
            project_type=state.project_type,
            codebase_structure=state.codebase_structure,
            created_files=state.files_created,
            file_changes=state.file_changes,
            codebase_path=state.codebase_path,
        )
        
        # 2. Build contract map (NEW)
        contract_map = _build_api_contract_map(state)
        context += f"\n\n📊 API CONTRACT MAP:\n```json\n{json.dumps(contract_map, indent=2)}\n```\n"
        
        # 3. Generate code
        generated_code = _generate_code_with_llm(context, file_path, llm)
        
        # 4. Validate API contract (NEW)
        dependency_files = _identify_dependency_files(file_path, state.files_created)
        validation_result = _validate_api_contract(
            generated_code, 
            dependency_files, 
            state.codebase_path
        )
        
        # 5. Auto-fix if needed (NEW)
        if not validation_result["valid"]:
            print(f"⚠️ API contract issues detected: {len(validation_result['errors'])} errors")
            
            # Try auto-fix
            fixed_code = _auto_fix_api_contract_issues(
                generated_code,
                validation_result,
                dependency_files,
                state.codebase_path
            )
            
            # Re-validate
            re_validation = _validate_api_contract(
                fixed_code,
                dependency_files,
                state.codebase_path
            )
            
            if re_validation["valid"]:
                print("✅ API contract issues auto-fixed successfully!")
                generated_code = fixed_code
            else:
                # If auto-fix fails, regenerate with more explicit instructions
                print("🔄 Auto-fix failed, regenerating with explicit contract requirements...")
                
                enhanced_context = context + "\n\n❌ PREVIOUS GENERATION HAD ERRORS:\n"
                for error in validation_result["errors"]:
                    enhanced_context += f"  - {error}\n"
                enhanced_context += "\n⚠️ MUST FIX THESE ERRORS IN NEW GENERATION\n"
                
                generated_code = _generate_code_with_llm(enhanced_context, file_path, llm)
        
        # 6. Implement file
        success = implement_single_file(
            file_path=file_path,
            file_content=generated_code,
            working_dir=state.codebase_path,
            action_type=action_type
        )
        
        # ... rest of existing code ...
```

---

## 📊 Phần 3: Testing & Validation

### 3.1 Unit Tests for Contract Validation

```python
# test_api_contract_validation.py

def test_validate_api_contract_method_mismatch():
    """Test detection of method name mismatches."""
    
    generated_code = '''
    async loginUser(req, res) {
        const { token, user } = await authService.loginUser({ email, password });
    }
    '''
    
    dependency_content = '''
    class AuthService {
        async validateUserCredentials(email, password) {
            return { token };
        }
    }
    '''
    
    validation = _validate_api_contract(generated_code, ["authService.js"], "/test")
    
    assert not validation["valid"]
    assert any("loginUser" in error for error in validation["errors"])
    assert any("validateUserCredentials" in error for error in validation["errors"])


def test_auto_fix_method_name():
    """Test auto-fixing of method names."""
    
    generated_code = "const result = await userRepository.create(userData);"
    validation_errors = ["Method 'create' not found. Available: createUser, findByEmail"]
    
    fixed_code = _auto_fix_api_contract_issues(generated_code, {"errors": validation_errors}, [], "/")
    
    assert "userRepository.createUser(userData)" in fixed_code
    assert "userRepository.create(userData)" not in fixed_code
```

### 3.2 Integration Tests

```python
def test_full_flow_with_contract_validation():
    """Test complete flow with API contract validation."""
    
    state = ImplementorState(
        task_id="TASK-001",
        tech_stack="nodejs",
        files_created=[
            "src/repositories/userRepository.js",  # Has createUser()
            "src/services/authService.js",          # Has validateUserCredentials()
        ]
    )
    
    # Execute step that creates authController.js
    state = execute_step(state)
    
    # Verify no API contract mismatches
    controller_content = read_file("src/controllers/authController.js")
    
    # Should call validateUserCredentials, not loginUser
    assert "authService.validateUserCredentials" in controller_content
    assert "authService.loginUser" not in controller_content
    
    # Should call createUser, not create or save
    assert "userRepository.createUser" in controller_content
    assert "userRepository.create" not in controller_content
```

---

## 🚀 Phần 4: Implementation Roadmap

### Phase 1: Quick Wins (1-2 days)
1. ✅ Dependency identification (DONE)
2. ✅ Context enhancement (DONE)
3. ✅ Prompt improvements (DONE)
4. 🆕 Basic validation function

### Phase 2: Core Features (3-5 days)
1. 🆕 Full API contract validation
2. 🆕 Auto-fix capability
3. 🆕 Enhanced context with signatures
4. 🆕 Contract mapping

### Phase 3: Advanced Features (1 week)
1. 🆕 Machine learning for method matching
2. 🆕 Historical pattern learning
3. 🆕 Cross-project contract templates
4. 🆕 Real-time contract monitoring

---

## 📈 Expected Results

### Before Implementation
- ❌ 3+ API contract mismatches per project
- ❌ Runtime errors from method not found
- ❌ Manual debugging required
- ❌ 30-60 minutes to fix issues

### After Implementation
- ✅ 0 API contract mismatches
- ✅ All methods validated before implementation
- ✅ Auto-fix for common issues
- ✅ < 1 minute to detect and fix

---

## 🎯 Conclusion

### Current Status
- ✅ Basic dependency tracking implemented
- ✅ Context enhancement with dependency files
- ✅ Prompt instructions for API consistency

### Needed Improvements
- 🆕 Runtime validation of generated code
- 🆕 Auto-fix capability for common issues
- 🆕 Pre-generation contract mapping
- 🆕 Enhanced context with method signatures

### Impact
- **Reduce API mismatches**: From 3+ to 0 per project
- **Improve code quality**: Consistent API contracts
- **Save debugging time**: From hours to minutes
- **Increase reliability**: No runtime surprises

---

**Version**: 2.0.0  
**Author**: AI Development Team  
**Date**: 2025-01-22  
**Status**: 🟡 Partially Implemented (Core features done, enhancements needed)
