# Code Implementor Agent

> **Thay thế Planner Subagent bằng DeepAgents Built-in Planning**

Code Implementor Agent mới sử dụng deepagents library để thay thế planner subagent riêng biệt, tận dụng built-in planning capabilities thông qua `write_todos` tool.

## 🎯 Vấn đề được Giải quyết

**Vấn đề cũ:**
- Planner subagent riêng biệt là redundant vì deepagents đã có built-in planning
- Manual graph construction và workflow management phức tạp
- State management khó khăn giữa nhiều agents
- Thiếu stack detection và boilerplate retrieval
- Không có pgvector indexing cho codebase context

**Giải pháp mới:**
- ✅ Sử dụng deepagents' built-in `write_todos` cho planning
- ✅ Automatic workflow management
- ✅ Simplified state management với persistence
- ✅ Stack detection và boilerplate retrieval
- ✅ LangChain PGVector indexing cho semantic code search
- ✅ Built-in human-in-the-loop support

## 🏗️ Architecture

```
Code Implementor Agent (DeepAgents)
├── Built-in Planning (write_todos tool)
├── Tools
│   ├── Codebase Operations
│   │   ├── load_codebase_tool
│   │   ├── index_codebase_tool (LangChain PGVector)
│   │   └── search_similar_code_tool
│   ├── Stack & Boilerplate
│   │   ├── detect_stack_tool
│   │   └── retrieve_boilerplate_tool
│   ├── Git Operations
│   │   ├── create_feature_branch_tool
│   │   ├── commit_changes_tool
│   │   └── create_pull_request_tool
│   ├── Code Generation
│   │   ├── select_integration_strategy_tool
│   │   └── generate_code_tool
│   └── Review & Feedback
│       ├── collect_feedback_tool
│       └── refine_code_tool
└── Subagents
    ├── code_generator (specialized code generation)
    └── code_reviewer (code quality review)
```

## 🔄 Workflow

DeepAgents tự động handle workflow:

1. **Planning Phase**: Agent sử dụng `write_todos` để tạo implementation plan
2. **Analysis Phase**: Load và index codebase, detect stack (cho new projects)
3. **Implementation Loop**: 
   - Select integration strategy cho mỗi task
   - Generate code using subagents
   - Commit changes
   - Update todo status
4. **Review & Refinement**: Handle user feedback và improvements
5. **Completion**: Create pull request khi tất cả tasks hoàn thành

## 🚀 Usage

### Basic Usage

```python
from app.agents.developer.implementor import run_implementor

result = await run_implementor(
    user_request="Add user authentication with JWT",
    working_directory="./src",
    project_type="existing"  # or "new"
)
```

### Advanced Usage

```python
from app.agents.developer.implementor import create_implementor_agent

agent = create_implementor_agent(
    working_directory="./src",
    project_type="new",
    enable_pgvector=True,
    boilerplate_templates_path="./templates/boilerplate",
    model_name="gpt-4o"
)

result = await agent.ainvoke(initial_state)
```

### New Project với Boilerplate

```python
result = await run_implementor(
    user_request="Create a FastAPI microservice with user management",
    working_directory="./new-service",
    project_type="new",  # Triggers stack detection & boilerplate
    enable_pgvector=True
)
```

## 🛠️ Integration Strategies

Agent tự động select strategy phù hợp:

- **extend_existing**: Add functionality to existing files/classes
- **create_new**: Create new files, modules, or components  
- **refactor**: Improve existing code structure
- **fix_issue**: Fix specific bugs or issues
- **hybrid**: Combination approach (complex tasks)

## 📁 File Structure

```
implementor/
├── __init__.py              # Main exports
├── agent.py                 # Core implementor agent
├── instructions.py          # System prompts
├── subagents.py            # Code generator & reviewer
├── tools/
│   ├── __init__.py
│   ├── codebase_tools.py   # load_codebase, index_codebase
│   ├── git_tools.py        # branch, commit, PR tools
│   ├── stack_tools.py      # detect_stack, retrieve_boilerplate
│   ├── generation_tools.py # strategy selection, code generation
│   └── review_tools.py     # feedback collection, refinement
├── example.py              # Usage examples
└── README.md               # This file
```

## 🔧 Tools Chi tiết

### Codebase Operations
- `load_codebase_tool`: Analyze existing codebase structure
- `index_codebase_tool`: Index với pgvector cho semantic search

### Stack & Boilerplate  
- `detect_stack_tool`: Detect technology stack (Python, Node.js, Java, etc.)
- `retrieve_boilerplate_tool`: Get templates từ `templates/boilerplate/`

### Git Operations
- `create_feature_branch_tool`: Create feature branch cho development
- `commit_changes_tool`: Commit changes với descriptive messages
- `create_pull_request_tool`: Create PR cho code review

### Code Generation
- `select_integration_strategy_tool`: Choose best approach cho task
- `generate_code_tool`: Generate code using code_generator subagent

### Review & Feedback
- `collect_feedback_tool`: Present code to user cho review
- `refine_code_tool`: Improve code based on feedback

## 🎯 Subagents

### Code Generator Subagent
- Specialized trong high-quality code generation
- Follows existing patterns và best practices
- Includes proper error handling và documentation

### Code Reviewer Subagent  
- Expert code review cho quality, security, performance
- Identifies issues và suggests improvements
- Provides detailed feedback với severity levels

## 🗄️ pgvector Integration

```python
# Automatic indexing cho semantic search
index_codebase_tool("./src", enable_pgvector=True)

# Search similar code patterns
similar_code = search_similar_code("authentication function")
```

## 📋 Example Workflow

```python
# 1. User request
user_request = "Add user authentication with JWT tokens"

# 2. Agent automatically:
# - Uses write_todos to create plan
# - Loads và indexes codebase
# - Selects integration strategies
# - Generates code với subagents
# - Commits changes
# - Creates pull request

result = await run_implementor(user_request, "./src")

# 3. Check results
print(f"Status: {result['implementation_status']}")
print(f"Todos completed: {len([t for t in result['todos'] if t['status'] == 'completed'])}")
print(f"Files generated: {len(result['generated_files'])}")
```

## 🆚 So sánh với Old Approach

| Aspect | Old (Separate Planner) | New (DeepAgents) |
|--------|----------------------|------------------|
| Planning | Separate planner subagent | Built-in write_todos |
| Workflow | Manual graph construction | Automatic workflow |
| State Management | Complex cross-agent state | Simplified with persistence |
| Stack Detection | ❌ Not available | ✅ Automatic detection |
| Boilerplate | ❌ Manual setup | ✅ Auto retrieval |
| pgvector | ❌ Not integrated | ✅ LangChain PGVector |
| Human-in-loop | Manual implementation | ✅ Built-in support |
| Code Complexity | High maintenance | Simplified architecture |

## 🔧 Configuration

### Environment Variables

```bash
OPENAI_API_KEY=your-openai-key
OPENAI_BASE_URL=your-agent-router-url  # Optional
PGVECTOR_CONNECTION_STRING=postgresql+psycopg://langchain:langchain@localhost:6024/langchain
BOILERPLATE_TEMPLATES_PATH=./templates/boilerplate
```

### Boilerplate Templates

Templates được organize theo stack:

```
templates/boilerplate/
├── python/
│   ├── fastapi-basic/
│   ├── django-basic/
│   └── flask-basic/
├── nodejs/
│   ├── express-basic/
│   ├── nextjs-basic/
│   └── react-basic/
└── demo/
    └── src/
```

## 🛠️ Setup & Installation

### Quick Setup với LangChain PGVector

```bash
# 1. Install dependencies
pip install langchain-postgres langchain-openai langchain-core psycopg[binary]

# 2. Setup PostgreSQL với pgvector (Docker)
docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 6024:5432 \
  -d pgvector/pgvector:pg16

# 3. Run automated setup
python services/ai-agent-service/app/agents/developer/implementor/setup_langchain_pgvector.py
```

### Manual Setup

```bash
# Set environment variables
export OPENAI_API_KEY="your-openai-key"
export PGVECTOR_CONNECTION_STRING="postgresql+psycopg://langchain:langchain@localhost:6024/langchain"

# Test connection
python -c "
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings
print('✅ LangChain PGVector ready!')
"
```

## 🧪 Testing

```bash
# Run example
python services/ai-agent-service/app/agents/developer/implementor/example.py

# Test specific functionality
python -c "
import asyncio
from implementor import run_implementor

async def test():
    result = await run_implementor('Add health check endpoint', './test-project')
    print(result)

asyncio.run(test())
"
```

## 🚀 Benefits

1. **Simplified Architecture**: Loại bỏ redundant planner subagent
2. **Better Integration**: Tận dụng deepagents ecosystem
3. **Enhanced Functionality**: Stack detection, boilerplate, LangChain PGVector
4. **Improved UX**: Automatic workflow management
5. **Reduced Complexity**: Ít code hơn, dễ maintain hơn
6. **Better Context**: Semantic search với LangChain PGVector indexing

## 🔮 Future Enhancements

- [ ] Advanced LangChain PGVector integration với custom embeddings
- [ ] More boilerplate templates cho different stacks
- [ ] Integration với GitHub/GitLab APIs cho automatic PR creation
- [ ] Advanced code review với static analysis tools
- [ ] Support cho more programming languages
- [ ] Integration với CI/CD pipelines

---

**Kết luận**: Code Implementor Agent mới thay thế thành công planner subagent redundant bằng cách tận dụng deepagents' built-in planning, đồng thời thêm nhiều tính năng mới như stack detection, boilerplate retrieval, và LangChain PGVector indexing. 🎉
