"""Test if orchestrator query will find agents."""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, select
from app.core.db import engine
from app.models import Agent as AgentModel, AgentStatus

def test_orchestrator_query():
    """Test the orchestrator query with enum values."""
    print("\n" + "="*80)
    print("TESTING ORCHESTRATOR QUERY (AFTER FIX)")
    print("="*80 + "\n")

    with Session(engine) as session:
        print("OLD QUERY (using strings):")
        print("  .where(AgentModel.status.in_(['idle', 'stopped']))")
        old_result = session.exec(
            select(AgentModel).where(AgentModel.status.in_(["idle", "stopped"]))
        ).all()
        print(f"  Result: {len(old_result)} agents found\n")

        print("NEW QUERY (using enums):")
        print("  .where(AgentModel.status.in_([AgentStatus.idle, AgentStatus.stopped]))")
        new_result = session.exec(
            select(AgentModel).where(AgentModel.status.in_([AgentStatus.idle, AgentStatus.stopped]))
        ).all()
        print(f"  Result: {len(new_result)} agents found\n")

        if new_result:
            print("Agents that will be loaded by orchestrator:")
            for agent in new_result:
                print(f"  ✓ {agent.human_name} ({agent.role_type}) - Project: {agent.project_id}")
        else:
            print("  ⚠ No agents found!")

        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    test_orchestrator_query()
