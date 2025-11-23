from app.core.db import engine
from sqlmodel import Session, select
from app.models import Agent, AgentStatus

session = Session(engine)
agents = session.exec(select(Agent)).all()

print(f"Total agents in DB: {len(agents)}\n")

# Group by status
by_status = {}
for a in agents:
    by_status.setdefault(a.status.value, []).append(a)

print("By status:")
for status, ags in by_status.items():
    names = [a.human_name for a in ags]
    print(f"  {status}: {len(ags)} agents")
    for name in names:
        print(f"    - {name}")

print("\n" + "="*50)

# Group by role
by_role = {}
for a in agents:
    by_role.setdefault(a.role_type, []).append(a)

print("\nBy role:")
for role, ags in by_role.items():
    print(f"  {role}: {len(ags)} agents (status: {[a.status.value for a in ags]})")

print("\n" + "="*50)

# Check stopped agents
stopped = [a for a in agents if a.status == AgentStatus.stopped]
print(f"\nStopped agents: {len(stopped)}")
for a in stopped:
    print(f"  - {a.human_name} ({a.role_type}, project: {str(a.project_id)[:8]})")
