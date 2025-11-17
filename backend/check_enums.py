from app.core.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname IN ('storytype', 'storystatus')"))
    enum_types = [row[0] for row in result]
    print(f"Found enum types: {enum_types}")

    # Also check backlog_items columns
    result2 = conn.execute(text("""
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns
        WHERE table_name = 'backlog_items'
        AND column_name IN ('type', 'status')
    """))
    print("\nColumn types:")
    for row in result2:
        print(f"  {row[0]}: {row[1]} (udt: {row[2]})")
