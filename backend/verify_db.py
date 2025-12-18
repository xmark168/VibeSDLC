"""Verify database schema after migration."""
from sqlalchemy import create_engine, text
from app.core.config import settings

def verify_enum():
    """Check StoryAgentState enum values."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    with engine.connect() as conn:
        result = conn.execute(text("SELECT unnest(enum_range(NULL::storyagentstate))"))
        print("StoryAgentState enum values in database:")
        for row in result:
            print(f"  - {row[0]}")

def verify_agent_pools():
    """Check agent_pools table schema."""
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'agent_pools' AND column_name IN ('priority', 'pool_name')
            ORDER BY column_name
        """))
        print("\nagent_pools table columns:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} (nullable: {row[2]})")

if __name__ == "__main__":
    try:
        verify_enum()
        verify_agent_pools()
        print("\nDatabase schema verification successful!")
    except Exception as e:
        print(f"\nError: {e}")
        exit(1)
