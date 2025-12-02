"""Quick demo of test_team_leader_interactive - runs test case #2"""
import asyncio
from test_team_leader_interactive import run_test_case, TEST_CASES

async def main():
    # Run test case #2 - IMPLEMENT Task
    test_case = TEST_CASES[1]  # Index 1 = test case #2
    await run_test_case(test_case)

if __name__ == "__main__":
    asyncio.run(main())
