# Langfuse Integration - Quick Start Guide

## 🚀 Quick Start (5 phút)

### Bước 1: Verify Credentials

Kiểm tra file `.env` đã có credentials:

```bash
cat .env | grep LANGFUSE
```

Kết quả mong đợi:
```
LANGFUSE_HOST=https://langfuse.vibesdlc.com
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
```

✅ Nếu có đầy đủ → Tiếp tục bước 2
❌ Nếu thiếu → Thêm credentials vào `.env`

### Bước 2: Test Integration

Chạy test suite:

```bash
cd services/ai-agent-service
python test_langfuse_integration.py
```

Kết quả mong đợi:
```
✅ PASS - Client Initialization
✅ PASS - CallbackHandler Creation
✅ PASS - Manual Trace Span
✅ PASS - Developer Agent Execution
✅ PASS - Trace Visibility

Results: 5/5 tests passed
🎉 All tests passed!
```

### Bước 3: View Traces

1. Mở browser: https://langfuse.vibesdlc.com
2. Login với credentials
3. Navigate to "Traces"
4. Tìm trace với session ID: `test-langfuse-integration`

### Bước 4: Use in Your Code

```python
from app.agents.developer import run_developer

# Chỉ cần gọi như bình thường - tracing tự động!
result = await run_developer(
    user_request="Add user authentication",
    working_directory="./src",
)

# Hoặc với custom session ID
result = await run_developer(
    user_request="Add user authentication",
    working_directory="./src",
    session_id="my-feature-123",
    user_id="developer-john",
)
```

## 📊 What Gets Traced?

### Automatic (không cần code thêm)

✅ **LLM Calls**
- Model name, input, output
- Token usage, latency
- Cost tracking

✅ **Tool Executions**
- Tool name, parameters
- Results, timing
- Success/failure status

✅ **Agent Steps**
- Each step in workflow
- Actions and observations
- Decision making process

✅ **Errors**
- Error type and message
- Stack traces
- Failed operations

### Manual (optional, cho detailed tracking)

```python
from app.utils.langfuse_tracer import trace_span

with trace_span(
    name="custom_operation",
    metadata={"feature": "auth", "priority": "high"}
) as span:
    # Your code here
    result = do_something()
    
    # Optional: add output
    span.end(output={"result": result})
```

## 🔍 Common Use Cases

### Use Case 1: Debug Failed Execution

```python
try:
    result = await run_developer(
        user_request="Complex feature",
        working_directory="./src",
        session_id="debug-session-123",
    )
except Exception as e:
    print(f"Failed: {e}")
    print("Check Langfuse for details: session_id=debug-session-123")
```

→ Xem trace trong Langfuse để biết:
- Bước nào failed?
- Error message chi tiết
- Stack trace đầy đủ
- State tại thời điểm lỗi

### Use Case 2: Monitor Performance

```python
import time

start = time.time()
result = await run_developer(
    user_request="Add feature",
    working_directory="./src",
    session_id="perf-test-1",
)
print(f"Local time: {time.time() - start}s")
```

→ So sánh với timing trong Langfuse:
- Tổng execution time
- Time cho từng tool
- LLM latency
- Bottlenecks

### Use Case 3: Track Multiple Features

```python
features = [
    "Add user model",
    "Add user endpoints", 
    "Add user tests",
]

for i, feature in enumerate(features):
    result = await run_developer(
        user_request=feature,
        working_directory="./src",
        session_id=f"batch-{i+1}",
        user_id="developer-john",
    )
```

→ Filter trong Langfuse by:
- User ID: `developer-john`
- Session ID pattern: `batch-*`
- Date range

### Use Case 4: Compare Model Performance

```python
models = ["gpt-4o-mini", "gpt-4o"]

for model in models:
    result = await run_developer(
        user_request="Same task",
        working_directory="./src",
        model_name=model,
        session_id=f"model-comparison-{model}",
    )
```

→ Compare trong Langfuse:
- Execution time
- Token usage
- Cost
- Quality of output

## 📈 Dashboard Tips

### Filter Traces

```
Session ID: feature-auth-*
User ID: developer-john
Date: Last 7 days
Status: Error
```

### Analyze Metrics

1. **Execution Time**: Identify slow operations
2. **Token Usage**: Track costs
3. **Error Rate**: Monitor reliability
4. **Tool Usage**: See which tools are used most

### Create Views

Save common filters as views:
- "My Recent Executions"
- "Failed Executions"
- "Slow Executions (>60s)"
- "High Cost Executions"

## 🛠️ Troubleshooting

### Problem: No traces appearing

**Check:**
1. ✅ Credentials in `.env`
2. ✅ Network connectivity to Langfuse host
3. ✅ Console logs for errors
4. ✅ Wait a few seconds for traces to appear

**Solution:**
```bash
# Test connection
python -c "from app.utils.langfuse_tracer import get_langfuse_client; print('OK' if get_langfuse_client() else 'FAIL')"
```

### Problem: Traces incomplete

**Possible causes:**
- Agent crashed before flush
- Network timeout
- Rate limiting

**Solution:**
```python
from app.utils.langfuse_tracer import flush_langfuse

# Manually flush at end
try:
    result = await run_developer(...)
finally:
    flush_langfuse()
```

### Problem: Too much data

**Solution:**
Disable tracing temporarily:

```bash
# In .env, comment out credentials
# LANGFUSE_PUBLIC_KEY=
# LANGFUSE_SECRET_KEY=
```

Agent will still work, just without tracing.

## 📚 Learn More

- **Full Documentation**: `app/utils/LANGFUSE_INTEGRATION.md`
- **Examples**: `examples/langfuse_tracing_example.py`
- **Test Suite**: `test_langfuse_integration.py`
- **Summary**: `LANGFUSE_INTEGRATION_SUMMARY.md`

## 🎯 Best Practices

### DO ✅

- Use meaningful session IDs: `feature-auth-2024-01-15`
- Add metadata for context: `{"priority": "high", "team": "backend"}`
- Check traces after errors
- Monitor execution times
- Track costs

### DON'T ❌

- Don't use random session IDs: `abc123`
- Don't ignore error traces
- Don't forget to flush in long-running processes
- Don't log sensitive data in metadata

## 🚦 Status Indicators

### Console Output

```
✅ Langfuse client initialized successfully
✅ Langfuse tracing enabled for session: my-session
📊 Langfuse tracing: Session my-session
🚀 Starting developer agent execution...
✅ Developer agent execution completed in 45.67s
✅ Langfuse traces flushed successfully
```

### What They Mean

- ✅ Green checkmark: Success
- ⚠️ Warning triangle: Non-critical issue
- ❌ Red X: Error
- 📊 Chart: Tracing info
- 🚀 Rocket: Starting operation

## 💡 Pro Tips

1. **Use consistent naming**: `feature-{name}-{date}`
2. **Add user context**: Always set `user_id` for team tracking
3. **Review daily**: Check traces at end of day
4. **Set up alerts**: For errors and slow executions
5. **Share traces**: Use session IDs to share with team

## ✨ That's It!

Bạn đã sẵn sàng sử dụng Langfuse tracing!

**Next steps:**
1. ✅ Run test suite
2. ✅ Try basic example
3. ✅ Check dashboard
4. ✅ Use in your development workflow

**Questions?**
- Check documentation in `app/utils/LANGFUSE_INTEGRATION.md`
- Run examples in `examples/langfuse_tracing_example.py`
- Review test suite in `test_langfuse_integration.py`

Happy tracing! 🎉

