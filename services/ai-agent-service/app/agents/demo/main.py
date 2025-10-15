"""
Basic FastAPI Application for Demo
This is a simple FastAPI app that the implementor agent will enhance with JWT authentication.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="Demo FastAPI Application",
    description="A simple FastAPI app for testing the implementor agent",
    version="1.0.0"
)

# Basic data models
class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

# In-memory storage (for demo purposes)
users_db: List[User] = [
    User(id=1, username="admin", email="admin@example.com", full_name="Administrator"),
    User(id=2, username="user1", email="user1@example.com", full_name="User One"),
]

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Welcome to Demo FastAPI Application"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Application is running"}

@app.get("/users", response_model=List[User])
async def get_users():
    """Get all users"""
    return users_db

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user by ID"""
    for user in users_db:
        if user.id == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users", response_model=User)
async def create_user(user: UserCreate):
    """Create a new user"""
    new_id = max([u.id for u in users_db], default=0) + 1
    new_user = User(id=new_id, **user.dict())
    users_db.append(new_user)
    return new_user

@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_update: UserCreate):
    """Update an existing user"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            updated_user = User(id=user_id, **user_update.dict())
            users_db[i] = updated_user
            return updated_user
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete a user"""
    for i, user in enumerate(users_db):
        if user.id == user_id:
            deleted_user = users_db.pop(i)
            return {"message": f"User {deleted_user.username} deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
