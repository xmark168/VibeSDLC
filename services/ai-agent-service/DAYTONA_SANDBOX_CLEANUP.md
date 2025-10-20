# Daytona Sandbox Cleanup Integration

## Overview

Tính năng tự động xóa Daytona sandbox sau khi Implementor Agent hoàn thành sprint (workflow execution) để tránh lãng phí tài nguyên và chi phí.

## Architecture

### Components

1. **Daytona Client Utility** (`app/agents/developer/implementor/utils/daytona_client.py`)
   - `get_daytona_config()`: Lấy cấu hình Daytona từ environment variables
   - `delete_sandbox_sync()`: Xóa sandbox với retry logic và timeout
   - `should_delete_sandbox()`: Logic quyết định có nên xóa sandbox không

2. **State Management** (`app/agents/developer/implementor/state.py`)
   - `SandboxDeletion`: Model để track kết quả xóa sandbox
   - `ImplementorState.sandbox_deletion`: Field để lưu thông tin deletion

3. **Finalize Node** (`app/agents/developer/implementor/nodes/finalize.py`)
   - `_handle_sandbox_cleanup()`: Function xử lý cleanup logic
   - Tích hợp vào workflow cuối cùng trước khi kết thúc

## Workflow Integration

### Position in Workflow
```
START → initialize → setup_branch → [copy_boilerplate] → 
install_dependencies → generate_code → implement_files → 
run_tests → run_and_verify → commit_changes → create_pr → 
finalize (WITH SANDBOX CLEANUP) → END
```

### Cleanup Logic in Finalize Node

1. **Check Conditions**:
   - Chỉ xóa khi workflow hoàn thành thành công (`status` in `["completed", "pr_ready", "finalized"]`)
   - Chỉ xóa nếu có `sandbox_id` trong state
   - Bỏ qua việc xóa nếu workflow bị lỗi hoặc bị hủy (để có thể debug)

2. **Deletion Process**:
   - Sử dụng Daytona Python SDK với `daytona.delete(workspace_id)`
   - Retry logic: tối đa 2 lần retry với exponential backoff
   - Timeout: 60 giây cho toàn bộ quá trình deletion
   - Handle "not found" errors gracefully (sandbox đã bị xóa)

3. **Error Handling**:
   - Nếu xóa sandbox thất bại, chỉ log warning và tiếp tục finalize workflow
   - Không để lỗi xóa sandbox làm fail toàn bộ sprint
   - Record tất cả kết quả (success/failure) trong state

## Configuration

### Environment Variables

```bash
# Required for Daytona operations
DAYTONA_API_KEY=your-daytona-api-key-here
DAYTONA_API_URL=https://app.daytona.io/api  # Optional, defaults to this
DAYTONA_TARGET=us                           # Optional, defaults to 'us'
```

### Dependencies

- `daytona>=0.111.0`: Daytona Python SDK
- `asyncio`: For async operations
- `threading`: For sync wrapper

## Usage Examples

### Successful Workflow with Sandbox Cleanup

```python
# State before finalize
state = ImplementorState(
    sandbox_id="planner-myrepo-123",
    status="completed",
    implementation_complete=True,
    # ... other fields
)

# After finalize node
state.sandbox_deletion = SandboxDeletion(
    sandbox_id="planner-myrepo-123",
    success=True,
    message="Sandbox planner-myrepo-123 deleted successfully",
    retries_used=0,
    error="",
    skipped=False,
    skip_reason=""
)
```

### Failed Workflow (Sandbox Preserved)

```python
# State before finalize
state = ImplementorState(
    sandbox_id="planner-myrepo-456",
    status="error",
    error_message="Implementation failed",
    # ... other fields
)

# After finalize node
state.sandbox_deletion = SandboxDeletion(
    sandbox_id="planner-myrepo-456",
    success=False,
    message="Sandbox deletion skipped: Workflow not completed successfully (status: error)",
    retries_used=0,
    error="",
    skipped=True,
    skip_reason="Workflow not completed successfully (status: error)"
)
```

### No Sandbox ID (Local Development)

```python
# State before finalize
state = ImplementorState(
    sandbox_id="",  # No sandbox
    status="completed",
    # ... other fields
)

# After finalize node
state.sandbox_deletion = SandboxDeletion(
    sandbox_id="",
    success=False,
    message="Sandbox deletion skipped: No sandbox ID provided",
    retries_used=0,
    error="",
    skipped=True,
    skip_reason="No sandbox ID provided"
)
```

## State Tracking

### SandboxDeletion Model

```python
class SandboxDeletion(BaseModel):
    sandbox_id: str = ""           # ID của sandbox
    success: bool = False          # Có xóa thành công không
    message: str = ""              # Thông báo kết quả
    retries_used: int = 0          # Số lần retry đã sử dụng
    error: str = ""                # Error message nếu thất bại
    skipped: bool = False          # Có bị skip không
    skip_reason: str = ""          # Lý do skip
```

### Integration with Summary

```python
summary = {
    # ... other fields
    "sandbox_cleanup": {
        "attempted": True,
        "success": True,
        "skipped": False,
        "skip_reason": "",
        "error": ""
    }
}
```

## Benefits

1. **Resource Management**: Tự động cleanup sandbox resources sau khi hoàn thành
2. **Cost Optimization**: Tránh lãng phí chi phí cho sandbox không sử dụng
3. **Debugging Support**: Giữ lại sandbox khi có lỗi để debug
4. **Graceful Handling**: Không làm fail workflow nếu cleanup thất bại
5. **Comprehensive Logging**: Track tất cả kết quả cleanup trong state

## Testing

### Test Files

1. `test_daytona_minimal.py`: Test core logic without dependencies
2. `test_daytona_client_simple.py`: Test utility functions
3. `test_sandbox_cleanup.py`: Integration test with finalize node

### Test Coverage

- ✅ Sandbox deletion logic for different statuses
- ✅ Edge cases (None, empty, whitespace values)
- ✅ Success/failure scenarios
- ✅ Skip conditions
- ✅ State model validation
- ✅ Configuration handling

## Monitoring

### Logs

```
🧹 Checking for Daytona sandbox cleanup...
🗑️  Deleting Daytona sandbox: planner-myrepo-123
✅ Sandbox deleted successfully: Sandbox planner-myrepo-123 deleted successfully
```

### AI Messages

```
🎉 Implementation completed successfully!

**Summary:**
- Task: Implement JWT authentication
- Files Created: 3
- Files Modified: 2
- Branch: feature/jwt-auth
- Commit: abc123de
- Tests: ✅ Passed
- Sandbox: ✅ Cleaned up successfully
- Status: Ready for review
```

## Future Enhancements

1. **Configurable Cleanup Policy**: Allow users to configure when to cleanup
2. **Batch Cleanup**: Cleanup multiple sandboxes at once
3. **Cleanup Scheduling**: Schedule cleanup for later instead of immediate
4. **Resource Usage Tracking**: Track sandbox usage before cleanup
5. **Integration with Monitoring**: Send cleanup metrics to monitoring systems
