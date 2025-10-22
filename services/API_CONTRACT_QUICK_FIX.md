# 🚀 Quick Fix Guide: API Contract Validation

## Giải pháp nhanh để implement ngay (1-2 giờ)

### Step 1: Add Validation Function (30 phút)

Thêm vào `execute_step.py` sau line 723:

```python
def _validate_api_contract_simple(generated_code: str, dependency_files: list, working_dir: str) -> list:
    """
    Simple validation để detect API contract mismatches.
    
    Returns:
        list: List of error messages (empty if valid)
    """
    import re
    
    errors = []
    
    # Read all dependency methods
    available_methods = {}
    for dep_file in dependency_files:
        dep_content = _read_dependency_file_content(dep_file, working_dir)
        if dep_content:
            # Extract service/repository name from file path
            if 'services/' in dep_file:
                service_name = dep_file.split('/')[-1].replace('.js', '').replace('.py', '')
                # Find all methods in the service
                methods = re.findall(r'async\s+(\w+)\s*\(', dep_content)  # JS async methods
                methods += re.findall(r'def\s+(\w+)\s*\(', dep_content)   # Python methods
                available_methods[service_name] = methods
            elif 'repositories/' in dep_file:
                repo_name = dep_file.split('/')[-1].replace('.js', '').replace('.py', '')
                methods = re.findall(r'async\s+(\w+)\s*\(', dep_content)
                methods += re.findall(r'def\s+(\w+)\s*\(', dep_content)
                available_methods[repo_name] = methods
    
    # Check method calls in generated code
    for service_name, methods in available_methods.items():
        # Find all calls to this service
        pattern = f'{service_name}\\.(\w+)\\('
        calls = re.findall(pattern, generated_code)
        
        for called_method in calls:
            if called_method not in methods:
                errors.append(
                    f"❌ Method '{service_name}.{called_method}()' not found! "
                    f"Available methods: {', '.join(methods)}"
                )
                # Suggest closest match
                for method in methods:
                    if called_method.lower() in method.lower() or method.lower() in called_method.lower():
                        errors[-1] += f" (Did you mean '{method}'?)"
                        break
    
    return errors
```

### Step 2: Integrate Validation (15 phút)

Update `execute_step.py` trong phần generate code (around line 150):

```python
# After generating code, add validation
if generated_code:
    # NEW: Validate API contracts
    dependency_files = _identify_dependency_files(file_path, state.files_created)
    if dependency_files:
        validation_errors = _validate_api_contract_simple(
            generated_code, 
            dependency_files, 
            state.codebase_path
        )
        
        if validation_errors:
            print(f"\n⚠️ API Contract Issues Detected:")
            for error in validation_errors:
                print(f"  {error}")
            
            # Add errors to context and regenerate
            enhanced_prompt = prompt + "\n\n❌ FIX THESE API CONTRACT ERRORS:\n"
            for error in validation_errors:
                enhanced_prompt += f"- {error}\n"
            enhanced_prompt += "\n⚠️ Use ONLY the methods shown as 'Available methods' above!"
            
            # Regenerate with enhanced prompt
            print("🔄 Regenerating with correct API contracts...")
            messages = [
                SystemMessage(content=enhanced_prompt),
                HumanMessage(content=f"Generate complete content for: {file_path}")
            ]
            response = llm.invoke(messages)
            generated_code = response.content
```

### Step 3: Enhance Prompt Context (15 phút)

Update `_build_implementation_context()` để highlight available methods:

```python
# In _build_implementation_context, after adding dependency files (line 628):

if dependency_files:
    # Existing code...
    for dep_file in dependency_files:
        dep_content = _read_dependency_file_content(dep_file, state.codebase_path)
        if dep_content:
            context += f"📄 File: {dep_file}\n"
            
            # NEW: Extract and highlight available methods
            import re
            methods = re.findall(r'async\s+(\w+)\s*\(', dep_content)
            methods += re.findall(r'def\s+(\w+)\s*\(', dep_content)
            
            if methods:
                context += "📌 AVAILABLE METHODS YOU CAN CALL:\n"
                for method in set(methods):  # Remove duplicates
                    context += f"   ✓ {method}()\n"
                context += "\n"
            
            context += f"```\n{dep_content}\n```\n\n"
```

### Step 4: Add Pre-Check Warning (10 phút)

Thêm warning trước khi generate mỗi file:

```python
# In execute_step.py, before calling LLM (around line 140):

# Check if this file needs to call other services
if any(keyword in file_path for keyword in ['controller', 'service', 'handler']):
    dependency_files = _identify_dependency_files(file_path, state.files_created)
    
    if dependency_files:
        print(f"\n⚠️ API Contract Check Required!")
        print(f"   File '{file_path}' depends on:")
        for dep in dependency_files:
            print(f"   - {dep}")
        print("   Will validate method calls after generation...")
```

---

## 📋 Testing Quick Fix

### Test Case 1: Controller calling Service

```python
# Generate a test controller
test_controller = """
async loginUser(req, res) {
    const { token, user } = await authService.loginUser({ email, password });
}
"""

# With authService having only validateUserCredentials()
errors = _validate_api_contract_simple(test_controller, ["services/authService.js"], "/project")

# Should detect: "Method 'authService.loginUser()' not found!"
```

### Test Case 2: Service calling Repository  

```python
# Generate a test service
test_service = """
async registerUser(userData) {
    const user = await userRepository.save(userData);
}
"""

# With userRepository having only createUser()
errors = _validate_api_contract_simple(test_service, ["repositories/userRepository.js"], "/project")

# Should detect: "Method 'userRepository.save()' not found!"
```

---

## ⏱️ Implementation Time

| Task | Time | Priority |
|------|------|----------|
| Add validation function | 30 min | High |
| Integrate into flow | 15 min | High |
| Enhance context | 15 min | Medium |
| Add warnings | 10 min | Low |
| **Total** | **70 min** | - |

---

## 🎯 Expected Immediate Impact

### Before Quick Fix
- ❌ loginUser() calls non-existent method
- ❌ save() calls non-existent method  
- ❌ Runtime errors

### After Quick Fix
- ✅ Detects mismatches before implementing
- ✅ Regenerates with correct method names
- ✅ No runtime errors

---

## 💡 Tips

1. **Start với validation đơn giản** - không cần perfect, chỉ cần detect được major issues
2. **Log all detections** - để track improvement over time
3. **Test với existing codebase** - run validation on current files để verify
4. **Iterate nhanh** - implement basic version first, enhance later

---

**Quick Fix Version**: 1.0.0  
**Implementation Effort**: Low (1-2 hours)  
**Impact**: High (Prevents runtime errors)  
**Risk**: Low (Không affect existing code)
