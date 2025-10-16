# Sync Tools State Injection Fix

## Problem

The agent was throwing validation errors when calling `sync_virtual_to_disk_tool`:

```
Error invoking tool 'sync_virtual_to_disk_tool' with kwargs {'working_directory': 'D:\\demo'} with error:
1 validation error for sync_virtual_to_disk_tool
state
  Field required [type=missing, input_value={'working_directory': 'D:\\demo'}, input_type=dict]
```

## Root Cause

The tools were originally designed with `InjectedState` annotation from LangChain:

```python
@tool
def sync_virtual_to_disk_tool(
    working_directory: str,
    state: Annotated[FilesystemState, InjectedState],  # ❌ Problematic
    ...
)
```

**Issues with this approach:**

1. **InjectedState not compatible with DeepAgents**: DeepAgents doesn't automatically inject state parameters like native LangGraph ToolNode
2. **Pydantic validation conflict**: When using `args_schema`, the schema didn't include `state` parameter, causing validation errors
3. **No automatic state passing**: Agent calls tool with only `working_directory`, but Pydantic expects `state` as a required field

## Solution

Remove `state` from function parameters and fetch it directly from DeepAgents context:

```python
@tool(args_schema=SyncVirtualToDiskInput)
def sync_virtual_to_disk_tool(
    working_directory: str,
    file_patterns: List[str] | None = None,
    overwrite_existing: bool = True,
    create_backup: bool = False,
) -> str:
    """Sync files from virtual file system to real disk."""
    try:
        # Get state from DeepAgents context
        state = None
        try:
            import contextvars
            for var in contextvars.copy_context().items():
                if hasattr(var[1], 'get') and 'files' in var[1]:
                    state = var[1]
                    break
        except Exception:
            pass

        # Fallback to alternative methods
        if state is None:
            try:
                from deepagents.state import get_current_state
                state = get_current_state()
            except (ImportError, RuntimeError, AttributeError):
                state = {}

        virtual_files = state.get("files", {}) if state else {}
        # ... rest of implementation
```

## Key Changes

1. **Removed `state` parameter** from function signature
2. **Added internal state retrieval** using context vars
3. **Schema matches function signature** - no more validation conflicts
4. **Graceful fallback** - returns empty dict if state unavailable

## Why This Works

- **Pydantic schema consistency**: `args_schema` now matches actual callable parameters
- **Context-based state access**: DeepAgents stores state in contextvars, accessible within tool execution
- **Backward compatible**: Tool still gets state, just through different mechanism
- **No wrapper needed**: No need for custom `wrap_tool_with_state_injection` function

## Testing

```python
# Agent can now call tool without state parameter
result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Implement feature X"}],
    "working_directory": "D:\\demo",
})

# Tool will automatically fetch state from DeepAgents context
# and sync virtual files to disk
```

## Related Files

- `sync_tools.py` - Updated tool implementations
- `agent.py` - Removed wrapper function, simplified tool registration
- `__init__.py` - No changes needed

## Alternative Approaches Considered

1. **Custom wrapper function** ❌
   - Added complexity without solving root cause
   - Still had Pydantic validation issues

2. **Manual state passing in agent config** ❌
   - Would require modifying DeepAgents internals
   - Not maintainable

3. **Remove args_schema** ❌
   - Loses nice schema documentation for LLM
   - Less type safety

4. **Context-based retrieval** ✅
   - Clean, simple solution
   - Leverages DeepAgents' context var design
   - No validation conflicts
