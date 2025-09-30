# PO Agent Service

Product Owner Agent với các sub-agents cho VibeSDLC project.

## Tính năng

### Gatherer Agent ✅
- **Phỏng vấn người dùng**: Thu thập requirements thông qua conversation
- **Web Research**: Tự động search và extract thông tin liên quan (Tavily)
- **Requirements Analysis**: Phân tích và tổng hợp requirements
- **Priority Classification**: Phân loại requirements theo độ ưu tiên
- **Insight Generation**: Tạo insights từ data đã thu thập

### Các Sub-agents khác (Coming Soon)
- **Vision Agent**: Tạo product vision và roadmap
- **Backlog Agent**: Quản lý và organize product backlog
- **Priority Agent**: Ưu tiên features theo business value

## Cài đặt

1. **Clone và setup**:
```bash
cd services/po-agent
cp .env.example .env
# Cập nhật API keys trong .env
```

2. **Install dependencies**:
```bash
uv sync
```

3. **Chạy service**:
```bash
uv run python main.py
```

## API Endpoints

### Gatherer Agent

#### POST `/gatherer/interview`
Phỏng vấn user để thu thập requirements.

**Request**:
```json
{
    "user_input": "Tôi muốn tạo một website e-commerce bán quần áo",
    "session_id": "optional-session-id"
}
```

**Response**:
```json
{
    "status": "complete",
    "requirements": [
        {
            "id": "req_1_1234567890",
            "title": "E-commerce Platform",
            "description": "Website bán quần áo online",
            "priority": "high",
            "category": "functional",
            "confidence": 0.8,
            "source": "interview"
        }
    ],
    "next_questions": [
        "Bạn có muốn tích hợp payment gateway nào cụ thể?",
        "Website cần hỗ trợ mobile không?"
    ],
    "insights": [
        "User cần e-commerce platform với focus vào fashion",
        "Cần quan tâm đến UX cho mobile users"
    ],
    "conversation_history": [...],
    "error": null
}
```

#### GET `/gatherer/requirements/summary`
Lấy tóm tắt requirements đã thu thập.

**Parameters**:
- `format`: "markdown" hoặc "json"

### Health Check

#### GET `/health`
Kiểm tra trạng thái service.

## Environment Variables

Xem file `.env.example` để biết các biến môi trường cần thiết:

- `OPENAI_API_KEY`: API key cho OpenAI (required)
- `TAVILY_API_KEY`: API key cho Tavily search (required)
- `HOST`: Host để bind service (default: 0.0.0.0)
- `PORT`: Port để chạy service (default: 8002)

## Architecture

```
PO Agent Service
├── Gatherer Agent (LangGraph workflow)
│   ├── Interview User
│   ├── Research Topics (Tavily)
│   └── Analyze Requirements
├── Vision Agent (Coming Soon)
├── Backlog Agent (Coming Soon)
└── Priority Agent (Coming Soon)
```

## Development

### Chạy tests:
```bash
uv run python -m pytest tests/
```

### Development mode:
```bash
ENV=development uv run python main.py
```

## Integration với VibeSDLC

Service này sẽ được gọi từ:
- Frontend UI để thu thập user requirements
- API Gateway để route requests
- Các agents khác trong hệ thống

## Roadmap

- [x] Gatherer Agent với LangGraph workflow
- [x] FastAPI endpoints
- [x] Tavily integration cho research
- [ ] Session management
- [ ] Vision Agent
- [ ] Backlog Agent
- [ ] Priority Agent
- [ ] Integration tests
- [ ] Docker deployment