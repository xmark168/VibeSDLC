# VibeSDLC Agent System

MetaGPT-inspired multi-agent system với single process, in-memory message passing.

## Cấu trúc

```
app/agents/
├── base/                      # Base classes
│   ├── message.py            # Message, MessageQueue, Memory
│   ├── role.py               # Role base class (Observe-Think-Act)
│   ├── action.py             # Action base class
│   └── environment.py        # Environment orchestrator
├── implementations/           # Agent implementations
│   ├── team_leader.py        # TeamLeaderAgent
│   ├── business_analyst.py   # BusinessAnalystAgent
│   ├── developer.py          # DeveloperAgent
│   └── tester.py             # TesterAgent
├── team.py                   # AgentTeam orchestrator
└── __main__.py               # Entry point
```

## Khởi động

### Start tất cả agents:
```bash
python -m app.agents
```

### Sử dụng trong code:
```python
from app.agents.team import AgentTeam
from app.agents.implementations import TeamLeaderAgent, DeveloperAgent

# Create team
team = AgentTeam()

# Hire agents
team.hire([
    TeamLeaderAgent(),
    DeveloperAgent(),
])

# Start with initial message
await team.start("Build a login feature", n_round=10)

# Get history
history = team.get_history()
```

## Cách hoạt động

### 1. Watch Pattern (Reactive)

Agents tự động react khi có message phù hợp:

```python
class DeveloperAgent(Role):
    def __init__(self):
        super().__init__(name="Developer")
        self._watch([WritePRD])  # React khi BA xong PRD
```

### 2. Observe-Think-Act Cycle

Mỗi agent theo vòng lặp:
1. **Observe**: Check message buffer, filter theo watch list
2. **Think**: Decide action ti���p theo
3. **Act**: Execute action
4. **Publish**: Share kết quả

### 3. Message Flow

```
User → UserRequest Message
   ↓
TeamLeader observes → analyzes → delegates
   ↓
BA observes delegation → creates PRD
   ↓
Developer observes PRD → writes code
   ↓
Tester observes code → creates tests
```

## Tạo Agent Mới

```python
from app.agents.base import Role, Action, Message

# 1. Define action
class MyAction(Action):
    async def run(self, context):
        result = "Do something with " + str(context)
        return result

# 2. Define agent
class MyAgent(Role):
    def __init__(self):
        super().__init__(name="MyAgent")
        self.set_actions([MyAction()])
        self._watch([SomeOtherAction])  # React to this

    async def _act(self) -> Message:
        result = await self.rc.todo.run(self.rc.memory.get(k=1))
        return Message(
            content=result,
            cause_by=type(self.rc.todo),
            sent_from=self.name
        )

# 3. Add to team
team.hire([MyAgent()])
```

## Configuration

Agents load config từ `app/crews/config/agents_config.yaml`:

```yaml
team_leader:
  model: "openai/gpt-4.1"
  role: "Team Leader"
  # ...
```

## Advantages

✅ **Đơn giản**: Single process, no Kafka complexity
✅ **Auto-start**: 1 command khởi động tất cả
✅ **Watch pattern**: Agents tự động react
✅ **Memory efficient**: Shared memory, no serialization
✅ **Fast**: In-memory message passing
✅ **Easy debug**: Breakpoints work normally

## Deployment

### Development:
```bash
python -m app.agents
```

### Production (Docker):
```dockerfile
CMD ["python", "-m", "app.agents"]
```

### Systemd:
```ini
[Service]
ExecStart=/usr/bin/python3 -m app.agents
```

## Example: Full Workflow

```python
import asyncio
from app.agents.team import AgentTeam
from app.agents.implementations import *

async def example():
    team = AgentTeam()

    team.hire([
        TeamLeaderAgent(),
        BusinessAnalystAgent(),
        DeveloperAgent(),
        TesterAgent(),
    ])

    # Start workflow
    history = await team.start(
        "Build a REST API for user authentication",
        n_round=10
    )

    # Print results
    for msg in history:
        print(f"{msg.sent_from}: {msg.content[:100]}...")

asyncio.run(example())
```

## Notes

- Agents chạy trong cùng process với asyncio
- Communication qua in-memory message queue
- Không cần Kafka/Redis cho basic usage
- Có thể tích hợp Kafka sau nếu cần scale

## Migration từ Old System

Old isolated agents (Kafka-based) đã được archived.
New system đơn giản hơn, phù hợp cho LLM agents (I/O bound).
