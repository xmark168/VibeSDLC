# Code Implementer - Flow Mô Tả Chi Tiết

## Tổng Quan
Code Implementer là sub-agent thứ 2 trong Developer Agent workflow, nhận implementation plan từ Task Analyzer và tạo ra production-ready code hoàn chỉnh để chuyển cho Test Generator.

---

## Flow Chi Tiết

### 🎯 **Bước 1: Nhận và Phân Tích Plan**

#### **Input**: Implementation Plan từ Task Analyzer
- **Requirements**: Danh sách yêu cầu chức năng và phi chức năng
- **Technical Constraints**: Ràng buộc kỹ thuật và môi trường
- **Dependencies**: Các thư viện và service phụ thuộc
- **Architecture Guidelines**: Hướng dẫn kiến trúc và design patterns
- **Selected Tech Stack (do người dùng chọn trước)**: Ngôn ngữ, framework, package manager, test framework, DB/ORM, CI/CD preferences

#### **Quá Trình Phân Tích**:
1. **Đọc và hiểu plan**: Phân tích từng component trong plan
2. **Xác định scope**: Xác định phạm vi công việc cần implement
3. **Lập danh sách patterns**: Xác định design patterns nào sẽ sử dụng
4. **Đánh giá complexity**: Ước tính độ phức tạp của từng phần
5. **Lên timeline**: Sắp xếp thứ tự ưu tiên implement

---

### 💻 **Bước 2: Generate Main Code (Tech Stack-Aware & Incremental)**

**2.0 Tech Stack Analysis & Project Context (Phân Tích Tech Stack & Context Dự Án)**

**2.0.1 Analyze Existing Codebase (Phân Tích Codebase Hiện Có)**
- **Detect Project Type**: Xác định đây là new project hay existing project
  - Check for existing files: `pyproject.toml`, `package.json`, `.csproj`, `go.mod`
  - Check for existing source code directories: `app/`, `src/`, `lib/`
  - Check for existing database migrations, tests, configs

- **Detect Existing Tech Stack** (nếu là existing project):
  - **Python**: Parse `pyproject.toml`, `requirements.txt`, `setup.py`
    - Framework: FastAPI, Django, Flask (detect from dependencies)
    - ORM: SQLAlchemy, Django ORM, Tortoise ORM
    - Testing: PyTest, unittest
    - Linter: Ruff, Pylint, Flake8
  - **Node.js**: Parse `package.json`, `tsconfig.json`
    - Framework: Express, NestJS, Fastify
    - ORM: Prisma, TypeORM, Sequelize
    - Testing: Jest, Vitest, Mocha
    - Linter: ESLint, Biome
  - **.NET**: Parse `.csproj`, `*.sln`
    - Framework: ASP.NET Core, Minimal API
    - ORM: Entity Framework Core, Dapper
    - Testing: xUnit, NUnit, MSTest

- **Validate Stack Compatibility**:
  - Compare detected stack với user's tech stack selection
  - **If mismatch**:
    - ⚠️ Warning: "Detected FastAPI but user selected Django"
    - Options:
      - (1) Continue with existing stack (recommended)
      - (2) Migrate to new stack (risky)
      - (3) Hybrid approach (not recommended)
  - **If match**: ✅ Proceed with existing stack

- **Load Existing Structure**:
  - **Parse directory structure**: Map existing folders và files
  - **Parse existing classes**: Extract class names, methods, attributes
  - **Parse existing modules**: Identify services, repositories, controllers
  - **Parse existing models**: Extract database models, DTOs, schemas
  - **Parse existing routes**: Extract API endpoints, URL patterns

- **Identify Existing Patterns**:
  - **Repository Pattern**: Check for `*Repository` classes
  - **Service Pattern**: Check for `*Service` classes
  - **Factory Pattern**: Check for `*Factory` classes
  - **Strategy Pattern**: Check for abstract base classes với multiple implementations
  - **Dependency Injection**: Check for DI container usage

- **Extract Naming Conventions**:
  - **Python**: Analyze existing code for snake_case, PascalCase usage
  - **Node.js**: Analyze for camelCase, PascalCase patterns
  - **.NET**: Analyze for PascalCase, camelCase patterns
  - **File naming**: Analyze existing file naming patterns

- **Analyze Dependencies**:
  - **Parse installed packages**: Extract versions từ lock files
  - **Check for conflicts**: Detect version conflicts với new requirements
  - **Identify missing dependencies**: List dependencies cần install

**2.0.2 Merge Strategy Selection (Chọn Chiến Lược Merge)**

- **Strategy 1: Extend Existing Module** (cho small-medium features)
  - **When**: Feature liên quan chặt chẽ đến existing functionality
  - **Actions**: Add new methods to existing classes, extend repositories

- **Strategy 2: Create New Module** (cho large features)
  - **When**: Feature độc lập, không liên quan trực tiếp đến existing code
  - **Actions**: Create new service/repository classes, new module directory

- **Strategy 3: Refactor & Extend** (khi existing code có issues)
  - **When**: Existing code có code smells, new feature expose design flaws
  - **Actions**: Refactor existing code first, then add new functionality

- **Strategy 4: Hybrid Approach** (cho complex scenarios)
  - **When**: Feature vừa extend existing vừa add new modules
  - **Actions**: Extend existing classes + Create new modules

**2.0.3 Initialize Project Structure** (Based on strategy)
- **For New Project**: Create full directory structure, generate all config files
- **For Existing Project**: Preserve existing structure, add new directories only if needed

**2.0.4 Git Branch Management (Quản Lý Git Branches)**

- **Detect Git Repository**:
  - **Check for `.git` directory**: Verify Git repository exists
    ```bash
    if [ -d ".git" ]; then
        echo "✅ Git repository detected"
    else
        echo "⚠️ Not a Git repository"
        echo "💡 Suggestion: Run 'git init' to initialize Git"
    fi
    ```
  - **Run `git status`**: Verify Git is working properly
  - **If not Git repo**:
    - ⚠️ Warning: "Project is not a Git repository"
    - 💡 Suggest: `git init` to initialize
    - 💡 Suggest: Create initial commit with existing code
  - **If Git not installed**:
    - ❌ Error: "Git is not installed"
    - 📖 Instructions: Install Git from https://git-scm.com/

- **Get Current Branch**:
  - **Run `git branch --show-current`**: Get current branch name
  - **Check branch type**:
    - `main` / `master` / `develop` → Main branches (should create feature branch)
    - `feature/*` → Already on feature branch
    - `hotfix/*` / `bugfix/*` → Other branch types
    - Other → Unknown branch type

- **Check Working Directory Status**:
  - **Run `git status --porcelain`**: Check for uncommitted changes
  - **If uncommitted changes exist**:
    - ⚠️ Warning: "You have uncommitted changes"
    - Options:
      - (1) Stash changes: `git stash save "WIP before {feature-name}"`
      - (2) Commit changes first
      - (3) Continue anyway (not recommended)
  - **If clean**: ✅ Proceed with branch creation

- **Create Feature Branch Strategy**:

  **Branch Naming Convention**:
  - **Format 1**: `feature/{feature-name}`
    - Example: `feature/payment-refund`
    - Use when: No ticket tracking system

  - **Format 2**: `feature/{ticket-id}-{feature-name}`
    - Example: `feature/JIRA-123-payment-refund`
    - Use when: Using JIRA, Linear, GitHub Issues

  - **Sanitize Feature Name**:
    ```python
    def sanitize_branch_name(feature_name: str) -> str:
        """
        Sanitize feature name for Git branch.

        Rules:
        - Convert to lowercase
        - Replace spaces with hyphens
        - Remove special characters
        - Limit length to 50 characters
        """
        name = feature_name.lower()
        name = name.replace(" ", "-")
        name = re.sub(r'[^a-z0-9-]', '', name)
        name = name[:50]
        return name

    # Example:
    # "Add Payment Refund Feature!" → "add-payment-refund-feature"
    ```

  **Branch Creation Logic**:

  - **Case 1: On main/master/develop branch**:
    ```bash
    # Current: main
    # Action: Create new feature branch

    $ git checkout -b feature/payment-refund
    # Switched to a new branch 'feature/payment-refund'

    ✅ Created feature branch: feature/payment-refund
    ```

  - **Case 2: Already on feature branch**:
    ```bash
    # Current: feature/payment-processing
    # New feature: Add refund (related to payment)

    # Option 1: Continue on current branch (recommended for incremental)
    ✅ Continue on: feature/payment-processing
    💡 Reason: Refund is part of payment feature

    # Option 2: Create sub-branch (for independent sub-feature)
    $ git checkout -b feature/payment-refund
    ✅ Created new branch: feature/payment-refund
    ```

  - **Case 3: On other branch type**:
    ```bash
    # Current: hotfix/critical-bug
    # Action: Ask user confirmation

    ⚠️ Warning: Currently on hotfix branch
    ❓ Question: Create feature branch anyway?
    Options:
      (1) Yes, create feature branch
      (2) No, stay on current branch
      (3) Switch to main first, then create feature branch
    ```

- **Commit Strategy**:

  **Commit Message Format** (Conventional Commits):
  ```
  <type>(<scope>): <subject>

  <body>

  <footer>
  ```

  **Types**:
  - `feat`: New feature
  - `fix`: Bug fix
  - `refactor`: Code refactoring
  - `test`: Add tests
  - `docs`: Documentation
  - `chore`: Maintenance

  **Initial Commit** (All generated code):
  ```bash
  $ git add .
  $ git commit -m "feat(payment): add refund functionality

  - Add Refund model to payment.py
  - Add process_refund() method to PaymentService
  - Add refund repository methods
  - Add refund API endpoints
  - Add refund tests
  - Add database migration for refunds table

  Implements: JIRA-123"

  ✅ Committed: feat(payment): add refund functionality
  ```

  **Incremental Commits** (Step-by-step):
  ```bash
  # Commit 1: Models and schemas
  $ git add app/models/payment.py app/schemas/refund.py
  $ git commit -m "feat(payment): add refund models and schemas"

  # Commit 2: Service layer
  $ git add app/services/payment_service.py app/repositories/payment_repository.py
  $ git commit -m "feat(payment): add refund service layer"

  # Commit 3: API endpoints
  $ git add app/routers/payment.py
  $ git commit -m "feat(payment): add refund API endpoints"

  # Commit 4: Tests
  $ git add tests/test_payment_service.py tests/test_refund_api.py
  $ git commit -m "test(payment): add refund tests"

  # Commit 5: Database migration
  $ git add alembic/versions/002_add_refunds_table.py
  $ git commit -m "feat(payment): add refunds table migration"
  ```

- **Git Ignore Management**:

  **Check Existing `.gitignore`**:
  ```python
  def check_gitignore(project_root: str) -> bool:
      """Check if .gitignore exists."""
      gitignore_path = os.path.join(project_root, ".gitignore")
      return os.path.exists(gitignore_path)
  ```

  **Add Stack-Specific Ignores** (if not present):

  **Python**:
  ```gitignore
  # Python
  __pycache__/
  *.py[cod]
  *$py.class
  *.so
  .Python

  # Virtual environments
  venv/
  env/
  ENV/
  .venv

  # Environment variables
  .env
  .env.local

  # IDE
  .vscode/
  .idea/
  *.swp
  *.swo

  # Testing
  .pytest_cache/
  .coverage
  htmlcov/

  # Database
  *.db
  *.sqlite3
  ```

  **Node.js**:
  ```gitignore
  # Node.js
  node_modules/
  npm-debug.log*
  yarn-debug.log*
  yarn-error.log*

  # Environment
  .env
  .env.local
  .env.*.local

  # Build
  dist/
  build/
  .next/
  out/

  # IDE
  .vscode/
  .idea/

  # Testing
  coverage/
  .nyc_output/
  ```

  **.NET**:
  ```gitignore
  # .NET
  bin/
  obj/
  *.user
  *.suo

  # Visual Studio
  .vs/
  *.vsidx

  # Build results
  [Dd]ebug/
  [Rr]elease/

  # NuGet
  *.nupkg
  packages/
  ```

- **Pre-commit Hooks** (Optional):

  **Suggest Installing Pre-commit**:
  ```bash
  # Python: pre-commit framework
  $ pip install pre-commit
  $ pre-commit install

  # Create .pre-commit-config.yaml
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.1.6
      hooks:
        - id: ruff
          args: [--fix]
        - id: ruff-format

    - repo: https://github.com/pre-commit/pre-commit-hooks
      rev: v4.5.0
      hooks:
        - id: trailing-whitespace
        - id: end-of-file-fixer
        - id: check-yaml
        - id: check-added-large-files
  ```

  **Run Linter/Formatter Before Commit**:
  ```bash
  # Python
  $ ruff check . --fix
  $ black .

  # Node.js
  $ eslint . --fix
  $ prettier --write .

  # .NET
  $ dotnet format
  ```

  **Run Tests Before Commit** (Optional):
  ```bash
  # Python
  $ pytest tests/

  # Node.js
  $ npm test

  # .NET
  $ dotnet test
  ```

---

### **🔄 Git Workflow Integration**

```
┌─────────────────────────────────────────────────────────────┐
│ Bước 2.0: Tech Stack Analysis & Project Context            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2.0.1: Analyze Existing Codebase                           │
│   - Detect project type (new/existing)                     │
│   - Detect tech stack                                       │
│   - Load existing structure                                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2.0.2: Merge Strategy Selection                            │
│   - Choose: Extend / Create New / Refactor / Hybrid        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2.0.3: Initialize Project Structure                        │
│   - Create/preserve directory structure                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2.0.4: Git Branch Management ⭐ NEW                        │
│                                                             │
│   Step 1: Detect Git Repository                            │
│   ├─ Check .git directory                                  │
│   ├─ Run git status                                        │
│   └─ If not Git → Suggest git init                         │
│                                                             │
│   Step 2: Get Current Branch                               │
│   ├─ Run git branch --show-current                         │
│   └─ Identify branch type (main/feature/hotfix)            │
│                                                             │
│   Step 3: Check Working Directory                          │
│   ├─ Run git status --porcelain                            │
│   ├─ If uncommitted changes → Suggest stash/commit         │
│   └─ If clean → Proceed                                    │
│                                                             │
│   Step 4: Create Feature Branch                            │
│   ├─ Sanitize feature name                                 │
│   ├─ Generate branch name: feature/{feature-name}          │
│   ├─ Run git checkout -b feature/{feature-name}            │
│   └─ Confirm branch creation                               │
│                                                             │
│   Step 5: Update .gitignore (if needed)                    │
│   ├─ Check existing .gitignore                             │
│   ├─ Add stack-specific ignores                            │
│   └─ Commit .gitignore updates                             │
│                                                             │
│   Step 6: Setup Pre-commit Hooks (optional)                │
│   └─ Suggest pre-commit installation                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2.1-2.5: Generate Code                                     │
│   - Setup Foundation                                        │
│   - Create Class Structure                                  │
│   - Implement Core Methods                                  │
│   - Add Infrastructure                                      │
│   - Quality Assurance                                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Git Commit Generated Code                                  │
│                                                             │
│   Option 1: Single Commit (All at once)                    │
│   ├─ git add .                                             │
│   └─ git commit -m "feat: add {feature-name}"              │
│                                                             │
│   Option 2: Incremental Commits (Step by step)             │
│   ├─ Commit 1: Models & Schemas                            │
│   ├─ Commit 2: Service Layer                               │
│   ├─ Commit 3: API Endpoints                               │
│   ├─ Commit 4: Tests                                       │
│   └─ Commit 5: Migrations                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Output Summary                                              │
│   ✅ Code generated on branch: feature/{feature-name}      │
│   ✅ Committed with message: "feat: add {feature-name}"    │
│   💡 Next: Run tests, then create Pull Request             │
└─────────────────────────────────────────────────────────────┘
```

---

### **⚠️ Error Handling**

**Error 1: Git Not Installed**
```bash
❌ Error: Git is not installed on this system

📖 Solution:
  - Windows: Download from https://git-scm.com/download/win
  - macOS: brew install git
  - Linux: sudo apt-get install git (Ubuntu/Debian)
           sudo yum install git (CentOS/RHEL)

🔧 After installation, run: git --version
```

**Error 2: Not a Git Repository**
```bash
⚠️ Warning: This project is not a Git repository

💡 Suggestion:
  1. Initialize Git repository:
     $ git init

  2. Create initial commit with existing code:
     $ git add .
     $ git commit -m "chore: initial commit"

  3. (Optional) Add remote repository:
     $ git remote add origin <repository-url>
     $ git push -u origin main

❓ Question: Initialize Git repository now?
   [Y/n]: _
```

**Error 3: Uncommitted Changes**
```bash
⚠️ Warning: You have uncommitted changes in your working directory

📋 Uncommitted files:
  M  app/services/payment_service.py
  M  app/models/payment.py
  ?? temp_file.py

💡 Options:
  1. Stash changes (recommended):
     $ git stash save "WIP before adding refund feature"
     → Changes will be saved and can be restored later

  2. Commit changes first:
     $ git add .
     $ git commit -m "wip: work in progress"
     → Commit current work before creating feature branch

  3. Continue anyway (not recommended):
     → New feature code will mix with uncommitted changes
     → Risk of conflicts and confusion

❓ Choose option [1/2/3]: _
```

**Error 4: Branch Already Exists**
```bash
❌ Error: Branch 'feature/payment-refund' already exists

💡 Options:
  1. Checkout existing branch:
     $ git checkout feature/payment-refund
     → Continue work on existing branch

  2. Use different branch name:
     → Suggested: feature/payment-refund-v2
     → Suggested: feature/payment-refund-enhanced

  3. Delete existing branch (dangerous):
     $ git branch -D feature/payment-refund
     → Only if you're sure the branch is not needed

❓ Choose option [1/2/3]: _
```

**Error 5: Merge Conflicts Detected**
```bash
⚠️ Warning: Potential merge conflicts detected

📋 Conflicting files:
  - app/models/payment.py (modified in both branches)
  - app/services/payment_service.py (modified in both branches)

💡 Recommendation:
  1. Merge main branch into feature branch first:
     $ git checkout feature/payment-refund
     $ git merge main

  2. Resolve conflicts manually:
     → Open conflicting files
     → Choose which changes to keep
     → Remove conflict markers (<<<<, ====, >>>>)

  3. Test after resolving conflicts:
     $ pytest tests/

  4. Commit resolved conflicts:
     $ git add .
     $ git commit -m "chore: resolve merge conflicts"

⚠️ Code generation paused. Please resolve conflicts first.
```

**Error 6: Detached HEAD State**
```bash
⚠️ Warning: You are in 'detached HEAD' state

💡 Explanation:
  You are not on any branch. Any commits you make will be lost
  when you checkout another branch.

💡 Solution:
  1. Create a new branch from current state:
     $ git checkout -b feature/payment-refund

  2. Or checkout an existing branch:
     $ git checkout main

❓ Create new branch now? [Y/n]: _
```

---

### **⚙️ Configuration Options**

```python
from dataclasses import dataclass
from typing import Optional, Literal

@dataclass
class GitConfig:
    """Configuration for Git branch management."""

    # Branch Management
    auto_create_branch: bool = True
    """Automatically create feature branch if on main/master/develop."""

    branch_prefix: str = "feature/"
    """Prefix for feature branch names."""

    branch_naming_format: Literal["simple", "with-ticket"] = "simple"
    """
    Branch naming format:
    - simple: feature/{feature-name}
    - with-ticket: feature/{ticket-id}-{feature-name}
    """

    ticket_id_pattern: Optional[str] = None
    """
    Regex pattern to extract ticket ID from feature description.
    Example: r'(JIRA-\d+)' for JIRA tickets
    """

    # Commit Strategy
    auto_commit: bool = True
    """Automatically commit generated code."""

    commit_strategy: Literal["single", "incremental"] = "single"
    """
    Commit strategy:
    - single: One commit for all generated code
    - incremental: Multiple commits (models, services, tests, etc.)
    """

    commit_message_template: str = "feat({scope}): add {feature_name}"
    """
    Commit message template.
    Variables: {scope}, {feature_name}, {ticket_id}
    """

    use_conventional_commits: bool = True
    """Use Conventional Commits format (feat, fix, chore, etc.)."""

    # Git Ignore
    auto_update_gitignore: bool = True
    """Automatically update .gitignore with stack-specific patterns."""

    # Pre-commit Hooks
    suggest_pre_commit: bool = True
    """Suggest installing pre-commit hooks."""

    run_linter_before_commit: bool = False
    """Run linter before committing (requires pre-commit hooks)."""

    run_tests_before_commit: bool = False
    """Run tests before committing (requires pre-commit hooks)."""

    # Error Handling
    on_uncommitted_changes: Literal["stash", "error", "continue"] = "error"
    """
    Action when uncommitted changes detected:
    - stash: Automatically stash changes
    - error: Stop and ask user
    - continue: Continue anyway (not recommended)
    """

    on_branch_exists: Literal["checkout", "error", "rename"] = "error"
    """
    Action when branch already exists:
    - checkout: Checkout existing branch
    - error: Stop and ask user
    - rename: Auto-rename to {branch-name}-v2
    """

# Example usage
git_config = GitConfig(
    auto_create_branch=True,
    branch_prefix="feature/",
    branch_naming_format="with-ticket",
    ticket_id_pattern=r'(JIRA-\d+)',
    commit_strategy="incremental",
    use_conventional_commits=True,
    run_linter_before_commit=True
)
```

---

### **📊 Example: Complete Git Workflow**

```bash
# ========================================
# User Request: "Add refund functionality to payment system (JIRA-123)"
# ========================================

# Step 1: Detect Git Repository
$ git status
# On branch main
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean

✅ Git repository detected
✅ Current branch: main
✅ Working directory clean

# Step 2: Create Feature Branch
$ git checkout -b feature/JIRA-123-payment-refund
# Switched to a new branch 'feature/JIRA-123-payment-refund'

✅ Created feature branch: feature/JIRA-123-payment-refund

# Step 3: Update .gitignore (if needed)
$ cat .gitignore
# ... existing ignores ...

# Add Python-specific ignores
$ echo "__pycache__/" >> .gitignore
$ echo "*.pyc" >> .gitignore
$ echo ".env" >> .gitignore

$ git add .gitignore
$ git commit -m "chore: update .gitignore for Python"

✅ Updated .gitignore

# Step 4: Generate Code (Steps 2.1-2.5)
# ... Code Implementer generates:
#   - app/models/payment.py (add Refund model)
#   - app/services/payment_service.py (add process_refund method)
#   - app/repositories/payment_repository.py (add refund queries)
#   - app/routers/payment.py (add refund endpoints)
#   - tests/test_payment_service.py (add refund tests)
#   - alembic/versions/002_add_refunds_table.py (migration)

✅ Code generation complete

# Step 5: Incremental Commits
# Commit 1: Models
$ git add app/models/payment.py app/schemas/refund.py
$ git commit -m "feat(payment): add refund models and schemas

- Add Refund SQLAlchemy model
- Add RefundCreate and RefundResponse schemas
- Add relationship between Payment and Refund

Implements: JIRA-123"

[feature/JIRA-123-payment-refund 1a2b3c4] feat(payment): add refund models and schemas
 2 files changed, 45 insertions(+)

# Commit 2: Service Layer
$ git add app/services/payment_service.py app/repositories/payment_repository.py
$ git commit -m "feat(payment): add refund service layer

- Add process_refund() method to PaymentService
- Add create_refund() to PaymentRepository
- Add get_refundable_payments() query
- Add refund validation logic

Implements: JIRA-123"

[feature/JIRA-123-payment-refund 2b3c4d5] feat(payment): add refund service layer
 2 files changed, 78 insertions(+)

# Commit 3: API Endpoints
$ git add app/routers/payment.py
$ git commit -m "feat(payment): add refund API endpoints

- POST /api/v1/payments/{id}/refund
- GET /api/v1/payments/{id}/refunds
- Add request/response validation
- Add error handling

Implements: JIRA-123"

[feature/JIRA-123-payment-refund 3c4d5e6] feat(payment): add refund API endpoints
 1 file changed, 52 insertions(+)

# Commit 4: Tests
$ git add tests/test_payment_service.py tests/test_refund_api.py
$ git commit -m "test(payment): add refund tests

- Add unit tests for process_refund()
- Add integration tests for refund API
- Add test fixtures for refund scenarios
- Achieve 95% coverage for refund feature

Implements: JIRA-123"

[feature/JIRA-123-payment-refund 4d5e6f7] test(payment): add refund tests
 2 files changed, 125 insertions(+)

# Commit 5: Database Migration
$ git add alembic/versions/002_add_refunds_table.py
$ git commit -m "feat(payment): add refunds table migration

- Create refunds table with foreign key to payments
- Add indexes for performance
- Add constraints for data integrity

Implements: JIRA-123"

[feature/JIRA-123-payment-refund 5e6f7g8] feat(payment): add refunds table migration
 1 file changed, 35 insertions(+)

# Step 6: Run Tests
$ pytest tests/
# ============================= test session starts ==============================
# collected 45 items
#
# tests/test_payment_service.py ................                          [ 35%]
# tests/test_refund_api.py .............................                  [100%]
#
# ============================== 45 passed in 2.34s ===============================

✅ All tests passed

# Step 7: Output Summary
┌─────────────────────────────────────────────────────────────┐
│ ✅ Code Generation Complete                                │
├─────────────────────────────────────────────────────────────┤
│ Branch: feature/JIRA-123-payment-refund                    │
│ Commits: 5 commits                                          │
│   1. feat(payment): add refund models and schemas          │
│   2. feat(payment): add refund service layer               │
│   3. feat(payment): add refund API endpoints               │
│   4. test(payment): add refund tests                       │
│   5. feat(payment): add refunds table migration            │
│                                                             │
│ Files Changed: 8 files                                      │
│ Lines Added: 335 lines                                      │
│ Test Coverage: 95%                                          │
├─────────────────────────────────────────────────────────────┤
│ 💡 Next Steps:                                             │
│   1. Review generated code                                  │
│   2. Run full test suite: pytest                           │
│   3. Run linter: ruff check .                              │
│   4. Create Pull Request to merge into main                │
│   5. Request code review from team                          │
└─────────────────────────────────────────────────────────────┘

# Step 8: Push to Remote (Optional)
$ git push -u origin feature/JIRA-123-payment-refund
# Enumerating objects: 25, done.
# Counting objects: 100% (25/25), done.
# Delta compression using up to 8 threads
# Compressing objects: 100% (15/15), done.
# Writing objects: 100% (15/15), 3.45 KiB | 3.45 MiB/s, done.
# Total 15 (delta 10), reused 0 (delta 0), pack-reused 0
# remote:
# remote: Create a pull request for 'feature/JIRA-123-payment-refund' on GitHub by visiting:
# remote:      https://github.com/user/repo/pull/new/feature/JIRA-123-payment-refund
# remote:
# To github.com:user/repo.git
#  * [new branch]      feature/JIRA-123-payment-refund -> feature/JIRA-123-payment-refund
# Branch 'feature/JIRA-123-payment-refund' set up to track remote branch 'feature/JIRA-123-payment-refund' from 'origin'.

✅ Pushed to remote repository
💡 Create Pull Request: https://github.com/user/repo/pull/new/feature/JIRA-123-payment-refund
```

---

**2.1 Setup Foundation (Stack-Specific & Incremental)**

- **For New Project**:
  - Create all foundation files from scratch
  - Define all constants, models, exceptions

- **For Existing Project**:
  - **Reuse Existing Constants**: Add new constants to existing config files
    - Example: Add `STRIPE_API_VERSION` to existing `app/config.py`

  - **Extend Existing Models**: Add new models to existing model files
    - Example: Add `Refund` model to `app/models/payment.py`
    - Maintain same ORM patterns (SQLAlchemy, Prisma, EF Core)

  - **Extend Exception Hierarchy**: Add new exceptions inheriting from existing base
    - Example: `RefundError(PaymentError)` inherits from existing `PaymentError`

  - **Follow Existing Type Definitions**: Use same type definition patterns
    - Example: If project uses `TypeAlias`, continue using it

**2.2 Create Class Structure (Stack-Specific & Incremental)**

- **For New Project**:
  - Create all classes from scratch
  - Apply stack conventions

- **For Existing Project**:
  - **Extend Existing Classes**: Add new methods to existing classes
    - Example: Add `process_refund()` to existing `PaymentService`
    - Maintain same method signature patterns
    - Follow existing naming conventions

  - **Create New Classes (if needed)**: Only when feature is independent
    - Example: Create `SubscriptionService` for new subscription feature
    - Follow same patterns as existing classes (Repository, DI, etc.)

  - **Follow Existing Patterns**: Apply same design patterns already in use
    - If project uses Repository pattern → New code MUST use Repository
    - If project uses DI → New code MUST use DI
    - If project uses specific naming → New code MUST follow same naming

**2.3 Implement Core Methods (Stack-Specific & Incremental)**

- **For New Project**:
  - Implement all methods from scratch
  - Follow stack conventions

- **For Existing Project**:
  - **Add Methods to Existing Classes**: Extend existing repositories/services
    - Example: Add `get_refundable_payments()` to `PaymentRepository`
    - Use same query patterns as existing methods
    - Follow same documentation style

  - **Maintain Consistency**: Keep same code style throughout
    - Same docstring format (Google, NumPy, JSDoc, XML)
    - Same error handling patterns
    - Same logging patterns
    - Same validation patterns

  - **Reuse Existing Helper Methods**: Don't duplicate logic
    - Example: Reuse `_validate_amount()` from existing code
    - Extract common logic to shared helpers if needed

  - **Update Existing Endpoints (if needed)**: Extend existing routers
    - Example: Add `/refund` endpoint to existing payment router
    - Follow same routing patterns and decorators

**2.4 Add Stack-Specific Infrastructure (Incremental)**

- **For New Project**:
  - Setup all infrastructure from scratch
  - Create all config files, test fixtures, migrations

- **For Existing Project**:
  - **Extend Existing Logging**: Add new log statements following existing patterns
    - Example: If project uses `structlog`, continue using it
    - Add new loggers for new modules if needed

  - **Update Existing Tests**: Extend test suites instead of creating new
    - Example: Add `test_process_refund()` to existing `test_payment_service.py`
    - Reuse existing fixtures and mocks
    - Follow same test structure and naming

  - **Incremental Database Migrations**: Create new migrations, don't recreate schema
    - Example: Create `002_add_refunds_table.py` migration
    - Use existing migration tool (Alembic, Prisma, EF)
    - Don't modify existing migrations

  - **Update Build Configuration**: Add new dependencies to existing config
    - Example: Add `stripe` to existing `pyproject.toml`
    - Update lock files (poetry.lock, package-lock.json)
    - Don't change existing build scripts unless necessary

**2.5 Quality Assurance (Stack-Specific & Incremental)**

- **For New Project**:
  - Run all quality checks from scratch
  - Setup all linters, formatters, type checkers

- **For Existing Project**:
  - **Run Existing Linters**: Use same linter config as existing code
    - Example: Use existing `.ruff.toml` or `eslint.config.js`
    - Fix any violations in new code only
    - Don't modify existing linter rules without approval

  - **Follow Existing Formatting**: Use same formatter settings
    - Example: Use existing `black` or `prettier` config
    - Format new code to match existing style

  - **Type Check New Code**: Run type checker on new files
    - Example: Run `mypy` only on new/modified files
    - Fix type errors in new code
    - Don't change existing type annotations

  - **Security Scan New Dependencies**: Check new packages for vulnerabilities
    - Example: Run `pip-audit` on newly added packages
    - Update vulnerable dependencies if found
---

### 🏗️ **Bước 3: Apply Design Patterns (Áp Dụng Design Patterns)**

#### **Quá Trình Áp Dụng Patterns**:

**3.1 Pattern Selection (Lựa Chọn Pattern)**
- **Phân tích requirements**: Xem pattern nào phù hợp với yêu cầu
- **Đánh giá complexity**: Chọn pattern phù hợp với độ phức tạp
- **Xem xét maintainability**: Ưu tiên patterns dễ maintain
- **Performance consideration**: Đảm bảo pattern không ảnh hưởng performance

**3.2 Repository Pattern Implementation**
- **Tạo Repository Interface**: Định nghĩa contract cho data access
- **Implement Concrete Repository**: Tạo implementation cụ thể
- **Database Operations**: Implement các operations với database
- **Query Optimization**: Tối ưu các database queries
- **Transaction Management**: Quản lý database transactions

**3.3 Factory Pattern Implementation**
- **Tạo Factory Interface**: Định nghĩa contract cho object creation
- **Implement Concrete Factory**: Tạo factory implementation
- **Object Creation Logic**: Implement logic tạo objects
- **Configuration Management**: Quản lý configuration cho factories
- **Dependency Injection**: Inject dependencies vào objects

**3.4 Observer Pattern Implementation**
- **Event System**: Tạo hệ thống events và notifications
- **Observer Registration**: Cho phép register/unregister observers
- **Event Broadcasting**: Broadcast events đến các observers
- **Async Processing**: Xử lý events bất đồng bộ
- **Error Handling**: Xử lý lỗi trong event system

**3.5 Strategy Pattern Implementation**
- **Strategy Interface**: Định nghĩa contract cho algorithms
- **Concrete Strategies**: Implement các algorithm cụ thể
- **Context Class**: Class sử dụng các strategies
- **Strategy Selection**: Logic chọn strategy phù hợp
- **Runtime Switching**: Cho phép thay đổi strategy runtime

---

### ⚠️ **Bước 4: Handle Error Scenarios (Xử Lý Các Tình Huống Lỗi)**

#### **Quá Trình Xử Lý Lỗi**:

**4.1 Identify Potential Failures (Xác Định Các Điểm Lỗi Tiềm Ẩn)**
- **Input Validation Failures**: Lỗi khi validate input data
- **External Service Failures**: Lỗi khi gọi external services
- **Database Operation Failures**: Lỗi khi thao tác với database
- **Business Logic Failures**: Lỗi trong business logic
- **Network Failures**: Lỗi kết nối mạng
- **Resource Exhaustion**: Hết memory, disk space, etc.

**4.2 Create Exception Classes (Tạo Exception Classes)**
- **Custom Exception Hierarchy**: Tạo hierarchy của custom exceptions
- **Business Logic Exceptions**: Exceptions cho business logic errors
- **Validation Exceptions**: Exceptions cho validation errors
- **External Service Exceptions**: Exceptions cho external service errors
- **Database Exceptions**: Exceptions cho database errors
- **System Exceptions**: Exceptions cho system-level errors

**4.3 Add Try-Catch Blocks (Thêm Try-Catch Blocks)**
- **Wrap Risky Operations**: Bọc các operations có thể gây lỗi
- **Specific Exception Handling**: Xử lý từng loại exception cụ thể
- **Graceful Degradation**: Xử lý lỗi một cách graceful
- **Error Context Preservation**: Giữ lại context khi có lỗi
- **User-Friendly Messages**: Tạo error messages dễ hiểu cho user

**4.4 Implement Fallback Mechanisms (Implement Cơ Chế Fallback)**
- **Primary/Secondary Operations**: Có operation chính và phụ
- **Circuit Breaker Pattern**: Tự động ngắt khi service fail liên tục
- **Retry Logic**: Thử lại khi có lỗi tạm thời
- **Timeout Handling**: Xử lý timeout cho các operations
- **Default Values**: Sử dụng giá trị mặc định khi có lỗi

**4.5 Add Validation Logic (Thêm Logic Validation)**
- **Input Validation**: Validate tất cả input data
- **Business Rule Validation**: Validate business rules
- **Data Integrity Checks**: Kiểm tra tính toàn vẹn dữ liệu
- **Security Validation**: Validate security requirements
- **Performance Validation**: Kiểm tra performance constraints

**4.6 Create Error Logging (Tạo Error Logging)**
- **Structured Logging**: Log errors theo format cấu trúc
- **Error Classification**: Phân loại errors theo severity
- **Context Information**: Log thêm context information
- **Stack Trace**: Capture stack trace cho debugging
- **Alerting**: Gửi alert cho critical errors

---

### ⚡ **Bước 5: Optimize Code Performance (Tối Ưu Performance)**

#### **Quá Trình Tối Ưu Performance**:

**5.1 Profile Code Execution (Profile Code Execution)**
- **Static Analysis**: Phân tích code tĩnh để tìm bottlenecks
- **Complexity Analysis**: Đánh giá độ phức tạp của algorithms
- **Memory Usage Analysis**: Phân tích memory usage patterns
- **Database Query Analysis**: Phân tích database queries
- **I/O Operations Analysis**: Phân tích I/O operations

**5.2 Identify Bottlenecks (Xác Định Bottlenecks)**
- **High Complexity Methods**: Tìm methods có độ phức tạp cao
- **Memory-Intensive Operations**: Tìm operations sử dụng nhiều memory
- **Slow Database Queries**: Tìm database queries chậm
- **Inefficient Algorithms**: Tìm algorithms không hiệu quả
- **Blocking Operations**: Tìm operations blocking

**5.3 Optimize Algorithms (Tối Ưu Algorithms)**
- **Algorithm Selection**: Chọn algorithms hiệu quả hơn
- **Data Structure Optimization**: Tối ưu data structures
- **Loop Optimization**: Tối ưu loops và iterations
- **Recursive to Iterative**: Chuyển từ recursive sang iterative
- **Caching Strategies**: Implement caching cho expensive operations

**5.4 Implement Caching (Implement Caching)**
- **Method-Level Caching**: Cache kết quả của expensive methods
- **Database Query Caching**: Cache kết quả database queries
- **API Response Caching**: Cache API responses
- **Session Caching**: Cache session data
- **Configuration Caching**: Cache configuration data

**5.5 Optimize Database Queries (Tối Ưu Database Queries)**
- **Query Optimization**: Tối ưu SQL queries
- **Index Optimization**: Tối ưu database indexes
- **Connection Pooling**: Implement connection pooling
- **Batch Operations**: Sử dụng batch operations
- **Lazy Loading**: Implement lazy loading

**5.6 Reduce Memory Usage (Giảm Memory Usage)**
- **Object Pooling**: Sử dụng object pooling
- **Memory Leak Prevention**: Ngăn chặn memory leaks
- **Garbage Collection Optimization**: Tối ưu garbage collection
- **Streaming Processing**: Sử dụng streaming cho large data
- **Resource Cleanup**: Đảm bảo cleanup resources

---

### ✅ **Bước 6: Quality Check & Output (Kiểm Tra Chất Lượng & Output)**

#### **Quá Trình Quality Check**:

**6.1 Code Quality Validation**
- **Code Style Check**: Kiểm tra coding style và conventions
- **Complexity Validation**: Kiểm tra độ phức tạp của code
- **Performance Validation**: Kiểm tra performance metrics
- **Security Validation**: Kiểm tra security vulnerabilities
- **Maintainability Check**: Đánh giá tính maintainable của code

**6.2 Generate Supporting Files**
- **Configuration Files**: Tạo các file cấu hình
- **Environment Setup**: Tạo setup cho các environments
- **Utility Functions**: Tạo các utility functions
- **Constants File**: Tạo file constants
- **Type Definitions**: Tạo type definitions

**6.3 Create Final Package**
- **Main Code Package**: Package code chính
- **Supporting Files Package**: Package các file hỗ trợ
- **Documentation Package**: Package documentation
- **Configuration Package**: Package configuration
- **Metadata**: Tạo metadata cho package

---

## 🔄 **Feedback Loops (Vòng Lặp Phản Hồi)**

### **Critical Issues Loop**
- **Trigger**: Khi phát hiện critical issues trong code
- **Action**: Quay lại bước 1 để phân tích lại plan
- **Examples**: Architecture không phù hợp, requirements không rõ ràng

### **Complex Issues Loop**
- **Trigger**: Khi gặp issues phức tạp trong implementation
- **Action**: Quay lại bước 2 để implement lại
- **Examples**: Performance issues, security vulnerabilities

### **Quality Failures Loop**
- **Trigger**: Khi quality check không pass
- **Action**: Quay lại bước 5 để optimize lại
- **Examples**: Code complexity quá cao, performance không đạt target

---

## 📊 **Output của Code Implementer**

### **Main Deliverables**:
1. **Production-Ready Code**: Code hoàn chỉnh, sẵn sàng production
2. **Design Patterns Implementation**: Các design patterns đã được implement
3. **Error Handling**: Comprehensive error handling system
4. **Performance Optimization**: Code đã được optimize performance
5. **Supporting Files**: Các file hỗ trợ cần thiết
6. **Stack-Specific Scaffolding**: Cấu hình linter/formatter, test framework, package manager, CI hint, ORM/migrations tương ứng tech stack người dùng

### **Quality Metrics**:
1. **Code Coverage**: Độ bao phủ của code
2. **Complexity Score**: Điểm độ phức tạp
3. **Performance Score**: Điểm performance
4. **Maintainability Score**: Điểm maintainability
5. **Security Score**: Điểm security

### **Next Phase Input**:
- **Code Package**: Toàn bộ code đã implement
- **Quality Report**: Báo cáo chất lượng code
- **Performance Metrics**: Các metrics về performance
- **Error Handling Documentation**: Documentation về error handling
- **Design Patterns Documentation**: Documentation về design patterns
- **Stack Config Docs**: Hướng dẫn chạy/lint/test/build theo tech stack đã chọn

---

---

## 📝 **Ví Dụ Cụ Thể: Incremental Development**

### **Scenario: Thêm Refund Feature vào Existing Payment System**

#### **Existing Codebase:**
```python
# app/models/payment.py (EXISTING)
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100))
    amount = Column(Float)
    status = Column(String(20))

# app/services/payment_service.py (EXISTING)
class PaymentService:
    def __init__(self, repository: PaymentRepository):
        self.repository = repository

    async def process_payment(self, data: PaymentCreate):
        """Process payment transaction."""
        # ... existing logic
```

#### **Bước 2.0.1: Analyze Existing Codebase**
```python
analysis_result = {
    "project_type": "existing",
    "tech_stack": {
        "language": "Python 3.11",
        "framework": "FastAPI 0.104.1",
        "orm": "SQLAlchemy 2.0.23",
        "testing": "PyTest 7.4.3"
    },
    "existing_patterns": {
        "repository": True,
        "service": True,
        "dependency_injection": True
    },
    "naming_conventions": {
        "classes": "PascalCase",
        "methods": "snake_case",
        "files": "snake_case"
    }
}
```

#### **Bước 2.0.2: Merge Strategy → Extend Existing Module**
```python
strategy = {
    "type": "extend_existing",
    "reason": "Refund is closely related to payment",
    "actions": [
        "Add Refund model to app/models/payment.py",
        "Add process_refund() to PaymentService",
        "Extend PaymentRepository with refund queries"
    ]
}
```

#### **Bước 2.1: Setup Foundation (Incremental)**
```python
# app/models/payment.py (EXTEND EXISTING FILE)
class Payment(Base):  # Existing
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(100))
    amount = Column(Float)
    status = Column(String(20))

# ✅ Add new model to existing file
class Refund(Base):  # NEW
    __tablename__ = "refunds"
    id = Column(Integer, primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id"))
    amount = Column(Float)
    reason = Column(String(200))
    status = Column(String(20))
```

#### **Bước 2.2-2.3: Extend Existing Classes**
```python
# app/services/payment_service.py (EXTEND)
class PaymentService:
    async def process_payment(self, data):  # Existing
        pass

    # ✅ Add new method
    async def process_refund(self, payment_id, amount, reason):  # NEW
        """Process refund for a payment."""
        payment = await self.repository.get_by_id(payment_id)
        # ... refund logic
```

---

## 🎯 **Kết Luận**

Code Implementer nhận implementation plan từ Task Analyzer và thông qua 6 bước chi tiết:

1. **Phân tích plan & existing codebase** để hiểu rõ requirements và context
2. **Tạo code chính** với structure hoàn chỉnh (new hoặc incremental)
3. **Áp dụng design patterns** phù hợp (follow existing patterns)
4. **Xử lý error scenarios** một cách comprehensive
5. **Tối ưu performance** để đạt targets
6. **Quality check** và tạo output package

**Đặc biệt quan trọng:**
- ✅ **Detect existing codebase** trước khi generate code
- ✅ **Reuse existing patterns** thay vì tạo mới
- ✅ **Extend existing classes** khi có thể
- ✅ **Maintain consistency** với code hiện có
- ✅ **Incremental migrations** thay vì recreate schema
- ✅ **Stack-aware scaffolding** theo tech stack người dùng chọn

Kết quả là một code package hoàn chỉnh, production-ready, **tích hợp mượt mà với existing codebase**, với error handling, performance optimization, design patterns phù hợp, và stack-specific tooling, sẵn sàng để chuyển cho Test Generator.
