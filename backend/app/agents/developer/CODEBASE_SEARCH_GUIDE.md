# 🔍 Codebase Search Tool - Ultimate Usage Guide

## 📋 Overview

**CodebaseSearchTool** là semantic search tool sử dụng vector embeddings để tìm code patterns và implementations trong project. Tool này giúp Coder Agent **KHÔNG bị hallucinate** bằng cách học từ existing code.

---

## ⚠️ **CRITICAL: When to Use vs When NOT to Use**

### ✅ **MUST USE When:**

1. **Before writing ANY new code** - Learn existing patterns
2. **Uncertain about implementation** - Find examples
3. **Don't know naming conventions** - Discover patterns
4. **Need to reuse utilities** - Find existing helpers
5. **Unsure about imports** - See how others import

### ❌ **DO NOT USE When:**

1. **You already know the exact file path** → Use `SafeFileReadTool` directly
2. **Exploring directory structure** → Use `SafeFileListTool`
3. **Reading package.json** → Use `SafeFileReadTool` (you know path)
4. **Checking if file exists** → Use `SafeFileListTool`

---

## 🎯 **Query Crafting Strategies**

### **Strategy 1: Concept-Based Queries**

**Purpose:** Understand HOW a concept is implemented

```yaml
# ❌ BAD: Too vague
query: "authentication"

# ✅ GOOD: Specific concept + context
query: "user authentication with JWT implementation"
query: "password hashing with bcrypt"
query: "protected route middleware patterns"
```

**Example Workflow:**
```python
# Coder needs to implement login
1. Search: "user authentication API route handler"
   → Find existing /api/auth patterns
2. Search: "JWT token generation in Next.js"
   → Learn how tokens are created
3. Search: "password validation with zod schema"
   → Reuse validation patterns
```

---

### **Strategy 2: Component-Type Queries**

**Purpose:** Find existing UI components to match style

```yaml
# ❌ BAD: Generic
query: "button"

# ✅ GOOD: Specific component + context
query: "shadcn button component with loading state"
query: "form input with error message display"
query: "modal dialog with confirmation action"
```

**Example Workflow:**
```python
# Coder needs to create LoginForm
1. Search: "form component with react-hook-form"
   → Learn form setup patterns
2. Search: "input field with validation error"
   → Match error display style
3. Search: "submit button with loading spinner"
   → Reuse loading patterns
```

---

### **Strategy 3: Architecture-Pattern Queries**

**Purpose:** Understand project structure and conventions

```yaml
# ❌ BAD: Too broad
query: "API routes"

# ✅ GOOD: Specific pattern + layer
query: "API route POST handler with zod validation"
query: "Next.js server action with error handling"
query: "Prisma database query in API route"
```

**Example Workflow:**
```python
# Coder needs to implement /api/users/[id]/route.ts
1. Search: "dynamic route parameter handling in Next.js"
   → Learn [id] pattern
2. Search: "GET request with database query"
   → See Prisma usage
3. Search: "error response format API route"
   → Match error handling
```

---

### **Strategy 4: Utility-Function Queries**

**Purpose:** Reuse existing helpers instead of recreating

```yaml
# ❌ BAD: Assuming existence
// Directly use: import { formatDate } from '@/lib/utils'

# ✅ GOOD: Search first
query: "date formatting utility functions"
query: "API response helper functions"
query: "error handling utilities"
```

**Example Workflow:**
```python
# Coder needs to format dates
1. Search: "date formatting with date-fns"
   → Find if date-fns is used
2. Search: "utility functions in lib folder"
   → Discover existing helpers
3. If found: Reuse existing
   If NOT found: Create new (and search for similar patterns)
```

---

### **Strategy 5: Anti-Hallucination Queries**

**Purpose:** Verify before assuming

```yaml
# Scenario: Need to access book.category
# ❌ BAD: Assume property exists
const category = book.category; // Hallucination!

# ✅ GOOD: Verify first
1. Search: "book model schema definition"
2. Search: "prisma book table columns"
3. Confirm 'category' exists in schema
4. Then write: const category = book.category;
```

**Common Verification Queries:**
```yaml
# Before accessing object properties:
query: "{ModelName} type definition"
query: "prisma {ModelName} schema"

# Before using library functions:
query: "{LibraryName} usage examples in project"
query: "how to use {FunctionName} in codebase"

# Before importing:
query: "imports from {PackageName}"
query: "{ComponentName} export location"
```

---

## 📝 **Query Examples by Task Type**

### **Task: Implement Authentication**

```yaml
# Step 1: Learn overall pattern
query: "authentication flow implementation"

# Step 2: Specific components
query: "login API route with credentials validation"
query: "JWT token creation and verification"
query: "session management in Next.js"

# Step 3: UI patterns
query: "login form component with error handling"
query: "password input field with visibility toggle"

# Step 4: Error handling
query: "authentication error responses"
query: "invalid credentials error message"
```

### **Task: Create Database Model**

```yaml
# Step 1: Learn schema patterns
query: "prisma model definition examples"
query: "database relationships in prisma schema"

# Step 2: Type generation
query: "prisma client type usage in API routes"
query: "typescript types from prisma models"

# Step 3: CRUD operations
query: "prisma create record with relations"
query: "prisma findUnique with include"
```

### **Task: Build Form Component**

```yaml
# Step 1: Form library usage
query: "react-hook-form setup with zod validation"
query: "form submission with server action"

# Step 2: Input components
query: "shadcn input component integration"
query: "form field with label and error message"

# Step 3: Validation patterns
query: "zod schema for form validation"
query: "async validation with debounce"
```

### **Task: Create API Route**

```yaml
# Step 1: Route structure
query: "Next.js API route handler structure"
query: "request body parsing with zod"

# Step 2: Database operations
query: "prisma query in API route"
query: "transaction handling with prisma"

# Step 3: Response patterns
query: "API success response format"
query: "error handling in API routes"
query: "HTTP status codes usage"
```

---

## 🚀 **Advanced Techniques**

### **Technique 1: Progressive Refinement**

Start broad → Narrow down

```python
# Round 1: Broad search
query: "user authentication"
→ Results: Too many, need narrowing

# Round 2: More specific
query: "user authentication with NextAuth"
→ Results: Still generic

# Round 3: Very specific
query: "NextAuth credentials provider with database"
→ Results: Perfect! Found exact pattern
```

### **Technique 2: Multi-Query Strategy**

Search multiple related concepts

```python
# Task: Implement protected route
queries = [
    "middleware for authentication check",
    "protected route with session verification",
    "redirect to login if unauthenticated",
]

# Combine insights from all 3 searches
```

### **Technique 3: Context-Aware Search**

Include project-specific context

```yaml
# Generic (less useful):
query: "form validation"

# Project-specific (more useful):
query: "form validation with zod in Next.js 16"
query: "server component form with server action"
```

---

## 🎨 **Query Templates**

### **Template 1: Feature Implementation**
```
"{feature} implementation in {framework}"
Example: "authentication implementation in Next.js"
```

### **Template 2: Component Pattern**
```
"{component_type} component with {feature}"
Example: "form component with async validation"
```

### **Template 3: Architecture Layer**
```
"{layer} with {technology} in {pattern}"
Example: "API route with Prisma in RESTful pattern"
```

### **Template 4: Utility Function**
```
"{function_purpose} helper function"
Example: "date formatting helper function"
```

### **Template 5: Error Handling**
```
"{error_type} error handling in {context}"
Example: "validation error handling in API routes"
```

---

## ⚡ **Performance Tips**

### **1. Limit Results Appropriately**

```python
# Most cases: top_k=5 (default)
codebase_search(query="auth patterns", top_k=5)

# Broad exploration: top_k=10
codebase_search(query="component patterns", top_k=10)

# Quick check: top_k=3
codebase_search(query="specific function usage", top_k=3)
```

### **2. Be Specific to Reduce Noise**

```yaml
# ❌ BAD: Too many irrelevant results
query: "component"  # Returns ALL components

# ✅ GOOD: Targeted results
query: "authentication component with form validation"
```

### **3. Search Before AND During Coding**

```python
# BEFORE coding (understand patterns)
search("form validation patterns")

# DURING coding (verify specific details)
search("zod email validation schema")

# AFTER error (find solutions)
search("typescript error cannot find module")
```

---

## 🐛 **Common Mistakes & Fixes**

### **Mistake 1: Not Searching Before Coding**

```python
# ❌ WRONG: Write code based on assumptions
const toast = useToast(); // Assume this hook exists

# ✅ CORRECT: Search first
1. Search: "toast notification usage in project"
2. Find: Project uses 'sonner' library
3. Then write: import { toast } from 'sonner'
```

### **Mistake 2: Vague Queries**

```python
# ❌ WRONG: Too vague
query: "validation"  # What kind? Where?

# ✅ CORRECT: Specific
query: "form field validation with zod schema"
```

### **Mistake 3: Ignoring Search Results**

```python
# ❌ WRONG: Search but ignore results
search("API error handling")
→ Results show: Use standardized ErrorResponse class
→ Agent writes: Custom error format (inconsistent!)

# ✅ CORRECT: Follow patterns from results
search("API error handling")
→ Results show: Use ErrorResponse class
→ Agent writes: return new ErrorResponse(...)
```

### **Mistake 4: Searching Too Late**

```python
# ❌ WRONG: Write code → Error → Then search
write_code("const user = book.author.profile")
→ Error: Property 'author' does not exist
→ Then search: "book model schema"

# ✅ CORRECT: Search BEFORE writing
search("book model schema")
→ Confirm: book has 'authorId', not 'author'
→ Then write: const authorId = book.authorId
```

---

## 🎓 **Best Practices Summary**

### **DO:**
1. ✅ **Search BEFORE writing any code**
2. ✅ **Use specific, context-aware queries**
3. ✅ **Search multiple related concepts**
4. ✅ **Verify properties/imports before using**
5. ✅ **Learn from search results (don't ignore)**
6. ✅ **Match existing code style/patterns**

### **DON'T:**
1. ❌ **Assume anything without verifying**
2. ❌ **Use vague, generic queries**
3. ❌ **Search when you know exact file path**
4. ❌ **Ignore search results and hallucinate**
5. ❌ **Write code without searching first**
6. ❌ **Search only after encountering errors**

---

## 📊 **Effectiveness Metrics**

### **Good Query Indicators:**

- ✅ Returns 5+ relevant results
- ✅ Results match your intent
- ✅ Find reusable code patterns
- ✅ Discover naming conventions
- ✅ Learn project structure

### **Bad Query Indicators:**

- ❌ No results found
- ❌ All results irrelevant
- ❌ Too many generic matches
- ❌ Still uncertain after reading
- ❌ Need to search again

---

## 🔧 **Integration with Workflow**

### **Planner Phase (STEP 3):**

```yaml
# Planner searches to:
1. Understand architecture: "project folder structure patterns"
2. Find dependencies: "libraries used for authentication"
3. Discover conventions: "naming conventions for API routes"
```

### **Coder Phase (STEP 2):**

```yaml
# Before EACH step:
STEP 2.1: Install dependencies
  → Search: "package installation scripts"

STEP 2.2: Implement Model
  → Search: "prisma model examples"
  
STEP 2.3: Create API Route
  → Search: "API route handler patterns"
  
STEP 2.4: Build Component
  → Search: "component structure with shadcn"
```

---

## 📝 **Quick Reference**

### **Search Workflow:**

```
1. Identify what you need to implement
2. Search: "{concept} implementation patterns"
3. Read top 3-5 results
4. Note: naming, structure, imports
5. Write code matching patterns
6. If uncertain: Search again with more specifics
```

### **Query Checklist:**

- [ ] Specific enough? (not "validation" → "zod email validation")
- [ ] Context included? (add "in Next.js" or "with Prisma")
- [ ] Actionable? (can you code from results?)
- [ ] Project-relevant? (matches tech stack?)

---

## 🎯 **Success Criteria**

**You're using Codebase Search effectively when:**

1. ✅ **Zero hallucinations** - No fake properties/imports
2. ✅ **Consistent code style** - Matches existing patterns
3. ✅ **Reusing utilities** - Not reinventing wheels
4. ✅ **Fewer errors** - Type-safe, verified code
5. ✅ **Faster implementation** - Learn from examples

---

## 📚 **Example: Complete Workflow**

### **Task: Implement User Profile Page**

```python
# === STEP 1: Understand Architecture ===
search("user profile page implementation")
search("Next.js page component patterns")

# === STEP 2: Database/Types ===
search("user model schema in prisma")
search("user type definition typescript")

# === STEP 3: API Route ===
search("GET user API route with dynamic id")
search("prisma findUnique user query")

# === STEP 4: Component ===
search("profile page component with server component")
search("user avatar component from shadcn")
search("profile form with editable fields")

# === STEP 5: Verification ===
search("typescript errors in profile component")
# Fix any issues found

# === RESULT ===
✅ Code matches project patterns
✅ No type errors
✅ Reused existing components
✅ Consistent styling
```

---

## 🚀 **Level Up Your Search Skills**

### **Beginner:**
- Search obvious concepts
- Read first result only
- Use generic queries

### **Intermediate:**
- Search specific patterns
- Compare multiple results
- Refine queries based on results

### **Advanced:**
- Multi-query strategy
- Context-aware searches
- Predictive searching (search what you'll need next)

---

**Remember:** `codebase_search` is your **anti-hallucination shield**. Use it religiously, and your code will be consistent, type-safe, and production-ready! 🛡️
