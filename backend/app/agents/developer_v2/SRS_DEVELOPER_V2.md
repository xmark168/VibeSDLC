# Software Requirements Specification (SRS)
# Developer V2 Agent - Story-Driven Code Generation System

**Document Version:** 1.0  
**Date:** 2025-12-05  
**Author:** VibeSDLC Team  
**Status:** Complete

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Functional Requirements](#4-functional-requirements)
5. [LangGraph Workflow Specification](#5-langgraph-workflow-specification)
6. [State Management](#6-state-management)
7. [Tools & APIs](#7-tools--apis)
8. [Skills System](#8-skills-system)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Data Flow & Sequence Diagrams](#10-data-flow--sequence-diagrams)
11. [Error Handling & Recovery](#11-error-handling--recovery)
12. [Integration Points](#12-integration-points)
13. [Configuration & Environment](#13-configuration--environment)
14. [Appendices](#14-appendices)

---

## 1. Introduction

### 1.1 Purpose
This document specifies the complete requirements for **Developer V2**, an AI-powered software development agent that processes User Stories and automatically generates production-ready code using LangGraph-based workflow orchestration.

### 1.2 Scope
Developer V2 is a component of the VibeSDLC multi-agent system, responsible for:
- Analyzing user stories and creating implementation plans
- Generating production code following project conventions
- Self-reviewing and iterating on code quality
- Running tests and fixing errors autonomously
- Managing git workspaces and code commits

### 1.3 Definitions & Acronyms

| Term | Definition |
|------|------------|
| **LangGraph** | State machine framework for building LLM-powered agents |
| **Story** | User Story with acceptance criteria to implement |
| **LGTM** | "Looks Good To Me" - Code review approval |
| **LBTM** | "Looks Bad To Me" - Code review rejection |
| **IS_PASS** | Summarize gate decision (YES = complete, NO = needs work) |
| **React Mode** | Iterative debug loop (MetaGPT Engineer2 pattern) |
| **Skill** | Reusable knowledge module for specific tech patterns |
| **CocoIndex** | Vector-based code search engine |
| **Worktree** | Git worktree for isolated branch development |

### 1.4 References
- AGENTS.md - System architecture documentation
- MetaGPT Engineer2 - Inspiration for React mode
- Anthropic Agent Skills - Pattern for skill system
- LangGraph Documentation - Workflow framework

---

## 2. Overall Description

### 2.1 Product Perspective

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VibeSDLC Multi-Agent System                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐         ┌──────────────────┐         ┌───────────────┐  │
│   │  Team Leader │────────▶│  Developer V2    │────────▶│  Git/GitHub   │  │
│   │  (Router)    │         │  (This Document) │         │  Repository   │  │
│   └──────────────┘         └──────────────────┘         └───────────────┘  │
│          │                          │                                        │
│          │                          ├──────▶ PostgreSQL (per-branch)        │
│          │                          ├──────▶ CocoIndex (code search)        │
│          │                          └──────▶ LLM APIs (Claude/GPT)          │
│          ▼                                                                   │
│   ┌──────────────┐         ┌──────────────────┐                             │
│   │    Tester    │         │ Business Analyst │                             │
│   └──────────────┘         └──────────────────┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Features Summary

| Feature | Description |
|---------|-------------|
| **Story Processing** | Receive and parse user stories with acceptance criteria |
| **Smart Analysis** | LLM-powered codebase exploration and planning |
| **Code Generation** | Generate complete, production-ready code |
| **Self-Review** | Automated LGTM/LBTM code review loop |
| **Auto-Testing** | Run build, lint, typecheck, and tests |
| **Error Recovery** | Analyze errors and auto-fix (up to 5 iterations) |
| **Git Integration** | Worktree management and commits |
| **Skill System** | Framework-specific knowledge modules |

### 2.3 User Classes and Characteristics

| User Class | Description | Interaction |
|------------|-------------|-------------|
| **Team Leader Agent** | Routes tasks to Developer V2 | Kafka delegation events |
| **Human Developer** | Reviews and merges generated code | GitHub PRs |
| **System Admin** | Configures and monitors the system | Configuration files |

### 2.4 Operating Environment
- **Runtime**: Python 3.11+
- **LLM Provider**: Anthropic Claude or OpenAI GPT (configurable)
- **Database**: PostgreSQL (per-branch containers)
- **Code Index**: CocoIndex with pgvector
- **Container**: Docker for database isolation
- **Package Manager**: Bun (for Next.js projects)

### 2.5 Design Constraints
1. **LLM Token Limits**: Context windows ~200K tokens
2. **Timeout**: Max 60s per LLM call
3. **Debug Iterations**: Max 5 error-fix cycles
4. **React Loop**: Max 40 iterations
5. **Review Retries**: Max 2 LBTM per step

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                              Developer V2 Agent                                │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         DeveloperV2 (BaseAgent)                          │  │
│  │  • handle_task() - Entry point                                          │  │
│  │  • handle_story_event() - Story transition handler                      │  │
│  │  • message_user() - User communication                                  │  │
│  └────────────────────────────────┬────────────────────────────────────────┘  │
│                                   │                                            │
│  ┌────────────────────────────────▼────────────────────────────────────────┐  │
│  │                         DeveloperGraph (LangGraph)                       │  │
│  │                                                                          │  │
│  │   ┌──────────┐   ┌─────────────────┐   ┌───────────┐   ┌────────┐      │  │
│  │   │  setup   │──▶│ analyze_and_plan│──▶│ implement │──▶│ review │      │  │
│  │   │workspace │   │                 │   │           │   │        │      │  │
│  │   └──────────┘   └─────────────────┘   └─────┬─────┘   └───┬────┘      │  │
│  │                                              │              │           │  │
│  │                                              │   LBTM       │           │  │
│  │                                              ◀──────────────┘           │  │
│  │                                              │                          │  │
│  │                                              │ LGTM                     │  │
│  │                                              ▼                          │  │
│  │   ┌───────────────┐   ┌───────────┐   ┌───────────┐                    │  │
│  │   │ analyze_error │◀──│ run_code  │◀──│ summarize │                    │  │
│  │   │               │   │           │   │           │                    │  │
│  │   └───────┬───────┘   └─────┬─────┘   └───────────┘                    │  │
│  │           │                 │                                           │  │
│  │           │ IMPLEMENT       │ PASS                                      │  │
│  │           ▼                 ▼                                           │  │
│  │   ┌───────────┐        ┌───────┐                                       │  │
│  │   │ implement │        │  END  │                                       │  │
│  │   └───────────┘        └───────┘                                       │  │
│  │                                                                          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │                         Supporting Components                           │   │
│  │                                                                         │   │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │   │
│  │  │ ProjectManager  │  │ SkillRegistry│  │ DevContainerManager       │ │   │
│  │  │ (CocoIndex)     │  │ (Tech Skills)│  │ (PostgreSQL containers)   │ │   │
│  │  └─────────────────┘  └──────────────┘  └────────────────────────────┘ │   │
│  │                                                                         │   │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌────────────────────────────┐ │   │
│  │  │ WorkspaceManager│  │ FileCache    │  │ LangfuseObservability     │ │   │
│  │  │ (Git worktrees) │  │ (Read cache) │  │ (Tracing)                 │ │   │
│  │  └─────────────────┘  └──────────────┘  └────────────────────────────┘ │   │
│  │                                                                         │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Breakdown

#### 3.2.1 Core Classes

| Class | File | Responsibility |
|-------|------|----------------|
| `DeveloperV2` | `developer_v2.py` | Main agent, extends BaseAgent |
| `DeveloperGraph` | `src/graph.py` | LangGraph state machine |
| `DeveloperState` | `src/state.py` | TypedDict state definition |
| `AdvancedProjectManager` | `project_manager.py` | CocoIndex code search |
| `ProjectWorkspaceManager` | `workspace_manager.py` | Git worktree management |
| `SkillRegistry` | `src/skills/registry.py` | Skill loading and catalog |
| `DevContainerManager` | `src/tools/container_tools.py` | Docker PostgreSQL |

#### 3.2.2 Node Modules

| Node | File | Purpose |
|------|------|---------|
| `setup_workspace` | `nodes/setup_workspace.py` | Git worktree, dependencies, skills |
| `analyze_and_plan` | `nodes/analyze_and_plan.py` | Story analysis, implementation plan |
| `implement` | `nodes/implement.py` | Code generation with tools |
| `review` | `nodes/review.py` | LGTM/LBTM code review |
| `summarize` | `nodes/summarize.py` | Final review, IS_PASS gate |
| `run_code` | `nodes/run_code.py` | Build, lint, test execution |
| `analyze_error` | `nodes/analyze_error.py` | Error analysis, fix planning |

#### 3.2.3 Tools

| Category | Tools | File |
|----------|-------|------|
| **Filesystem** | read_file_safe, write_file_safe, edit_file, glob, grep_files | `tools/filesystem_tools.py` |
| **Git** | git_status, git_commit, git_create_branch, git_worktree | `tools/git_tools.py` |
| **Shell** | execute_shell | `tools/shell_tools.py` |
| **CocoIndex** | search_codebase, get_related_code | `tools/cocoindex_tools.py` |
| **Container** | container_exec, container_start, container_stop | `tools/container_tools.py` |
| **Skills** | activate_skill, read_skill_file, list_skill_files | `tools/skill_tools.py` |
| **Workspace** | setup_git_worktree, commit_workspace_changes | `tools/workspace_tools.py` |

---

## 4. Functional Requirements

### 4.1 Story Processing (FR-001)

#### FR-001.1: Story Input Parsing
**Priority:** High  
**Description:** Parse user story content from JSON or plain text format.

**Input Formats:**
```json
// JSON format
{
  "story_id": "STORY-123",
  "title": "User Login Feature",
  "content": "As a user, I want to login...",
  "acceptance_criteria": [
    "User can enter email and password",
    "System validates credentials",
    "User sees dashboard after login"
  ]
}

// Plain text format
User Login Feature

As a user, I want to login to access my dashboard.

Acceptance Criteria:
- User can enter email and password
- System validates credentials
- User sees dashboard after login
```

**Acceptance Criteria:**
- SHALL parse JSON story with story_id, title, content, acceptance_criteria
- SHALL parse plain text with title on line 1 and AC after "Acceptance Criteria:"
- SHALL extract story_id from JSON or generate from task_id

---

#### FR-001.2: Story Event Handling
**Priority:** High  
**Description:** Handle story status transitions from Kanban board.

**Events:**
| Event | From Status | To Status | Action |
|-------|-------------|-----------|--------|
| Story Pull | Todo | InProgress | Start processing |
| Story Complete | InProgress | Review | Notify completion |

**Acceptance Criteria:**
- SHALL trigger workflow when story transitions to InProgress
- SHALL ignore transitions to other statuses
- SHALL send task completion notification via Kafka

---

### 4.2 Workspace Management (FR-002)

#### FR-002.1: Git Worktree Setup
**Priority:** High  
**Description:** Create isolated git worktree for story implementation.

**Process:**
1. Generate branch name: `story_{short_id}` (max 8 chars from story_id)
2. Create git worktree from main branch
3. Install dependencies (`bun install --frozen-lockfile`)
4. Generate Prisma client if schema exists
5. Load project context (AGENTS.md, project structure)

**Acceptance Criteria:**
- SHALL create unique branch per story
- SHALL reuse existing worktree if already created
- SHALL skip dependency install if package.json unchanged (hash check)
- SHALL skip prisma generate if schema unchanged (hash check)

---

#### FR-002.2: Workspace Template
**Priority:** Medium  
**Description:** Initialize new projects from Next.js boilerplate.

**Template Location:** `backend/app/agents/templates/boilerplate/nextjs-boilerplate`

**Excluded from Copy:**
- node_modules, .next, build, dist, out
- .turbo, .cache, coverage, .swc
- __pycache__, .pytest_cache, venv

**Acceptance Criteria:**
- SHALL copy boilerplate excluding build artifacts
- SHALL preserve .env file for database connection
- SHALL preserve bun.lock for deterministic installs

---

### 4.3 Analysis & Planning (FR-003)

#### FR-003.1: Codebase Exploration
**Priority:** High  
**Description:** Explore codebase to understand context before planning.

**Available Tools:**
- `read_file_safe` - Read file contents
- `list_directory_safe` - List directory structure
- `glob` - Pattern-based file search
- `grep_files` - Text search in files
- `search_codebase_tool` - Semantic code search (CocoIndex)

**Smart Prefetch:**
- Always read: package.json, prisma/schema.prisma, tsconfig.json, src/app/layout.tsx
- Keyword extraction from story title/requirements
- Glob search for files matching keywords

**Acceptance Criteria:**
- SHALL explore codebase with max 8 tool iterations
- SHALL summarize exploration if > 8000 characters
- SHALL extract keywords from story for smart prefetch

---

#### FR-003.2: Implementation Plan Generation
**Priority:** High  
**Description:** Generate structured implementation plan.

**Output Schema:**
```python
class ImplementationPlan:
    story_summary: str  # 1-sentence summary
    logic_analysis: List[List[str]]  # [[file_path, description], ...]
    steps: List[PlanStep]  # Ordered implementation steps

class PlanStep:
    order: int  # 1-based step number
    description: str  # What to implement
    file_path: str  # Target file path
    action: Literal["create", "modify"]  # Action type
    dependencies: List[str]  # Files needed as context
```

**Ordering Convention:**
1. Database schema (prisma)
2. API routes
3. Components
4. Pages

**Acceptance Criteria:**
- SHALL generate plan with structured output (Pydantic)
- SHALL order steps: database → API → components → pages
- SHALL pre-load dependency file contents (MetaGPT style)
- SHALL filter out migration steps (use db push instead)

---

### 4.4 Code Implementation (FR-004)

#### FR-004.1: Step-by-Step Implementation
**Priority:** High  
**Description:** Execute implementation plan one step at a time.

**Available Tools:**
- `write_file_safe` - Create new files
- `edit_file` - Modify existing files
- `read_file_safe` - Read files (required before edit)
- `activate_skills` - Load skill patterns
- `read_skill_file` - Read detailed skill docs
- `execute_shell` - Run shell commands (debug mode)

**Context Provided:**
- Logic analysis (all file descriptions)
- Current step task description
- Pre-loaded dependency content
- Modified files from previous steps
- Debug logs (if in error recovery)

**Acceptance Criteria:**
- SHALL implement ONE file per step
- SHALL write complete code (no TODOs, no placeholders)
- SHALL enforce read-before-edit rule
- SHALL track all modified files
- SHALL activate relevant skills before writing code

---

#### FR-004.2: Skill Integration
**Priority:** High  
**Description:** Use skill system for framework-specific patterns.

**Skill Selection Guide:**
| File Type | Skill |
|-----------|-------|
| API route (src/app/api/**/route.ts) | `api-route` |
| React component (*.tsx) | `frontend-component`, `frontend-design` |
| Database/Prisma schema | `database-model` |
| Server Actions | `server-action` |
| Unit tests | `unit-test` |
| Debugging | `debugging` |

**Workflow:**
1. Call `activate_skills(["skill-name"])` to load patterns
2. Use patterns from skill to write code
3. Write file with `write_file_safe` or `edit_file`

**Acceptance Criteria:**
- SHALL activate skills before writing code
- SHALL follow patterns from activated skills
- SHALL handle skill not found gracefully

---

### 4.5 Code Review (FR-005)

#### FR-005.1: LGTM/LBTM Review
**Priority:** High  
**Description:** Review implemented code for quality.

**Review Criteria:**
1. **Completeness**: No TODOs, placeholders, or incomplete code
2. **Correctness**: Logic is correct, handles edge cases
3. **Types**: Strong typing, no `any` types (TypeScript)
4. **Imports**: All imports valid and used
5. **Syntax**: Proper JSX/TSX tag closure

**Scope Rules:**
- ONLY review current file from current step
- DO NOT check dependencies from other steps
- Integration errors caught in run_code phase

**Acceptance Criteria:**
- SHALL output LGTM (approve) or LBTM (request changes)
- SHALL provide specific feedback for LBTM
- SHALL force LGTM after 2 LBTM attempts per step
- SHALL track per-step LBTM count separately

---

### 4.6 Code Validation (FR-006)

#### FR-006.1: Build & Test Execution
**Priority:** High  
**Description:** Run format, lint, typecheck, build, and tests.

**Execution Phases:**
1. **Format** (prettier) - Allow fail
2. **Lint Fix** (eslint --fix) - Allow fail
3. **Typecheck** (tsc --noEmit) - Must pass
4. **Build** (next build) - Must pass
5. **Test** (bun test) - Must pass

**Service Configuration:**
```yaml
tech_stack:
  service:
    - name: app
      path: .
      install_cmd: bun install --frozen-lockfile
      typecheck_cmd: bun run typecheck
      build_cmd: bun run build
      test_cmd: bun test
      format_cmd: bunx prettier --write .
      lint_fix_cmd: bunx eslint --fix .
      needs_db: true
      db_cmds:
        - bunx prisma generate
        - bunx prisma db push
```

**Acceptance Criteria:**
- SHALL run all phases in order
- SHALL fail fast on typecheck/build/test errors
- SHALL capture stdout/stderr for error analysis
- SHALL write test logs to `logs/developer/test_log/`

---

### 4.7 Error Recovery (FR-007)

#### FR-007.1: Error Analysis
**Priority:** High  
**Description:** Analyze build/test errors and create fix plan.

**Structured Error Parsing:**
- TypeScript: `file.tsx(line,col): error TS2307: message`
- Next.js: `./src/file.tsx:line:col`
- Prisma: `Error code: P1001`
- Jest: `FAIL src/file.test.tsx`

**Common Error Patterns:**
| Pattern | Fix |
|---------|-----|
| "useActionState only works in Client Component" | Add `'use client'` |
| "Cannot read properties of undefined" | Add null check or default |
| "TS2307 Cannot find module" | Check import path, install package |
| "P2025 Record not found" | Check ID exists before update |

**Acceptance Criteria:**
- SHALL parse structured errors from logs
- SHALL match against common patterns for quick fix
- SHALL generate 1-2 fix steps for simple errors
- SHALL allow max 5 debug iterations
- SHALL return UNFIXABLE if error persists

---

#### FR-007.2: React Mode Loop
**Priority:** Medium  
**Description:** Iterative debug loop for complex errors.

**Behavior:**
- Reset current_step to 0 on test failure
- Increment react_loop_count
- Re-run implementation with error context
- Max 40 react loop iterations

**Acceptance Criteria:**
- SHALL track react_loop_count separately from debug_count
- SHALL provide error_analysis in implement context
- SHALL stop after max_react_loop reached

---

### 4.8 Git Operations (FR-008)

#### FR-008.1: Commit Changes
**Priority:** Medium  
**Description:** Commit implemented changes to branch.

**Process:**
1. Check for uncommitted changes
2. Stage modified files
3. Create commit with descriptive message
4. Push to remote (if configured)

**Commit Message Format:**
```
feat(story-{id}): {title}

Implemented by Developer V2 Agent
Branch: story_{short_id}
```

**Acceptance Criteria:**
- SHALL only commit if workspace has changes
- SHALL use conventional commit format
- SHALL include story ID in commit message

---

## 5. LangGraph Workflow Specification

### 5.1 State Machine Definition

```
                    ┌─────────────────────────┐
                    │      Entry Point        │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    setup_workspace      │
                    │ • Create git worktree   │
                    │ • Install dependencies  │
                    │ • Load skills registry  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   analyze_and_plan      │
                    │ • Explore codebase      │
                    │ • Generate plan         │
                    │ • Pre-load dependencies │
                    └────────────┬────────────┘
                                 │
                                 ▼
              ┌──────────────────────────────────────┐
              │             implement                │
              │ • Execute current step               │
              │ • Write/edit files                   │
              │ • Activate skills                    │
              └───────────────┬──────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  use_code_review? │
                    └────────┬──────────┘
                             │
              ┌──────────────┼──────────────┐
              │ YES          │              │ NO
              ▼              │              ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │     review      │      │    │  more steps?    │
    │ • LGTM/LBTM     │      │    └────────┬────────┘
    └────────┬────────┘      │             │
             │               │    ┌────────┴────────┐
    ┌────────┴────────┐      │    │ YES        │ NO │
    │ LGTM      LBTM  │      │    ▼            ▼    │
    │   │         │   │      │ implement   summarize│
    │   │         │   │      │                      │
    │   │   ┌─────┘   │      │                      │
    │   │   │ (max 2) │      │                      │
    │   │   ▼         │      │                      │
    │   │ implement   │      └──────────────────────┘
    │   │             │
    │   ▼             │
    │ more steps?     │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │ YES        │ NO │
    ▼            ▼
 implement    summarize (if total_lbtm > 0)
                 │
                 │ (skip if all LGTM)
                 ▼
          ┌─────────────────┐
          │    run_code     │
          │ • Format        │
          │ • Lint          │
          │ • Typecheck     │
          │ • Build         │
          │ • Test          │
          └────────┬────────┘
                   │
          ┌────────┴────────┐
          │ PASS      FAIL  │
          ▼            │
         END           │ (debug_count < 5)
                       ▼
               ┌───────────────┐
               │ analyze_error │
               │ • Parse errors│
               │ • Create fix  │
               └───────┬───────┘
                       │
              ┌────────┴────────┐
              │ IMPLEMENT  STOP │
              ▼            ▼
           implement      END
```

### 5.2 Routing Functions

```python
def route_after_implement(state) -> Literal["review", "implement", "summarize"]:
    """Route after implement based on use_code_review flag."""
    if state.get("use_code_review", True):
        return "review"
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    if current_step < total_steps:
        return "implement"
    return "summarize"


def route_review_result(state) -> Literal["implement", "summarize", "run_code"]:
    """Route based on review result (LGTM/LBTM)."""
    if state.get("review_result") == "LBTM":
        return "implement"  # Re-implement current step
    
    current_step = state.get("current_step", 0)
    total_steps = state.get("total_steps", 0)
    if current_step < total_steps:
        return "implement"  # Next step
    
    if state.get("total_lbtm_count", 0) == 0:
        return "run_code"  # Skip summarize if all LGTM
    return "summarize"


def route_summarize_result(state) -> Literal["implement", "run_code"]:
    """Route based on IS_PASS result."""
    if state.get("is_pass") == "NO" and state.get("summarize_count", 0) < 2:
        return "implement"
    return "run_code"


def route_after_test(state) -> Literal["analyze_error", "__end__"]:
    """Route based on test result."""
    if state.get("run_result", {}).get("status") == "PASS":
        return "__end__"
    if state.get("debug_count", 0) < 5:
        return "analyze_error"
    return "__end__"


def route_after_analyze_error(state) -> Literal["implement", "__end__"]:
    """Route after error analysis."""
    if state.get("action") == "IMPLEMENT":
        return "implement"
    return "__end__"
```

### 5.3 Loop Limits

| Loop | Max Iterations | Enforcement |
|------|----------------|-------------|
| LBTM per step | 2 | Force LGTM after 2 attempts |
| Summarize NO | 2 | Move to run_code |
| Debug | 5 | Stop and report |
| React | 40 | Stop and report |

---

## 6. State Management

### 6.1 DeveloperState TypedDict

```python
class DeveloperState(TypedDict, total=False):
    # ============ INPUT ============
    story_id: str
    epic: str
    story_title: str
    story_description: str
    story_requirements: List[str]
    acceptance_criteria: List[str]
    project_id: str
    task_id: str
    user_id: str
    langfuse_handler: Any

    # ============ FLOW CONTROL ============
    action: Literal["ANALYZE", "PLAN", "IMPLEMENT", "RESPOND"]
    task_type: Literal["feature", "bugfix", "refactor", "enhancement", "documentation"]
    complexity: Literal["low", "medium", "high"]
    use_code_review: bool  # Default True

    # ============ ANALYSIS ============
    analysis_result: dict
    affected_files: List[str]
    dependencies: List[str]
    risks: List[str]
    estimated_hours: float

    # ============ PLANNING ============
    implementation_plan: List[dict]  # PlanStep dicts
    current_step: int
    total_steps: int
    logic_analysis: List[List[str]]  # [[file_path, description], ...]
    dependencies_content: Dict[str, str]  # Pre-loaded file contents

    # ============ IMPLEMENTATION ============
    files_created: List[str]
    files_modified: List[str]

    # ============ WORKSPACE ============
    workspace_path: str
    branch_name: str
    main_workspace: str
    workspace_ready: bool
    index_ready: bool  # CocoIndex
    merged: bool

    # ============ OUTPUT ============
    message: str
    error: Optional[str]

    # ============ RUN CODE ============
    run_result: Optional[Dict[str, Any]]
    run_stdout: Optional[str]
    run_stderr: Optional[str]
    run_status: Optional[str]  # PASS/FAIL
    test_command: Optional[List[str]]

    # ============ DEBUG ============
    debug_count: int
    max_debug: int  # Default 5
    debug_history: Optional[List[Dict[str, Any]]]
    error_analysis: Optional[Dict[str, Any]]

    # ============ REACT LOOP ============
    react_loop_count: int
    max_react_loop: int  # Default 40
    react_mode: bool  # Default True

    # ============ SKILLS ============
    tech_stack: str  # Default "nextjs"
    skill_registry: Any  # SkillRegistry instance
    available_skills: List[str]

    # ============ CONTEXT ============
    project_context: Optional[str]  # AGENTS.md content
    agents_md: Optional[str]
    project_config: Optional[Dict[str, Any]]
    related_code_context: Optional[str]

    # ============ REVIEW ============
    review_result: Optional[str]  # LGTM/LBTM
    review_feedback: Optional[str]
    review_details: Optional[str]
    review_count: int
    total_lbtm_count: int
    step_lbtm_counts: Dict[str, int]  # Per-step tracking

    # ============ SUMMARIZE ============
    summary: Optional[str]
    todos: Optional[Dict[str, str]]  # {file_path: issue}
    is_pass: Optional[str]  # YES/NO
    summarize_feedback: Optional[str]
    summarize_count: int
    files_reviewed: Optional[str]
    story_summary: Optional[str]
```

### 6.2 State Helper Functions

```python
# Unpack functions (state dict -> Pydantic model)
def unpack_story(state: Dict) -> StoryInput: ...
def unpack_workspace(state: Dict) -> WorkspaceState: ...
def unpack_plan(state: Dict) -> PlanState: ...
def unpack_review(state: Dict) -> ReviewState: ...
def unpack_debug(state: Dict) -> DebugState: ...
def unpack_summarize(state: Dict) -> SummarizeState: ...
def unpack_run_code(state: Dict) -> RunCodeState: ...

# Pack functions (Pydantic model -> state dict)
def pack_story(model: StoryInput) -> Dict: ...
def pack_workspace(model: WorkspaceState) -> Dict: ...
def pack_plan(model: PlanState) -> Dict: ...
def pack_review(model: ReviewState) -> Dict: ...
def pack_debug(model: DebugState) -> Dict: ...
def pack_summarize(model: SummarizeState) -> Dict: ...
def pack_run_code(model: RunCodeState) -> Dict: ...
```

---

## 7. Tools & APIs

### 7.1 Filesystem Tools

| Tool | Parameters | Returns | Side Effects |
|------|------------|---------|--------------|
| `read_file_safe` | file_path: str | File content or error | Caches content, tracks read |
| `write_file_safe` | file_path: str, content: str, mode: str | Success message | Creates dirs, invalidates cache |
| `edit_file` | file_path: str, old_str: str, new_str: str, replace_all: bool | Success/error | Requires read first |
| `multi_edit_file` | file_path: str, edits: List[dict] | Success/error | Atomic operation |
| `list_directory_safe` | dir_path: str | Directory listing | None |
| `delete_file_safe` | file_path: str | Success/error | Deletes file |
| `copy_file_safe` | source: str, dest: str | Success/error | Copies file |
| `move_file_safe` | source: str, dest: str | Success/error | Moves file |
| `glob` | pattern: str, path: str | Matching files | None |
| `grep_files` | pattern: str, path: str, file_pattern: str | Matching lines | None |

### 7.2 Git Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `git_status` | - | Status output |
| `git_commit` | message: str | Commit hash |
| `git_create_branch` | branch_name: str | Success/error |
| `git_checkout` | branch_name: str | Success/error |
| `git_diff` | - | Diff output |
| `git_merge` | source_branch: str | Success/error |
| `git_create_worktree` | branch: str, path: str | Worktree info |
| `git_remove_worktree` | path: str | Success/error |

### 7.3 Shell Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `execute_shell` | command: str, working_directory: str, timeout: int | {exit_code, stdout, stderr} |

### 7.4 Container Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `container_start` | workspace_path: str, project_type: str | DB connection info |
| `container_exec` | command: str | Command output |
| `container_logs` | tail: int | DB logs |
| `container_status` | - | Container status |
| `container_stop` | - | Confirmation |

### 7.5 Skill Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `activate_skills` | skills: List[str] | Skill content |
| `read_skill_file` | path: str | File content |
| `list_skill_files` | - | Available files |

### 7.6 CocoIndex Tools

| Tool | Parameters | Returns |
|------|------------|---------|
| `search_codebase_tool` | query: str, top_k: int | Code snippets with scores |
| `get_related_code` | file_path: str | Related code context |
| `get_project_structure` | - | Directory tree |
| `get_agents_md` | workspace_path: str | AGENTS.md content |

---

## 8. Skills System

### 8.1 Skill Architecture

```
skills/
├── general/                    # Tech-agnostic skills
│   ├── debugging/
│   │   └── SKILL.md
│   └── run-command/
│       └── SKILL.md
│
├── nextjs/                     # Next.js specific skills
│   ├── api-route/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── examples.md
│   ├── database-model/
│   │   └── SKILL.md
│   ├── frontend-component/
│   │   └── SKILL.md
│   ├── frontend-design/
│   │   └── SKILL.md
│   ├── server-action/
│   │   └── SKILL.md
│   ├── state-management/
│   │   └── SKILL.md
│   ├── unit-test/
│   │   └── SKILL.md
│   └── authentication/
│       └── SKILL.md
│
├── plan_prompts.yaml           # Tech-specific planning prompts
├── project-structure.md        # Project structure template
└── registry.py                 # Skill loader
```

### 8.2 SKILL.md Format

```markdown
---
name: api-route
description: Create Next.js API routes with proper validation and error handling
internal: false
---

# API Route Skill

## When to Use
- Creating new API endpoints (src/app/api/**/route.ts)
- Adding CRUD operations
- Integrating with database

## Patterns

### Basic Route Structure
\`\`\`typescript
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { z } from "zod";

const schema = z.object({
  name: z.string().min(1),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = schema.parse(body);
    
    const result = await prisma.model.create({ data });
    return NextResponse.json({ success: true, data: result });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { success: false, error: "Validation failed" },
        { status: 400 }
      );
    }
    return NextResponse.json(
      { success: false, error: "Internal error" },
      { status: 500 }
    );
  }
}
\`\`\`

## Rules
1. Always validate input with Zod
2. Return consistent response shape: { success, data?, error? }
3. Handle errors with proper status codes
4. Use try-catch for database operations
```

### 8.3 Skill Loading Process

1. **Level 1 (Startup)**: Load metadata from frontmatter
   - name, description, internal flag
   - Used for skill catalog in system prompt

2. **Level 2 (Activation)**: Load full SKILL.md body
   - Triggered by `activate_skills()` tool call
   - Injected into implement context

3. **Level 3 (On-Demand)**: Load bundled files
   - references/, scripts/, assets/
   - Loaded via `read_skill_file()` tool

### 8.4 SkillRegistry API

```python
class SkillRegistry:
    @classmethod
    def load(cls, tech_stack: str) -> "SkillRegistry":
        """Load all skills for tech stack (including general)."""
    
    def get_skill_catalog_for_prompt(self) -> str:
        """Get skill list for system prompt (Level 1)."""
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID (exact or partial match)."""
    
    def get_skill_ids(self) -> List[str]:
        """List all available skill IDs."""
    
    def get_skill_content(self, skill: Skill) -> str:
        """Get full skill content (Level 2)."""
```

---

## 9. Non-Functional Requirements

### 9.1 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Story processing time | < 10 minutes | End-to-end for simple story |
| LLM call latency | < 60 seconds | Per individual call |
| Code search latency | < 2 seconds | CocoIndex query |
| File read latency | < 100ms | With cache hit |
| Build time | < 3 minutes | Next.js production build |

### 9.2 Reliability Requirements

| Requirement | Specification |
|-------------|---------------|
| LLM retry | 3 attempts with exponential backoff |
| Debug iterations | Max 5 before stopping |
| Review iterations | Max 2 LBTM per step |
| State persistence | LangGraph checkpointing |
| Error logging | All errors to structured logs |

### 9.3 Scalability Requirements

| Aspect | Specification |
|--------|---------------|
| Concurrent stories | 1 per agent instance |
| Horizontal scaling | Multiple agent instances via Kafka |
| Database isolation | One PostgreSQL container per branch |
| Index isolation | One CocoIndex table per project |

### 9.4 Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| Path traversal prevention | `_is_safe_path()` check |
| Command injection | Parameterized execution |
| Secret handling | Environment variables only |
| Container isolation | Docker network separation |

### 9.5 Observability Requirements

| Aspect | Tool | Data Captured |
|--------|------|---------------|
| Tracing | Langfuse | LLM calls, tool usage, spans |
| Logging | Python logging | All node transitions |
| Metrics | Custom | Token usage, latency, success rate |
| Test logs | File | Build/test output per story |

---

## 10. Data Flow & Sequence Diagrams

### 10.1 Story Processing Flow

```
┌─────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────┐
│  Kafka  │     │ DeveloperV2  │     │ LangGraph   │     │   LLM   │
└────┬────┘     └──────┬───────┘     └──────┬──────┘     └────┬────┘
     │                 │                    │                  │
     │ TaskContext     │                    │                  │
     │────────────────▶│                    │                  │
     │                 │                    │                  │
     │                 │ Initial state      │                  │
     │                 │───────────────────▶│                  │
     │                 │                    │                  │
     │                 │                    │ setup_workspace  │
     │                 │                    │─────────────────▶│
     │                 │                    │◀─────────────────│
     │                 │                    │                  │
     │                 │                    │ analyze_and_plan │
     │                 │                    │─────────────────▶│
     │                 │                    │◀─────────────────│
     │                 │                    │                  │
     │                 │                    │ implement (loop) │
     │                 │                    │─────────────────▶│
     │                 │                    │◀─────────────────│
     │                 │                    │                  │
     │                 │                    │ review           │
     │                 │                    │─────────────────▶│
     │                 │                    │◀─────────────────│
     │                 │                    │                  │
     │                 │                    │ run_code         │
     │                 │                    │──────┐           │
     │                 │                    │      │ Shell     │
     │                 │                    │◀─────┘           │
     │                 │                    │                  │
     │                 │ Final state        │                  │
     │                 │◀───────────────────│                  │
     │                 │                    │                  │
     │ TaskResult      │                    │                  │
     │◀────────────────│                    │                  │
     │                 │                    │                  │
```

### 10.2 Code Search Flow (CocoIndex)

```
┌───────────┐     ┌─────────────────┐     ┌──────────┐     ┌──────────┐
│  LLM Node │     │ ProjectManager  │     │ pgvector │     │ Reranker │
└─────┬─────┘     └────────┬────────┘     └─────┬────┘     └─────┬────┘
      │                    │                    │                 │
      │ search_codebase    │                    │                 │
      │───────────────────▶│                    │                 │
      │                    │                    │                 │
      │                    │ embed_query_fast() │                 │
      │                    │────────────────────│                 │
      │                    │                    │                 │
      │                    │ Vector search      │                 │
      │                    │───────────────────▶│                 │
      │                    │◀───────────────────│                 │
      │                    │ (20 candidates)    │                 │
      │                    │                    │                 │
      │                    │ Rerank candidates  │                 │
      │                    │────────────────────────────────────▶│
      │                    │◀────────────────────────────────────│
      │                    │ (top 5 reranked)   │                 │
      │                    │                    │                 │
      │ Code snippets      │                    │                 │
      │◀───────────────────│                    │                 │
      │                    │                    │                 │
```

### 10.3 Error Recovery Flow

```
                    ┌─────────────────┐
                    │    run_code     │
                    │  status: FAIL   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  analyze_error  │
                    │ • Parse errors  │
                    │ • Match patterns│
                    │ • Create fix    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │   IMPLEMENT     │           │   UNFIXABLE     │
    │ (fixable error) │           │ (give up)       │
    └────────┬────────┘           └────────┬────────┘
             │                             │
             ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │    implement    │           │      END        │
    │ debug_count++   │           │ Report error    │
    └────────┬────────┘           └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │    run_code     │
    │ (retry test)    │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │ PASS      FAIL  │
    ▼            │
   END           │ (debug_count < 5)
                 ▼
          analyze_error
           (repeat)
```

---

## 11. Error Handling & Recovery

### 11.1 Error Categories

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| **LLM Timeout** | API timeout, rate limit | Retry 3x with backoff |
| **Parse Error** | Invalid JSON from LLM | Fallback to regex extraction |
| **Build Error** | TypeScript, Next.js | analyze_error → fix |
| **Test Error** | Jest assertion failure | analyze_error → fix |
| **Git Error** | Merge conflict, worktree exists | Reuse existing or recreate |
| **Tool Error** | File not found, permission denied | Return error message to LLM |

### 11.2 Error Parsing Patterns

```python
# TypeScript: src/file.tsx(line,col): error TS2307: message
ts_pattern = r'([^\s(]+\.tsx?)\((\d+),(\d+)\):\s*error\s*(TS\d+):\s*(.+)'

# Next.js: ./src/file.tsx:line:col
nextjs_pattern = r'\./([^\s:]+\.tsx?):(\d+):(\d+)\s*\n?\s*(.+?)(?:\n|$)'

# Prisma: Error code: P1001
prisma_pattern = r'Error code:\s*(P\d+)[^\n]*\n?(.+?)(?:\n\n|$)'

# Jest: FAIL src/file.test.tsx
jest_pattern = r'FAIL\s+([^\s]+\.test\.tsx?)'

# Module not found
module_pattern = r"(?:Cannot find module|Module not found|Can't resolve)\s*['\"]([^'\"]+)['\"]"
```

### 11.3 Common Error Fixes

| Error Code | Pattern | Auto-Fix |
|------------|---------|----------|
| TS2307 | Cannot find module | Check path, install package |
| TS2345 | Type mismatch | Cast or fix type |
| TS2322 | Not assignable | Type assertion |
| TS2339 | Property doesn't exist | Add to interface or `?.` |
| TS7006 | Implicit any | Add type annotation |
| P2002 | Unique constraint | Handle duplicate |
| P2025 | Record not found | Check exists before update |

### 11.4 Debug History Tracking

```python
debug_history = [
    {
        "iteration": 1,
        "error_type": "TEST_ERROR",
        "file": "src/app/api/users/route.ts",
        "fix_description": "Add Zod validation",
        "result": "FAIL"
    },
    {
        "iteration": 2,
        "error_type": "IMPORT_ERROR", 
        "file": "src/components/UserForm.tsx",
        "fix_description": "Fix import path",
        "result": "PASS"
    }
]
```

---

## 12. Integration Points

### 12.1 Kafka Topics

| Topic | Publisher | Consumer | Message Type |
|-------|-----------|----------|--------------|
| `DELEGATION_REQUESTS` | Team Leader | Developer V2 | TaskContext |
| `AGENT_RESPONSES` | Developer V2 | Frontend | TaskResult |
| `STORY_EVENTS` | Kanban Board | Developer V2 | StoryTransition |

### 12.2 Database Connections

| Database | Purpose | Connection String |
|----------|---------|-------------------|
| **PostgreSQL (Main)** | Application data | Via Prisma |
| **PostgreSQL (CocoIndex)** | Code embeddings | `COCOINDEX_DATABASE_URL` |
| **PostgreSQL (Per-Branch)** | Dev container | `postgresql://dev:dev@localhost:{port}/app` |

### 12.3 External Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Anthropic API** | Claude LLM | `ANTHROPIC_API_KEY`, `ANTHROPIC_API_BASE` |
| **OpenAI API** | GPT fallback | `OPENAI_API_KEY`, `OPENAI_API_BASE` |
| **Langfuse** | Observability | Auto-configured via langfuse client |
| **Docker** | Container management | Docker socket |

---

## 13. Configuration & Environment

### 13.1 Environment Variables

```bash
# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_API_BASE=https://api.anthropic.com
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1

# Model Override (optional)
DEVV2_MODEL_PLAN=claude-sonnet-4-20250514
DEVV2_MODEL_IMPLEMENT=claude-opus-4-5-20251101
DEVV2_MODEL_REVIEW=claude-sonnet-4-20250514

# CocoIndex
COCOINDEX_DATABASE_URL=postgresql://user:pass@localhost:5432/cocoindex

# Project Database (for dev containers)
DATABASE_URL=postgresql://dev:dev@localhost:5432/app
```

### 13.2 LLM Configuration

```python
LLM_CONFIG = {
    "router": {"model": "claude-opus-4-5-20251101", "temperature": 0.1, "timeout": 30},
    "analyze": {"model": "claude-opus-4-5-20251101", "temperature": 0.2, "timeout": 40},
    "plan": {"model": "claude-opus-4-5-20251101", "temperature": 0.2, "timeout": 60},
    "implement": {"model": "claude-opus-4-5-20251101", "temperature": 0, "timeout": 60},
    "debug": {"model": "claude-opus-4-5-20251101", "temperature": 0.2, "timeout": 40},
    "review": {"model": "claude-opus-4-5-20251101", "temperature": 0.1, "timeout": 30},
    "summarize": {"model": "claude-opus-4-5-20251101", "temperature": 0.1, "timeout": 30},
}
```

### 13.3 Project Configuration (project_config)

```yaml
tech_stack:
  name: nextjs
  service:
    - name: app
      path: .
      install_cmd: bun install --frozen-lockfile
      typecheck_cmd: bun run typecheck
      build_cmd: bun run build
      test_cmd: bun test
      format_cmd: bunx prettier --write .
      lint_fix_cmd: bunx eslint --fix .
      needs_db: true
      db_cmds:
        - bunx prisma generate
        - bunx prisma db push
```

---

## 14. Appendices

### 14.1 File Structure

```
backend/app/agents/developer_v2/
├── developer_v2.py          # Main agent class
├── flows.py                 # CocoIndex embedding functions
├── project_manager.py       # AdvancedProjectManager (CocoIndex)
├── workspace_manager.py     # ProjectWorkspaceManager (Git)
├── __init__.py
│
├── src/
│   ├── graph.py             # LangGraph definition
│   ├── state.py             # DeveloperState TypedDict
│   ├── schemas.py           # Pydantic schemas
│   ├── state_helpers.py     # State pack/unpack utilities
│   ├── prompts.yaml         # LLM prompts
│   ├── __init__.py
│   │
│   ├── nodes/               # LangGraph nodes
│   │   ├── setup_workspace.py
│   │   ├── analyze_and_plan.py
│   │   ├── implement.py
│   │   ├── review.py
│   │   ├── summarize.py
│   │   ├── run_code.py
│   │   ├── analyze_error.py
│   │   ├── _llm.py          # LLM instances
│   │   ├── _helpers.py      # Node helpers
│   │   ├── schemas.py       # Node-specific schemas
│   │   └── __init__.py
│   │
│   ├── tools/               # LangChain tools
│   │   ├── filesystem_tools.py
│   │   ├── git_tools.py
│   │   ├── shell_tools.py
│   │   ├── cocoindex_tools.py
│   │   ├── container_tools.py
│   │   ├── skill_tools.py
│   │   ├── workspace_tools.py
│   │   ├── execution_tools.py
│   │   └── __init__.py
│   │
│   ├── skills/              # Skill system
│   │   ├── registry.py      # SkillRegistry class
│   │   ├── skill_loader.py  # SKILL.md parser
│   │   ├── __init__.py
│   │   ├── general/         # Tech-agnostic skills
│   │   │   ├── debugging/SKILL.md
│   │   │   └── run-command/SKILL.md
│   │   └── nextjs/          # Next.js skills
│   │       ├── api-route/SKILL.md
│   │       ├── database-model/SKILL.md
│   │       ├── frontend-component/SKILL.md
│   │       ├── frontend-design/SKILL.md
│   │       ├── server-action/SKILL.md
│   │       ├── state-management/SKILL.md
│   │       ├── unit-test/SKILL.md
│   │       ├── authentication/SKILL.md
│   │       ├── plan_prompts.yaml
│   │       └── project-structure.md
│   │
│   └── utils/               # Utility modules
│       ├── compress_utils.py
│       ├── db_container.py
│       ├── json_utils.py
│       ├── llm_utils.py
│       ├── prompt_utils.py
│       ├── token_utils.py
│       └── __init__.py
│
├── tests/                   # Test files
│   ├── test_dev_v2_real2.py
│   ├── test_analyze_and_plan.py
│   ├── test_skill_tools.py
│   ├── test_story_homepage.py
│   └── test_metagpt_flow.py
│
└── docker/                  # Docker configs
    └── docker-compose.dev.yml
```

### 14.2 API Response Schema

```python
class TaskResult:
    success: bool
    output: str
    error_message: Optional[str]
    structured_data: Optional[dict]  # Contains:
        # action: str
        # task_type: str
        # complexity: str
        # analysis: dict
        # plan_steps: int
        # files_created: List[str]
        # files_modified: List[str]
        # validation: dict
        # tests_passed: bool
        # branch_name: str
        # workspace_path: str
```

### 14.3 Glossary

| Term | Definition |
|------|------------|
| **Agent** | Autonomous software component that performs tasks |
| **BaseAgent** | Abstract class providing Kafka integration |
| **CocoIndex** | Vector embedding library for code search |
| **LangGraph** | State machine framework for LLM workflows |
| **Node** | Single step in LangGraph workflow |
| **Skill** | Reusable knowledge module in SKILL.md format |
| **Story** | User Story with acceptance criteria |
| **Worktree** | Git feature for parallel branch checkouts |
| **LGTM** | "Looks Good To Me" - code review approval |
| **LBTM** | "Looks Bad To Me" - code review rejection |
| **IS_PASS** | Summarize gate decision (YES/NO) |
| **React Mode** | Iterative debug pattern from MetaGPT |

---

**End of Document**

---

*Document History:*
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-05 | VibeSDLC Team | Initial complete specification |
