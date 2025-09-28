# VibeSDLC - Microservices

A modern microservices application built with FastAPI, React, and event-driven architecture using Kafka.

## 🏗️ Architecture

All services are **peer-to-peer** with no dependencies between them. Each service connects directly to external infrastructure.

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                 │    │                  │    │                 │
│    Frontend     │    │ Management       │    │   AI Agent      │
│   (React)       │    │ Service          │    │   Service       │
│                 │    │ (FastAPI)        │    │ (FastAPI)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         │                       │                       │
         │              ┌────────▼────────┐             │
         │              │                 │             │
         └─────────────►│ External        │◄────────────┘
                        │ PostgreSQL      │
                        │                 │
                        └─────────────────┘

                        ┌─────────────────┐
                        │                 │
                        │ External Kafka  │
                        │  (Self-hosted)  │
                        │                 │
                        └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose**
- **Node.js 24+** (for frontend development)
- **External Infrastructure** (production) or use local development mode

## 🎯 Two Deployment Modes

### Mode 1: Production (External Infrastructure)

For production with external PostgreSQL & Kafka:

```bash
# 1. Setup external infrastructure first
# 2. Configure environment
cp .env.example .env
# Edit .env with your external services

# 3. Start services
docker compose up -d
```

### Mode 2: Local Development

For local development with PostgreSQL included:

```bash
# 1. Setup environment
cp .env.example .env
# Keep default localhost settings

# 2. Start with local PostgreSQL
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

# 3. Check services
docker compose ps
```

### Configuration

**Production (.env):**
```bash
# External Infrastructure
POSTGRES_SERVER=your-postgres-server
KAFKA_BOOTSTRAP_SERVERS=your-kafka-server:9092

# Credentials
POSTGRES_PASSWORD=your-secure-password
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
```

**Local Development:**
```bash
# Local Infrastructure (defaults work)
POSTGRES_SERVER=localhost
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Still need AI keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 4. Access Applications

- **Frontend**: http://localhost:5173
- **Management API**: http://localhost:8000
- **AI Agent API**: http://localhost:8001
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
VibeSDLC/
├── services/
│   ├── management-service/    # Core business logic API
│   └── ai-agent-service/      # AI processing service
├── frontend/                  # React application
├── docker-compose.yml         # Service orchestration
├── .env.example              # Environment template
└── README.md                 # This file
```

## 🛠️ Services

### Management Service (Port 8000)
- **FastAPI** backend with PostgreSQL
- User management, authentication
- Business logic and data processing
- REST API with OpenAPI docs

### AI Agent Service (Port 8001)
- **FastAPI** service for AI operations
- OpenAI & Anthropic Claude integration
- Event-driven processing via Kafka
- LangFuse observability (optional)

### Frontend (Port 5173)
- **React 19** with TypeScript
- **Vite** for fast development
- **Chakra UI** component library
- **TanStack** Router & Query

## 🔧 Development

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

See [frontend/README.md](frontend/README.md) for detailed frontend setup.

### Backend Development

```bash
# Management Service
cd services/management-service
# Follow service-specific README

# AI Agent Service
cd services/ai-agent-service
# Follow service-specific README
```

### Database Migrations

```bash
# Run migrations in management service
docker-compose exec management-service alembic upgrade head
```

## 🐘 Kafka Configuration

Since Kafka is self-hosted externally, ensure your Kafka server:

1. **Is accessible** from Docker containers
2. **Has required topics** created (or auto-create enabled)
3. **Proper networking** configuration

### Required Kafka Topics

```bash
# Create topics on your Kafka server
kafka-topics --create --topic user-events --bootstrap-server your-kafka:9092
kafka-topics --create --topic ai-requests --bootstrap-server your-kafka:9092
kafka-topics --create --topic ai-responses --bootstrap-server your-kafka:9092
```

### Docker Network Access

If Kafka is on the same host:
```bash
# Use host networking for services
docker-compose up --net=host
```

Or configure Kafka to be accessible from Docker:
```bash
# In your Kafka server.properties
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://your-host-ip:9092
```

## 🧪 Testing

```bash
# Frontend tests
cd frontend
npm run test:e2e

# Backend tests
docker-compose exec management-service pytest
docker-compose exec ai-agent-service pytest
```

## 📊 Monitoring

### Health Checks

```bash
# Check service health
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Logs

```bash
# View logs
docker-compose logs -f management-service
docker-compose logs -f ai-agent-service
docker-compose logs -f frontend
```

## 🔒 Security

### Environment Variables

- Never commit `.env` files
- Use strong passwords and secret keys
- Rotate API keys regularly

### Production Considerations

- Use HTTPS in production
- Configure proper CORS settings
- Set up proper authentication
- Use secrets management (Docker Secrets, etc.)

## 🐳 Docker Commands

### NPM Scripts (Recommended)

```bash
# Local Development
npm run dev              # Start with local PostgreSQL
npm run dev:build        # Build and start
npm run dev:down         # Stop local development

# Production
npm run prod             # Start production mode
npm run prod:build       # Build and start production
npm run prod:down        # Stop production

# Monitoring
npm run logs             # View all logs
npm run logs:management  # Management service logs
npm run logs:ai          # AI agent service logs
npm run logs:frontend    # Frontend logs
npm run status           # Check service status

# Cleanup
npm run clean            # Stop and remove everything
```

### Direct Docker Commands

```bash
# Local development
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d

# Production
docker compose up -d

# Logs and debugging
docker compose logs -f [service-name]
docker compose exec management-service bash
```

## 🚨 Troubleshooting

### Common Issues

1. **Kafka Connection Failed**
   ```bash
   # Check Kafka accessibility
   telnet your-kafka-server 9092

   # Verify environment variable
   echo $KAFKA_BOOTSTRAP_SERVERS
   ```

2. **Database Connection Issues**
   ```bash
   # Check PostgreSQL
   docker-compose logs postgres

   # Test connection
   docker-compose exec postgres psql -U postgres -d app
   ```

3. **Frontend Build Issues**
   ```bash
   # Clear node_modules and rebuild
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Port Conflicts

If ports are already in use:
```bash
# Check what's using ports
lsof -i :5173  # Frontend
lsof -i :8000  # Management API
lsof -i :8001  # AI Agent API
lsof -i :5432  # PostgreSQL
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/new-feature`
3. **Make changes** and test
4. **Commit**: `git commit -m 'Add new feature'`
5. **Push**: `git push origin feature/new-feature`
6. **Create Pull Request**

## 📝 License

This project is licensed under the MIT License.

---

**Need help?** Check individual service READMEs or create an issue.