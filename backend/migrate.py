"""
Simple migration script to apply pending Alembic migrations.
Run with: python migrate.py
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command

def run_migrations():
    """Run all pending migrations"""
    print("Running database migrations...")
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Run upgrade to head
    command.upgrade(alembic_cfg, "head")
    
    print("[OK] Migrations completed successfully!")

if __name__ == "__main__":
    run_migrations()
