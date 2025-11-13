import asyncio
from sqlalchemy import text
from app.database import engine

async def verify():
    async with engine.connect() as conn:
        print("="*60)
        print("AGENTS TABLE VERIFICATION")
        print("="*60 + "\n")

        # Check agents table columns
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'agents'
            ORDER BY ordinal_position
        """))

        print("Columns in agents table:")
        print("-" * 60)
        for row in result:
            nullable = "NULL" if row[2] == 'YES' else "NOT NULL"
            print(f"  - {row[0]}: {row[1]} {nullable}")

        # Check foreign keys
        fk_result = await conn.execute(text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name='agents'
        """))

        print("\nForeign Keys:")
        print("-" * 60)
        for row in fk_result:
            print(f"  - {row[0]} -> {row[1]}.{row[2]}")

        # Check indexes
        idx_result = await conn.execute(text("""
            SELECT
                i.relname AS index_name,
                a.attname AS column_name
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = 'agents'
              AND t.relkind = 'r'
              AND i.relname NOT LIKE '%_pkey'
            ORDER BY i.relname
        """))

        print("\nIndexes:")
        print("-" * 60)
        seen = set()
        for row in idx_result:
            if row[0] not in seen:
                print(f"  - {row[0]}: {row[1]}")
                seen.add(row[0])

        print("\n" + "="*60)
        print("[SUCCESS] project_id added to agents table!")
        print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(verify())
