"""Quick script to check messages in database"""
import asyncio
from sqlmodel import Session, select, func
from app.core.db import engine
from app.models import Message, AuthorType, MessageVisibility

def check_recent_messages():
    with Session(engine) as session:
        # Get all messages from last hour
        stmt = (
            select(Message)
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        
        messages = session.exec(stmt).all()
        
        print("\n=== RECENT MESSAGES (Last 20) ===\n")
        for msg in messages:
            print(f"ID: {msg.id}")
            print(f"  Author: {msg.author_type}")
            print(f"  Visibility: {msg.visibility}")
            print(f"  Agent: {msg.agent_name if hasattr(msg, 'agent_name') else 'N/A'}")
            print(f"  Type: {msg.message_type}")
            print(f"  Content: {msg.content[:100]}...")
            print(f"  Created: {msg.created_at}")
            print()
        
        # Count by visibility
        user_msg_count = session.exec(
            select(func.count())
            .select_from(Message)
            .where(Message.visibility == MessageVisibility.USER_MESSAGE)
        ).one()
        
        system_log_count = session.exec(
            select(func.count())
            .select_from(Message)
            .where(Message.visibility == MessageVisibility.SYSTEM_LOG)
        ).one()
        
        print(f"USER_MESSAGE count: {user_msg_count}")
        print(f"SYSTEM_LOG count: {system_log_count}")
        
        # Check for agent responses specifically
        agent_responses = session.exec(
            select(Message)
            .where(Message.author_type == AuthorType.AGENT)
            .where(Message.message_type != "activity")
            .order_by(Message.created_at.desc())
            .limit(10)
        ).all()
        
        print(f"\n=== RECENT AGENT RESPONSES (Last 10) ===\n")
        for msg in agent_responses:
            print(f"ID: {msg.id}")
            print(f"  Visibility: {msg.visibility}")
            print(f"  Type: {msg.message_type}")
            print(f"  Content: {msg.content[:200]}...")
            print()

if __name__ == "__main__":
    check_recent_messages()
