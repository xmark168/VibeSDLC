# Nested Subagents Guide

## Overview

The Implementor subagent has two nested subagents that handle specialized tasks during code generation. This document explains the architecture and how to use them effectively.

## Architecture

```
Developer Agent (Main DeepAgent)
└── Implementor Subagent
    ├── code_generator (nested subagent)
    │   └── Generates and modifies code files in virtual FS
    └── code_reviewer (nested subagent - internal)
        └── Performs quick quality checks on generated code
```

### Important Distinction

**Two Different Code Reviewers:**

1. **Implementor's Internal code_reviewer** (nested subagent)
   - Quick quality checks during generation
   - Lightweight review for obvious issues
   - Used by Implementor before syncing to disk
   - Defined in: `implementor/subagents.py`

2. **Main Developer Agent's code_reviewer** (top-level subagent)
   - Comprehensive security and architecture review
   - Full analysis with detailed feedback
   - Used by main Developer Agent after implementation
   - Defined in: `code_reviewer/__init__.py`

## Nested Subagent Details

### 1. code_generator Subagent

**Purpose:** Generate high-quality, production-ready code

**Capabilities:**
- Create new files with `write_file()`
- Modify existing files with `edit_file()`
- Follow existing code patterns
- Apply best practices and design patterns
- Include proper error handling and documentation

**Tools Available:**
- `write_file`: Create new files in virtual FS
- `edit_file`: Modify existing files in virtual FS
- `read_file`: Read files from virtual FS
- `ls`: List files in virtual FS

**When to Use:**
- Need to generate new code files
- Need to modify existing code
- Have clear specifications and context
- Want to delegate file writing operations

**How to Delegate:**

```python
task(
    description='''Generate user authentication endpoints:
    - POST /api/auth/login
    - POST /api/auth/register
    - GET /api/auth/me
    
    Context: FastAPI project with SQLAlchemy
    Strategy: create_new
    Target files: app/api/auth.py, app/models/user.py
    
    Requirements:
    - Use JWT tokens for authentication
    - Hash passwords with bcrypt
    - Include input validation
    - Add proper error handling
    ''',
    subagent_type="code_generator"
)
```

**What to Provide:**
1. Clear specifications of what to implement
2. Codebase context (existing patterns, dependencies)
3. Integration strategy (create_new, extend_existing, etc.)
4. Target files to create/modify
5. Specific requirements or constraints

**What You Get Back:**
- Files created/modified in virtual FS
- Summary of changes made
- Integration notes
- Testing recommendations

**Important Notes:**
- Files are created in VIRTUAL FS (memory)
- YOU must sync to disk with `sync_virtual_to_disk_tool()`
- code_generator does NOT commit or sync

### 2. code_reviewer Subagent (Internal)

**Purpose:** Quick quality checks on generated code

**Capabilities:**
- Check code quality and structure
- Identify obvious bugs or issues
- Verify best practices adherence
- Provide quick feedback

**Tools Available:**
- `read_file`: Read files from virtual FS
- `ls`: List files in virtual FS

**When to Use:**
- After code generation (before syncing to disk)
- Before committing changes
- During iteration (check fixes)
- For complex changes (validate approach)

**How to Delegate:**

```python
task(
    description='''Review the authentication endpoints:
    Files: app/api/auth.py, app/models/user.py
    
    Check for:
    - Security vulnerabilities (password handling, JWT)
    - Input validation on all endpoints
    - Proper error handling
    - Code quality and maintainability
    - SQL injection prevention
    ''',
    subagent_type="code_reviewer"
)
```

**Review Criteria:**
1. **Code Quality**: Readability, maintainability, naming
2. **Basic Security**: Input validation, error handling, obvious vulnerabilities
3. **Performance**: Algorithm efficiency, resource management
4. **Best Practices**: Language conventions, design patterns
5. **Integration**: Compatibility with existing code

**What You Get Back:**
- Overall assessment
- Issues found (categorized by severity)
- Specific recommendations
- Approval status (ready/needs fixes/requires changes)

**Important Notes:**
- This is NOT a comprehensive security audit
- For full review, main Developer Agent uses its own code_reviewer
- Focus is on quick quality checks during generation

## Complete Workflow Example

### Scenario: Add User Profile Feature

```python
# 1. Planning Phase
write_todos([
    "Analyze existing user model and API structure",
    "Generate profile endpoints (GET, PUT)",
    "Add profile model with fields",
    "Review and test implementation"
])

# 2. Analysis Phase
codebase_context = load_codebase_tool(
    working_directory=state["working_directory"]
)

# 3. Select Integration Strategy
strategy = select_integration_strategy_tool(
    task_description="Add user profile endpoints",
    codebase_context=codebase_context
)
# Returns: "create_new" - create new profile module

# 4. Delegate to code_generator
task(
    description='''Generate user profile feature:
    
    Endpoints:
    - GET /api/profiles/me - Get current user profile
    - PUT /api/profiles/me - Update profile
    
    Model:
    - Profile model with: full_name, bio, avatar_url, user_id (FK)
    
    Context:
    - FastAPI project with SQLAlchemy
    - Existing User model in app/models/user.py
    - Existing auth with JWT in app/api/auth.py
    
    Strategy: create_new
    Target files:
    - app/api/profile.py (new)
    - app/models/profile.py (new)
    - app/main.py (modify to include router)
    
    Requirements:
    - Only authenticated users can access
    - Users can only view/edit their own profile
    - Validate input (max lengths, required fields)
    - Return 404 if profile doesn't exist
    - Include proper error handling
    ''',
    subagent_type="code_generator"
)

# 5. Review Generated Code
task(
    description='''Review the profile implementation:
    Files: app/api/profile.py, app/models/profile.py, app/main.py
    
    Focus on:
    - Authorization: Users can only access own profile
    - Input validation: Check max lengths, required fields
    - Error handling: Proper HTTP status codes
    - Security: No SQL injection, proper auth checks
    - Code quality: Follows existing patterns
    ''',
    subagent_type="code_reviewer"
)

# 6. Handle Review Feedback
# If issues found, delegate back to code_generator with fixes
# Example:
if review_found_issues:
    task(
        description='''Fix issues in profile implementation:
        
        Issues to fix:
        - Add max length validation on bio field (500 chars)
        - Add authorization check in PUT endpoint
        - Improve error message for missing profile
        
        Files: app/api/profile.py
        ''',
        subagent_type="code_generator"
    )

# 7. Sync to Disk (CRITICAL)
sync_virtual_to_disk_tool(working_directory=state["working_directory"])

# 8. Commit Changes
commit_changes_tool(
    working_directory=state["working_directory"],
    commit_message="Add user profile endpoints with CRUD operations"
)

# 9. Update Todo Status
# Mark todo as completed
```

## Best Practices

### 1. Provide Clear Context

**Good:**
```python
task(
    description='''Generate authentication middleware:
    
    Context:
    - FastAPI project
    - JWT tokens stored in Authorization header
    - User model has id, email, hashed_password fields
    - Existing get_current_user dependency in app/api/auth.py
    
    Requirements:
    - Verify JWT token
    - Extract user from token
    - Return 401 if invalid
    - Cache user lookup for performance
    ''',
    subagent_type="code_generator"
)
```

**Bad:**
```python
task(
    description="Add auth middleware",
    subagent_type="code_generator"
)
```

### 2. Review Before Syncing

Always review generated code before syncing to disk:

```python
# Generate
task(description="...", subagent_type="code_generator")

# Review (RECOMMENDED)
task(description="Review generated code...", subagent_type="code_reviewer")

# Sync only if review passes
sync_virtual_to_disk_tool(working_directory=state["working_directory"])
```

### 3. Iterate if Needed

Don't hesitate to regenerate if quality is insufficient:

```python
# First attempt
task(description="Generate feature X", subagent_type="code_generator")

# Review finds issues
task(description="Review feature X", subagent_type="code_reviewer")

# Fix issues
task(
    description="Fix issues: [list specific issues]",
    subagent_type="code_generator"
)

# Review again
task(description="Review fixes", subagent_type="code_reviewer")
```

### 4. Be Specific About Requirements

Include all important requirements in the description:

```python
task(
    description='''Generate user registration endpoint:
    
    Requirements:
    - Email validation (valid format)
    - Password strength (min 8 chars, uppercase, lowercase, number)
    - Check if email already exists (return 409)
    - Hash password with bcrypt
    - Create user in database
    - Return JWT token
    - Send welcome email (async task)
    
    Error handling:
    - 400 for invalid input
    - 409 for duplicate email
    - 500 for server errors
    ''',
    subagent_type="code_generator"
)
```

## Troubleshooting

### Issue: Generated code doesn't follow existing patterns

**Solution:** Provide more codebase context

```python
# Load codebase first
context = load_codebase_tool(working_directory=state["working_directory"])

# Include relevant context in description
task(
    description=f'''Generate feature X:
    
    Existing patterns to follow:
    {context["patterns"]}
    
    Similar implementations:
    {context["similar_code"]}
    ''',
    subagent_type="code_generator"
)
```

### Issue: Review finds many issues

**Solution:** Provide clearer specifications and requirements

```python
# Be more specific about requirements
task(
    description='''Generate feature with these SPECIFIC requirements:
    1. [Requirement 1 with details]
    2. [Requirement 2 with details]
    3. [Requirement 3 with details]
    
    Security requirements:
    - [Security requirement 1]
    - [Security requirement 2]
    
    Error handling:
    - [Error case 1]: Return [status code]
    - [Error case 2]: Return [status code]
    ''',
    subagent_type="code_generator"
)
```

### Issue: Files not appearing on disk

**Solution:** Remember to sync virtual FS to disk

```python
# After generation
task(description="...", subagent_type="code_generator")

# MUST sync before commit
sync_virtual_to_disk_tool(working_directory=state["working_directory"])

# Now commit
commit_changes_tool(...)
```

## Summary

- **code_generator**: Generates code in virtual FS
- **code_reviewer** (internal): Quick quality checks
- Always provide clear context and specifications
- Review before syncing to disk
- Iterate if needed to improve quality
- Sync to disk before committing

For more details, see:
- `implementor/instructions.py` - Full Implementor instructions with nested subagent guidelines
- `implementor/subagents.py` - Subagent configurations
- `developer/README.md` - Overall architecture documentation

