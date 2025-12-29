# VibeSDLC 🚀

> **AI-Powered Software Development Lifecycle Platform** — Hệ thống multi-agent tự động hóa quy trình phát triển phần mềm.

## 💡 Ý tưởng cốt lõi

VibeSDLC mô phỏng một **đội ngũ phát triển phần mềm ảo** với các AI Agent chuyên biệt:

| Agent | Vai trò |
|-------|---------|
| 🎯 **Team Leader** | Điều phối, phân công task, quản lý workflow |
| 📋 **Business Analyst** | Phân tích yêu cầu, tạo PRD, backlog |
| 💻 **Developer** | Code implementation |
| 🧪 **Tester** | Kiểm thử, đảm bảo chất lượng |

## 🏗️ Kiến trúc

```
┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend       │
│   (React/Vite)  │     │   (FastAPI)     │
└─────────────────┘     └────────┬────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
   ┌────▼────┐            ┌──────▼─────┐           ┌──────▼──────┐
   │  Kafka  │            │ PostgreSQL │           │    Redis    │
   │ Message │            │  Database  │           │    Cache    │
   │  Queue  │            └────────────┘           └─────────────┘
   └────┬────┘
        │
   ┌────▼────────────────────────────────────────┐
   │              AI Agent Pool                  │
   │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
   │  │ Team    │ │Business │ │Developer│ ...    │
   │  │ Leader  │ │ Analyst │ │         │        │
   │  └─────────┘ └─────────┘ └─────────┘        │
   └─────────────────────────────────────────────┘
```

## ⚡ Tech Stack

**Backend:**
- FastAPI + SQLModel + PostgreSQL
- Kafka (message queue giữa các agents)
- Redis (caching)
- LangGraph/LangChain (AI Agent orchestration)

**Frontend:**
- React 19 + TypeScript + Vite
- TanStack Router + React Query
- TailwindCSS + Radix UI + Framer Motion

**Infrastructure:**
- Docker Compose
- MinIO (object storage)
- Sentry (error tracking)

## 🚀 Quick Start

```bash
# 1. Khởi chạy infrastructure
docker-compose up -d

# 2. Backend
cd backend
uv install
python main.py

# 3. Frontend
cd frontend
pnpm install
pnpm dev
```

## 📁 Cấu trúc thư mục

```
VibeSDLC/
├── backend/
│   └── app/
│       ├── agents/          # AI Agents (core logic)
│       │   ├── business_analyst/
│       │   ├── developer/
│       │   ├── team_leader/
│       │   └── tester/
│       ├── api/routes/      # REST endpoints
│       ├── kafka/           # Message queue handlers
│       ├── models/          # Database models
│       ├── services/        # Business logic
│       └── websocket/       # Real-time communication
└── frontend/
    └── src/
        ├── components/      # UI components
        ├── routes/          # Pages
        └── stores/          # State management (Zustand)
```

## 🔑 Tính năng chính

1. **Kanban Board** — Quản lý stories theo workflow Scrum
2. **Real-time Chat** — Giao tiếp với AI agents qua WebSocket
3. **Autonomous Execution** — Agent tự động xử lý task từ backlog
4. **Git Integration** — Tự động tạo branch, commit code
5. **Artifact Management** — Lưu trữ PRD, specs, code files

