"""
PO Agent Service - Product Owner Agent với các sub-agents
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import os

from app.agents.gatherer_agent import create_gatherer_agent, GathererTools

# FastAPI app
app = FastAPI(
    title="PO Agent Service",
    description="Product Owner Agent với Gatherer, Vision, Backlog, Priority sub-agents",
    version="0.1.0"
)

# Initialize agents
gatherer_agent = create_gatherer_agent()
gatherer_tools = GathererTools(gatherer_agent)

# Request/Response models
class InterviewRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = None

class InterviewResponse(BaseModel):
    status: str
    requirements: List[Dict[str, Any]]
    next_questions: List[str]
    insights: List[str]
    conversation_history: List[Dict[str, Any]]
    error: Optional[str] = None

# Routes
@app.get("/")
async def root():
    return {"message": "PO Agent Service is running", "version": "0.1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "po-agent"}

@app.post("/gatherer/interview", response_model=InterviewResponse)
async def interview_user(request: InterviewRequest):
    """
    Phỏng vấn user để thu thập requirements
    """
    try:
        result = await gatherer_tools.interview_user(request.user_input)
        return InterviewResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interview failed: {str(e)}")

@app.get("/gatherer/requirements/summary")
async def get_requirements_summary(format: str = "markdown"):
    """
    Lấy tóm tắt requirements đã thu thập
    """
    try:
        # This would need session management in production
        # For now, return empty summary
        return {
            "format": format,
            "summary": "No requirements collected yet. Start an interview first.",
            "total_requirements": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

def main():
    """Main function để chạy service"""
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting PO Agent Service on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True if os.getenv("ENV") == "development" else False
    )

if __name__ == "__main__":
    main()
