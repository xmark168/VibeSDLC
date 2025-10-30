# Langfuse Integration for Developer Agent

## Tổng quan

Langfuse đã được tích hợp vào Developer Agent để monitor và trace toàn bộ flow thực thi. Tích hợp này cung cấp:

- **Automatic Tracing**: Tự động trace tất cả LLM calls và tool executions thông qua CallbackHandler
- **Manual Tracing**: Trace chi tiết các bước workflow quan trọng
- **Metadata Capture**: Capture input/output, timing, errors, và agent state
- **Session Management**: Theo dõi các session execution riêng biệt
- **Error Tracking**: Tự động log errors và exceptions

## Cấu hình

### Environment Variables

Thêm các biến sau vào file `.env`:

```env
LANGFUSE_HOST=https://langfuse.vibesdlc.com
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
```

Nếu không có credentials, tracing sẽ tự động bị disable và agent vẫn hoạt động bình thường.

## Sử dụng

### Basic Usage

```python
from app.agents.developer import run_developer

# Run agent với tracing tự động
result = await run_developer(
    user_request="Add user authentication",
    working_directory="./src",
    session_id="dev-session-123",  # Optional: custom session ID
    user_id="developer-1",          # Optional: user identifier
)
```

### Session Management

Nếu không cung cấp `session_id`, một ID ngẫu nhiên sẽ được tạo tự động:

```python
# Auto-generated session ID
result = await run_developer(
    user_request="Add user authentication",
    working_directory="./src",
)
# Session ID format: dev-{uuid}
```

### Custom Tracing

Để thêm custom traces trong code của bạn:

```python
from app.utils.langfuse_tracer import trace_span, log_agent_state

# Trace một code block
with trace_span(
    name="custom_operation",
    metadata={"operation_type": "analysis"},
    input_data={"param": "value"}
) as span:
    result = perform_operation()
    
    # Optionally update span with output
    if span:
        span.end(output={"result": result})

# Log agent state
log_agent_state(
    state=agent_state,
    phase="planning",
    trace_id="optional-trace-id"
)
```

## Traced Components

### Automatic Tracing (via CallbackHandler)

Các component sau được trace tự động:

1. **LLM Calls**: Tất cả calls đến ChatOpenAI
2. **Tool Executions**: Tất cả tool calls từ agent
3. **Agent Steps**: Mỗi bước trong agent workflow
4. **Subagent Calls**: Calls đến code_generator_subagent

### Manual Tracing

Các workflow phases được trace thủ công:

1. **Initialization**: Agent setup và initial state
2. **Execution**: Main agent execution với timing
3. **Completion**: Final state và results
4. **Errors**: Exception handling và error details

### Traced Tools

Các tools quan trọng có enhanced tracing (optional):

- `load_codebase_tool` - Codebase analysis
- `create_feature_branch_tool` - Git branch creation
- `commit_changes_tool` - Git commits
- `generate_code_tool` - Code generation
- `select_integration_strategy_tool` - Strategy selection
- `sync_virtual_to_disk_tool` - File system sync
- `collect_feedback_tool` - Feedback collection
- `refine_code_tool` - Code refinement

## Viewing Traces

### Langfuse Dashboard

1. Truy cập: https://langfuse.vibesdlc.com
2. Login với credentials
3. Navigate to "Traces" section
4. Filter by:
   - Session ID
   - User ID
   - Date range
   - Status (success/error)

### Trace Information

Mỗi trace bao gồm:

- **Metadata**:
  - Session ID
  - User ID
  - Working directory
  - Project type
  - Model name
  - User request

- **Timing**:
  - Start time
  - End time
  - Duration
  - Individual step timings

- **State Information**:
  - Initial state
  - Intermediate states
  - Final state
  - Todos progress
  - Generated files count
  - Commit count

- **Errors**:
  - Error type
  - Error message
  - Stack trace
  - Failed step

## Architecture

### Components

```
┌─────────────────────────────────────────┐
│         Developer Agent                 │
│  (with Langfuse CallbackHandler)        │
└─────────────────┬───────────────────────┘
                  │
                  ├─► Automatic Tracing
                  │   - LLM calls
                  │   - Tool executions
                  │   - Agent steps
                  │
                  └─► Manual Tracing
                      - Workflow phases
                      - State logging
                      - Error tracking
                      │
                      ▼
            ┌─────────────────┐
            │  Langfuse API   │
            └─────────────────┘
                      │
                      ▼
            ┌─────────────────┐
            │ Langfuse Dashboard│
            └─────────────────┘
```

### Files

- `app/utils/langfuse_tracer.py` - Core tracing utilities
- `app/agents/developer/agent.py` - Agent with tracing integration
- `app/agents/developer/implementor/tools/traced_tools.py` - Enhanced tool tracing (optional)

## Best Practices

### 1. Use Meaningful Session IDs

```python
# Good: Descriptive session ID
session_id = f"feature-auth-{timestamp}"

# Bad: Random or unclear ID
session_id = "abc123"
```

### 2. Add Relevant Metadata

```python
with trace_span(
    name="operation",
    metadata={
        "feature": "authentication",
        "environment": "development",
        "version": "1.0.0",
    }
):
    # ... operation
```

### 3. Handle Errors Gracefully

Tracing không nên làm gián đoạn agent execution. Tất cả tracing code đã được wrap với try-except.

### 4. Flush Traces

Traces được flush tự động ở cuối execution, nhưng bạn có thể flush thủ công:

```python
from app.utils.langfuse_tracer import flush_langfuse

flush_langfuse()
```

## Troubleshooting

### Traces không xuất hiện

1. Kiểm tra credentials trong `.env`
2. Kiểm tra network connectivity đến Langfuse host
3. Xem console logs cho warnings/errors
4. Verify Langfuse client initialization:
   ```
   ✅ Langfuse client initialized successfully
   ```

### Performance Impact

Langfuse tracing có minimal performance impact:
- Async logging không block execution
- Automatic batching của events
- Configurable flush intervals

### Disable Tracing

Để tạm thời disable tracing:

```python
# Option 1: Remove credentials từ .env
# Option 2: Set empty values
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
```

Agent sẽ tự động detect và disable tracing.

## Advanced Usage

### Custom Trace Decorators

```python
from app.utils.langfuse_tracer import trace_function

@trace_function(
    name="custom_function",
    capture_input=True,
    capture_output=True,
    metadata={"type": "analysis"}
)
def my_function(param1, param2):
    # Function implementation
    return result
```

### Nested Traces

```python
with trace_span("parent_operation") as parent:
    # Parent operation
    
    with trace_span(
        "child_operation",
        parent_observation_id=parent.id if parent else None
    ):
        # Child operation
```

### Conditional Tracing

```python
from app.utils.langfuse_tracer import _langfuse_client

if _langfuse_client:
    # Tracing is enabled
    with trace_span("operation"):
        # ... traced operation
else:
    # Tracing is disabled
    # ... operation without tracing
```

## Monitoring Metrics

### Key Metrics to Track

1. **Execution Time**: Total agent execution duration
2. **Tool Usage**: Frequency and duration of tool calls
3. **Success Rate**: Percentage of successful executions
4. **Error Rate**: Frequency and types of errors
5. **LLM Costs**: Token usage and costs per execution
6. **Workflow Efficiency**: Time spent in each phase

### Dashboard Views

Create custom views in Langfuse for:
- Daily execution trends
- Error analysis
- Performance bottlenecks
- Cost tracking
- User activity

## Support

Để được hỗ trợ:
1. Check console logs cho error messages
2. Review Langfuse dashboard cho trace details
3. Verify environment configuration
4. Contact team nếu cần thiết

## Future Enhancements

Planned improvements:
- [ ] Custom metrics tracking
- [ ] Performance benchmarking
- [ ] Cost optimization insights
- [ ] Automated alerting
- [ ] Integration với monitoring tools khác

