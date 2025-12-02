import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d = json.load(open(r'C:\Users\son16\OneDrive\Desktop\thunder-file_d6dd5498.json', encoding='utf-8'))
plan = next((o for o in d['observations'] if o.get('name') == 'analyze_and_plan'), None)

if plan:
    print("=== PLAN NODE ANALYSIS ===\n")
    
    # Skip input analysis, focus on output
    print("--- SKIPPING INPUT (encoding issues) ---")
    
    # Output
    print("\n--- OUTPUT ---")
    out = plan.get('output', {})
    content = out.get('content', '') if isinstance(out, dict) else str(out)
    print(content)
    
    # Parse steps
    print("\n--- STEPS ANALYSIS ---")
    try:
        import re
        match = re.search(r'<result>(.*?)</result>', content, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            steps = data.get('steps', [])
            print(f"Total steps: {len(steps)}")
            print("\nSteps breakdown:")
            for s in steps:
                action = s.get('action', 'unknown')
                desc = s.get('description', '')[:60]
                file_path = s.get('file_path', '')
                print(f"  {s.get('order')}. [{action}] {desc}")
                print(f"     -> {file_path}")
            
            # Count by action type
            print("\n--- ACTION TYPE COUNT ---")
            actions = {}
            for s in steps:
                a = s.get('action', 'unknown')
                actions[a] = actions.get(a, 0) + 1
            for a, c in sorted(actions.items(), key=lambda x: -x[1]):
                print(f"  {a}: {c}")
                
            # Count test steps
            test_steps = [s for s in steps if s.get('action') == 'test' or 'test' in s.get('description', '').lower()]
            print(f"\n--- TEST STEPS: {len(test_steps)} ---")
            for s in test_steps:
                print(f"  {s.get('order')}. {s.get('description', '')[:50]}")
    except Exception as e:
        print(f"Parse error: {e}")
    
    # Usage stats
    print("\n--- USAGE ---")
    usage = plan.get('usage', {})
    print(f"Input tokens: {usage.get('input', 0)}")
    print(f"Output tokens: {usage.get('output', 0)}")
    print(f"Cost: ${plan.get('calculatedTotalCost', 0):.4f}")
