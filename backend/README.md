# VibeSDLC Backend Service

Backend API service with auto-scaling multiprocessing agent pools.

## Tech Stack

- **FastAPI** - Modern async Python web framework
- **PostgreSQL** - Primary database
- **PgBouncer** - Connection pooler for PostgreSQL
- **Redis** - Agent pool coordination & IPC
- **Kafka** - Event streaming for agent communication
- **SQLModel** - ORM with Pydantic integration
- **Multiprocessing** - Auto-scaling worker processes

## Architecture

### Multiprocessing Agent Pools

```
┌─────────────────────────────────────┐
│ FastAPI Master Process              │
│  ├─ AgentPoolManager (per role)     │
│  ├─ Redis Client (IPC)              │
│  └─ API Endpoints                   │
└─────────────────────────────────────┘
           ↓ spawn via multiprocessing
┌─────────────────────────────────────┐
│ Worker Process 1                    │
│  ├─ AgentPool (max 10 agents)       │
│  ├─ Redis Listener                  │
│  └─ Own Event Loop                  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ Worker Process 2 (auto-spawned)     │
│  └─ ... (when Process 1 reaches 10) │
└─────────────────────────────────────┘
```

**Auto-Scaling**: When a pool reaches 10 agents, a new worker process is automatically spawned.

## Quick Start

### 1. Prerequisites

- Python 3.13+
- Docker & Docker Compose
- uv (Python package manager)

### 2. Start Infrastructure

```bash
# From project root (VibeSDLC/)
docker-compose up -d

# This starts:
# - PostgreSQL (port 5432)
# - PgBouncer (port 6432)
# - Redis (port 6379)
# - Kafka + Zookeeper (ports 9092, 2181)
# - Redis Commander UI (port 8081)
# - Kafka UI (port 8080)
```

### 3. Configure Environment

```bash
cd backend

# Copy example env file
cp ../.env.docker.example ../.env.docker

# Update .env file in backend/
# Key settings:
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vibeSDLC_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=vibeSDLC

# PgBouncer connection (recommended for production)
PGBOUNCER_URL=postgresql+psycopg://vibeSDLC_user:your_password@localhost:6432/vibeSDLC

# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 4. Install Dependencies

```bash
# Install dependencies with uv
uv sync
```

### 5. Run Database Migrations

```bash
# Create/update database schema
uv run alembic upgrade head
```

### 6. Start Backend Server

```bash
# Development mode (with auto-reload)
uv run dev.py

# Or manually with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify Startup

Check logs for successful initialization:

```
Initializing Redis for multiprocessing agent pools...
✓ Redis connected successfully
✓ Created manager: team_leader_pool (team_leader)
✓ Created manager: business_analyst_pool (business_analyst)
✓ Created manager: developer_pool (developer)
✓ Created manager: tester_pool (tester)
```

## API Endpoints

### Agent Management

```bash
# Spawn agent (auto-scales workers)
POST /api/v1/agents/spawn
{
  "project_id": "uuid",
  "role_type": "developer",
  "pool_name": "developer_pool",
  "heartbeat_interval": 30,
  "max_idle_time": 300
}

# Terminate agent
POST /api/v1/agents/terminate
{
  "pool_name": "developer_pool",
  "agent_id": "uuid",
  "graceful": true
}

# Get project agents
GET /api/v1/agents/project/{project_id}
```

### Pool Management

```bash
# List all pools
GET /api/v1/agents/pools

# Get specific pool stats
GET /api/v1/agents/pools/{pool_name}

# Create new pool
POST /api/v1/agents/pools
{
  "role_type": "developer",
  "pool_name": "custom_pool",
  "config": {
    "max_agents": 10,
    "health_check_interval": 60
  }
}

# Delete pool
DELETE /api/v1/agents/pools/{pool_name}?graceful=true
```

### Monitoring

```bash
# System stats
GET /api/v1/agents/monitor/system

# Dashboard data
GET /api/v1/agents/monitor/dashboard

# Agent health
GET /api/v1/agents/health
```

## Development

### Database Migrations

```bash
# Create new migration
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1
```

### Testing

```bash
# Run tests
uv run pytest

# Run specific test
uv run python app/tests/test_agent.py
```

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy app/
```

## Monitoring & Debugging

### Check Infrastructure

```bash
# PostgreSQL
psql -h localhost -p 5432 -U vibeSDLC_user vibeSDLC

# PgBouncer stats
psql -h localhost -p 6432 -U vibeSDLC_user pgbouncer -c "SHOW POOLS;"

# Redis
redis-cli ping
redis-cli KEYS "agent:*"  # All agents
redis-cli KEYS "process:*"  # All workers
redis-cli ZRANGE "pool:developer_pool:processes" 0 -1 WITHSCORES  # Pool capacity

# Kafka
kafka-console-consumer --bootstrap-server localhost:9092 --topic user_messages --from-beginning
```

### Web UIs

- **Redis Commander**: http://localhost:8081
- **Kafka UI**: http://localhost:8080
- **API Docs**: http://localhost:8000/docs

### Monitor Worker Processes

```bash
# List Python processes
tasklist /FI "IMAGENAME eq python.exe"  # Windows
ps aux | grep python  # Linux/Mac

# Watch Redis pub/sub
redis-cli
> SUBSCRIBE "pool:developer_pool:commands"
# Then spawn agent and watch messages
```

## Troubleshooting

### Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis
redis-cli ping  # Should return PONG

# Check connection
telnet localhost 6379
```

**Fix**:
```bash
docker-compose restart redis
# Or
docker-compose up -d redis
```

### Workers Not Spawning

**Symptoms**: Spawn request succeeds but no worker processes appear

**Debug**:
1. Check Redis pub/sub:
   ```bash
   redis-cli
   > SUBSCRIBE "pool:developer_pool:commands"
   ```
2. Check manager logs for spawn failures
3. Verify system resources (CPU, RAM)

**Fix**:
- Restart backend service
- Check multiprocessing module compatibility (Windows may have limitations)

### Database Connection Exhausted

**Error**: `FATAL: sorry, too many clients already`

**Fix**: Use PgBouncer (already configured in docker-compose)

Update backend `.env`:
```bash
# Use PgBouncer instead of direct PostgreSQL
SQLALCHEMY_DATABASE_URI=postgresql+psycopg://vibeSDLC_user:password@localhost:6432/vibeSDLC
```

### Agent Stuck in "spawning" State

**Symptoms**: Agent created in DB but never reaches "idle"

**Debug**:
```bash
# Check Redis registry
redis-cli HGETALL "agent:<agent_id>"

# Check worker process count
redis-cli ZRANGE "pool:developer_pool:processes" 0 -1
```

**Fix**:
1. Check worker logs for errors
2. Manually update agent status in DB:
   ```sql
   UPDATE agents SET status = 'idle' WHERE id = '<agent_id>';
   ```
3. Or terminate and respawn:
   ```bash
   POST /api/v1/agents/terminate
   POST /api/v1/agents/spawn
   ```

## Performance Tuning

### Redis

```bash
# Increase maxmemory (if needed)
redis-cli CONFIG SET maxmemory 1gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### PgBouncer

Edit `/etc/pgbouncer/pgbouncer.ini`:
```ini
# Increase pool size for high concurrency
default_pool_size = 50
reserve_pool_size = 10

# Or in docker-compose.yml:
environment:
  DEFAULT_POOL_SIZE: 50
  RESERVE_POOL_SIZE: 10
```

### Worker Scaling

Adjust max_agents_per_process:

```python
# In agent_management.py: initialize_default_pools()
manager = AgentPoolManager(
    pool_name=pool_name,
    role_class=role_class,
    max_agents_per_process=20,  # Increase from default 10
    heartbeat_interval=30,
)
```

**Trade-offs**:
- Higher = Fewer processes, less overhead
- Lower = More processes, better CPU parallelism

## Utilities

### Kill Stuck Processes

```bash
# Windows
tasklist /FI "IMAGENAME eq python.exe"
taskkill /PID <pid> /F

# Linux/Mac
pkill -f "python.*uvicorn"
pkill -f "agent_pool_worker"
```

### Clear Redis Data

```bash
# WARNING: Deletes all data
redis-cli FLUSHALL

# Selective delete
redis-cli DEL "agent:*"
redis-cli DEL "process:*"
```

### Reset Database

```bash
# Drop all tables
uv run alembic downgrade base

# Recreate
uv run alembic upgrade head
```

## Project Structure

```
backend/
├── app/
│   ├── agents/
│   │   ├── core/
│   │   │   ├── agent_pool.py          # Single-process pool
│   │   │   ├── agent_pool_manager.py  # Multiprocessing manager
│   │   │   ├── agent_pool_worker.py   # Worker process
│   │   │   ├── redis_client.py        # Redis integration
│   │   │   └── registry.py            # Agent/Process tracking
│   │   └── roles/                     # Agent role implementations
│   ├── api/
│   │   └── routes/
│   │       └── agent_management.py    # API endpoints
│   ├── core/
│   │   ├── config.py                  # Settings
│   │   └── db.py                      # Database connection
│   ├── models/                        # SQLModel models
│   └── main.py                        # FastAPI app
├── alembic/                           # Database migrations
├── tests/                             # Test suite
├── docker-compose.yml                 # Infrastructure
├── pyproject.toml                     # Dependencies
└── README.md                          # This file
```

## Additional Documentation

- **Multiprocessing Setup**: `MULTIPROCESSING_SETUP.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`

## Support

For issues:
1. Check logs in FastAPI console
2. Check `MULTIPROCESSING_SETUP.md` troubleshooting section
3. Monitor Redis: `redis-cli MONITOR`
4. Check worker logs (stdout/stderr of worker processes)

## License

Proprietary - VibeSDLC Project
