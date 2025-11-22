"""Diagnostic script to check agent status in database."""
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, select
from app.core.db import engine
from app.models import Agent as AgentModel, Project

def check_agents():
    """Check all agents in database."""
    print("\n" + "="*80)
    print("AGENT STATUS DIAGNOSTIC")
    print("="*80 + "\n")

    with Session(engine) as session:
        # Get all projects
        projects = session.exec(select(Project)).all()
        print(f"Found {len(projects)} projects in database:\n")

        for project in projects:
            print(f"Project: {project.name} ({project.code}) - ID: {project.id}")

            # Get agents for this project
            agents = session.exec(
                select(AgentModel).where(AgentModel.project_id == project.id)
            ).all()

            if agents:
                print(f"  Agents ({len(agents)}):")
                for agent in agents:
                    print(f"    - {agent.human_name} ({agent.role_type})")
                    print(f"      Status: {agent.status} (type: {type(agent.status)})")
                    print(f"      ID: {agent.id}")
            else:
                print("  No agents found!")
            print()

        # Check agents that orchestrator would load
        print("\n" + "-"*80)
        print("AGENTS THAT ORCHESTRATOR WOULD LOAD (status='idle' or 'stopped'):")
        print("-"*80 + "\n")

        loadable_agents = session.exec(
            select(AgentModel).where(AgentModel.status.in_(["idle", "stopped"]))
        ).all()

        if loadable_agents:
            print(f"Found {len(loadable_agents)} loadable agents:")
            for agent in loadable_agents:
                print(f"  - {agent.human_name} ({agent.role_type}) in project {agent.project_id}")
                print(f"    Status: '{agent.status}' (type: {type(agent.status).__name__})")
        else:
            print("No agents with status 'idle' or 'stopped' found!")
            print("\nAll agents in database:")
            all_agents = session.exec(select(AgentModel)).all()
            for agent in all_agents:
                print(f"  - {agent.human_name}: status='{agent.status}' (type: {type(agent.status).__name__})")

        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    check_agents()
