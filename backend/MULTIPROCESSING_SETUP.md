# Agent Pool Multiprocessing Setup Guide

This document explains how to configure and use the auto-scaling agent pool system with multiprocessing.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ FastAPI Process (Master)                                │
│  ├─ AgentPoolManager - manages worker processes         │
│  ├─ Redis Client - shared state & IPC                   │
│  └─ API Endpoints - spawn/terminate/monitor             │
└─────────────────────────────────────────────────────────┘
                    ↓ (spawn via multiprocessing)
┌─────────────────────────────────────────────────────────┐
│ Worker Process 1 (AgentPoolWorker)                      │
│  ├─ AgentPool (10 agents max)                           │
│  ├─ Redis Client - receive IPC commands                 │
│  ├─ Own DB engine via PgBouncer                         │
│  └─ Own asyncio event loop                              │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ Worker Process 2 (auto-spawned when Process 1 full)     │
│  └─ ... (same structure)                                 │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Redis

Redis is required for:
- Shared state (agent registry, process registry)
- Inter-process communication (pub/sub)
- Distributed locking

#### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Windows (using Docker):**
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

**Docker Compose (recommended for development):**

Create `docker-compose.redis.yml`:
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: vibesd lc-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  redis-data:
```

Start Redis:
```bash
docker-compose -f docker-compose.redis.yml up -d
```

### 2. PgBouncer (Optional but Recommended)

PgBouncer is a connection pooler for PostgreSQL that manages database connections efficiently when using multiple worker processes.

#### Why PgBouncer?

Without PgBouncer:
- Each worker process creates its own connection pool (default 5 connections)
- With 10 workers: 10 × 5 = 50 database connections
- PostgreSQL default max_connections: 100
- Risk of exhausting connections quickly

With PgBouncer:
- All workers connect to PgBouncer (local, fast)
- PgBouncer manages a single connection pool to PostgreSQL
- Can handle 100+ worker connections with only 10-20 PostgreSQL connections

#### Installation

**Ubuntu/Debian:**
```bash
sudo apt install pgbouncer
```

**macOS:**
```bash
brew install pgbouncer
```

**Docker:**
```bash
docker run -d \
  --name pgbouncer \
  -p 6432:6432 \
  -e DATABASES_HOST=your_postgres_host \
  -e DATABASES_PORT=5432 \
  -e DATABASES_USER=your_user \
  -e DATABASES_PASSWORD=your_password \
  -e DATABASES_DBNAME=vibesd lc \
  pgbouncer/pgbouncer:latest
```

#### Configuration

Create `/etc/pgbouncer/pgbouncer.ini`:

```ini
[databases]
vibesd lc = host=localhost port=5432 dbname=vibesd lc

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = session
max_client_conn = 200
default_pool_size = 20
reserve_pool_size = 5
reserve_pool_timeout = 5
```

Create `/etc/pgbouncer/userlist.txt`:
```
"your_user" "md5<md5_hash_of_password>"
```

Generate MD5 hash:
```bash
echo -n "passwordyour_user" | md5sum
```

Start PgBouncer:
```bash
pgbouncer -d /etc/pgbouncer/pgbouncer.ini
```

#### Docker Compose (Full Stack)

Create `docker-compose.full.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: vibesd lc-postgres
    environment:
      POSTGRES_USER: vibesd lc_user
      POSTGRES_PASSWORD: your_password
      POSTGRES_DB: vibesd lc
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    restart: unless-stopped

  pgbouncer:
    image: pgbouncer/pgbouncer:latest
    container_name: vibesd lc-pgbouncer
    environment:
      DATABASES_HOST: postgres
      DATABASES_PORT: 5432
      DATABASES_USER: vibesd lc_user
      DATABASES_PASSWORD: your_password
      DATABASES_DBNAME: vibesd lc
      POOL_MODE: session
      MAX_CLIENT_CONN: 200
      DEFAULT_POOL_SIZE: 20
    ports:
      - "6432:6432"
    depends_on:
      - postgres
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: vibesd lc-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

volumes:
  postgres-data:
  redis-data:
```

## Environment Configuration

Update your `.env` file:

```bash
# ===== Existing PostgreSQL Connection =====
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vibesd lc_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=vibesd lc

# ===== PgBouncer Connection (Optional) =====
# If using PgBouncer, workers will use this instead of direct PostgreSQL
# Format: postgresql+psycopg://user:password@host:port/dbname
PGBOUNCER_URL=postgresql+psycopg://vibesd lc_user:your_password@localhost:6432/vibesd lc

# ===== Redis Connection =====
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=  # Leave empty if no password
REDIS_DB=0

# Alternative: Redis URL (overrides individual settings)
# REDIS_URL=redis://localhost:6379/0
# REDIS_URL=redis://:password@localhost:6379/0  # With password
```

## Usage

### Enable/Disable Multiprocessing

In `backend/app/api/routes/agent_management.py`:

```python
# Line 109
USE_MULTIPROCESSING = True   # Enable multiprocessing mode
# USE_MULTIPROCESSING = False  # Fallback to single-process mode
```

### Starting the System

1. **Start infrastructure:**
   ```bash
   # Using Docker Compose
   docker-compose -f docker-compose.full.yml up -d

   # Or start services individually
   # Redis
   redis-server

   # PgBouncer (if using)
   pgbouncer -d /etc/pgbouncer/pgbouncer.ini
   ```

2. **Start FastAPI application:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

3. **Verify startup:**
   Check logs for:
   ```
   Initializing Redis for multiprocessing mode...
   ✓ Connected to Redis successfully
   ✓ Auto-created manager: team_leader_pool (team_leader) [multiprocessing mode]
   ✓ Auto-created manager: business_analyst_pool (business_analyst) [multiprocessing mode]
   ✓ Auto-created manager: developer_pool (developer) [multiprocessing mode]
   ✓ Auto-created manager: tester_pool (tester) [multiprocessing mode]
   ```

### Auto-Scaling Behavior

**Trigger:** When a pool reaches max_agents (default: 10) in current worker process

**Action:** Automatically spawns a new worker process

**Example:**
```
Request: Spawn agent #11 in developer_pool

Current state:
- Worker Process 1: 10/10 agents (FULL)

Auto-scaling:
1. Manager detects all workers are at capacity
2. Manager spawns Worker Process 2
3. Agent #11 spawns in Worker Process 2

New state:
- Worker Process 1: 10/10 agents
- Worker Process 2: 1/10 agents
```

### Monitoring

**Check pool stats:**
```bash
curl http://localhost:8000/api/v1/agents/pools
```

Response:
```json
[
  {
    "pool_name": "developer_pool",
    "process_count": 2,
    "total_capacity": 20,
    "used_capacity": 11,
    "available_capacity": 9,
    "agent_count": 11,
    "utilization": 0.55,
    "active_worker_processes": 2
  }
]
```

**Check Redis registry:**
```bash
# All agents
redis-cli KEYS "agent:*"

# All worker processes
redis-cli KEYS "process:*"

# Agents in a specific pool
redis-cli SMEMBERS "pool:developer_pool:agents"

# Processes in a specific pool (sorted by capacity)
redis-cli ZREVRANGE "pool:developer_pool:processes" 0 -1 WITHSCORES
```

**Check PgBouncer stats:**
```bash
psql -h localhost -p 6432 -U vibesd lc_user pgbouncer -c "SHOW POOLS;"
psql -h localhost -p 6432 -U vibesd lc_user pgbouncer -c "SHOW STATS;"
```

## Troubleshooting

### Redis Connection Failed

**Error:** `Failed to connect to Redis`

**Solutions:**
1. Check Redis is running: `redis-cli ping` → should return `PONG`
2. Verify REDIS_HOST and REDIS_PORT in `.env`
3. Check firewall: `telnet localhost 6379`
4. Check Redis logs: `journalctl -u redis`

### Worker Processes Not Spawning

**Symptoms:** Spawn fails when pool reaches capacity

**Debug:**
1. Check manager logs for spawn failures
2. Verify Redis pub/sub: `redis-cli SUBSCRIBE "pool:developer_pool:commands"`
3. Check system resource limits: `ulimit -a`
4. On Windows: Ensure Python multiprocessing works (may need `if __name__ == '__main__'`)

### Database Connection Exhaustion

**Error:** `FATAL: remaining connection slots are reserved`

**Solutions:**
1. **Use PgBouncer** (recommended)
2. Increase PostgreSQL max_connections:
   ```sql
   ALTER SYSTEM SET max_connections = 200;
   SELECT pg_reload_conf();
   ```
3. Reduce worker pool size in `db.py`:
   ```python
   worker_engine = create_engine(db_url, pool_size=3, max_overflow=5)
   ```

### Workers Not Receiving Commands

**Symptoms:** Spawn command sent but agent not created

**Debug:**
1. Check Redis pub/sub subscription:
   ```bash
   redis-cli
   > SUBSCRIBE "pool:developer_pool:commands"
   ```

   Then spawn agent and watch for messages

2. Check worker logs for command processing
3. Verify target_process_id matches running process:
   ```bash
   redis-cli ZRANGE "pool:developer_pool:processes" 0 -1
   ```

### Stale Worker Processes

**Symptoms:** Process count increases but workers are not responding

**Solution:**
The manager automatically cleans up stale processes (no heartbeat for 5 minutes).

Manual cleanup:
```bash
# Find stale processes
redis-cli KEYS "process:*"

# Check last heartbeat
redis-cli HGET "process:<process_id>" "last_heartbeat"

# Delete stale process
redis-cli DEL "process:<process_id>"
redis-cli ZREM "pool:developer_pool:processes" "<process_id>"
```

## Performance Tuning

### Redis

Increase max memory and enable persistence:
```bash
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET save "900 1 300 10 60 10000"
```

### PgBouncer

Tune pool sizes based on load:
```ini
# For high concurrency
default_pool_size = 50
reserve_pool_size = 10

# For memory-constrained systems
default_pool_size = 10
reserve_pool_size = 3
```

### Worker Configuration

Adjust max_agents_per_process:
```python
# In agent_management.py: initialize_default_pools()
manager = AgentPoolManager(
    pool_name=pool_name,
    role_class=role_class,
    max_agents_per_process=20,  # Increase for more agents per worker
    heartbeat_interval=30,
)
```

**Trade-offs:**
- **Higher max_agents_per_process:** Fewer processes, less overhead, but less parallelism
- **Lower max_agents_per_process:** More processes, better CPU utilization, but more overhead

## Fallback to Single-Process Mode

If Redis or multiprocessing causes issues, disable by setting:

```python
# In agent_management.py
USE_MULTIPROCESSING = False
```

System will fallback to original single-process AgentPool behavior.

## Migration from Single-Process

Existing agents in database will be automatically restored into worker processes on startup.

No manual migration required - the system handles restoration transparently.

## Security Considerations

1. **Redis Authentication:** Set REDIS_PASSWORD in production
2. **PgBouncer:** Use auth_type = md5 and strong passwords
3. **Network:** Bind Redis/PgBouncer to localhost in production, use firewall rules
4. **Secrets:** Never commit `.env` with real credentials

## Additional Resources

- [Redis Documentation](https://redis.io/documentation)
- [PgBouncer Documentation](https://www.pgbouncer.org/)
- [Python Multiprocessing](https://docs.python.org/3/library/multiprocessing.html)
