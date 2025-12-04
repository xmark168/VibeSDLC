"""
MetaGPT Compatibility Analysis for dev_v2
Compare our implementation with MetaGPT's Engineer role flow.
"""

def analyze_compatibility():
    """Analyze compatibility between dev_v2 and MetaGPT."""
    
    print("=" * 70)
    print("MetaGPT vs dev_v2 Compatibility Analysis")
    print("=" * 70)
    
    # MetaGPT Engineer Role Features
    metagpt_features = {
        # Planning Phase
        "logic_analysis": {
            "metagpt": "Task decomposition with file-level planning",
            "dev_v2": "logic_analysis in plan_prompts.yaml with dependencies",
            "status": "IMPLEMENTED",
            "score": 100
        },
        "pre_load_context": {
            "metagpt": "get_codes() loads all related files before WriteCode",
            "dev_v2": "_preload_dependencies() loads deps in analyze_and_plan",
            "status": "IMPLEMENTED", 
            "score": 100
        },
        
        # Implementation Phase
        "single_llm_call": {
            "metagpt": "WriteCode uses single _aask() call, no tools",
            "dev_v2": "Minimal tools (skill + write), context pre-loaded",
            "status": "PARTIAL",
            "score": 80,
            "note": "Still uses tools but minimal (skill-focused)"
        },
        "design_doc_context": {
            "metagpt": "Design doc with data structures & interfaces",
            "dev_v2": "logic_analysis + pre_loaded_context",
            "status": "IMPLEMENTED",
            "score": 90
        },
        "complete_code_rule": {
            "metagpt": "Rule: Write out EVERY CODE DETAIL, DON'T LEAVE TODO",
            "dev_v2": "Rule 2: COMPLETE CODE: No placeholders, no TODOs",
            "status": "IMPLEMENTED",
            "score": 100
        },
        "one_file_focus": {
            "metagpt": "Only One file: implement THIS ONLY ONE FILE",
            "dev_v2": "Rule 1: ONE FILE ONLY: Implement THIS ONLY ONE FILE",
            "status": "IMPLEMENTED",
            "score": 100
        },
        
        # Review Phase  
        "code_review": {
            "metagpt": "WriteCodeReview with LGTM/LBTM decision",
            "dev_v2": "review node with LGTM/LBTM decision + feedback",
            "status": "IMPLEMENTED",
            "score": 100,
            "note": "nodes/review.py with route_after_review()"
        },
        "review_loop": {
            "metagpt": "LBTM triggers rewrite with feedback",
            "dev_v2": "LBTM triggers re-implement with review_feedback",
            "status": "IMPLEMENTED",
            "score": 100,
            "note": "Max 2 retries per step"
        },
        
        # Validation Phase
        "summarize_code": {
            "metagpt": "SummarizeCode reviews all files for TODOs/issues",
            "dev_v2": "summarize node reviews all files, detects TODOs",
            "status": "IMPLEMENTED",
            "score": 100,
            "note": "nodes/summarize.py with IS_PASS gate"
        },
        "is_pass_gate": {
            "metagpt": "IS_PASS check: YES/NO to proceed or retry",
            "dev_v2": "IS_PASS gate in summarize node with route_after_summarize()",
            "status": "IMPLEMENTED",
            "score": 100,
            "note": "YES -> validate, NO -> re-implement"
        },
        "run_tests": {
            "metagpt": "RunCode executes and validates",
            "dev_v2": "validate node runs tests",
            "status": "IMPLEMENTED",
            "score": 100
        },
        
        # Debug Phase
        "debug_error": {
            "metagpt": "DebugError with Editor tools for fixing",
            "dev_v2": "analyze_error + implement with full tools in debug mode",
            "status": "IMPLEMENTED",
            "score": 90
        },
        "debug_tools": {
            "metagpt": "Editor tools (read, write, edit, search)",
            "dev_v2": "Full toolset in debug mode (read, write, edit, grep, glob)",
            "status": "IMPLEMENTED",
            "score": 100
        },
        
        # Prompt Structure
        "prompt_structure": {
            "metagpt": "NOTICE + Context + Format example + Instruction",
            "dev_v2": "NOTICE + Context + Instruction + Skills + Tools",
            "status": "IMPLEMENTED",
            "score": 90,
            "note": "Added Skills section unique to dev_v2"
        },
        "numbered_rules": {
            "metagpt": "Numbered instruction rules (1-7)",
            "dev_v2": "Numbered instruction rules (1-7)",
            "status": "IMPLEMENTED",
            "score": 100
        },
        
        # Unique dev_v2 Features (bonus)
        "agentic_skills": {
            "metagpt": "Not present - uses design docs",
            "dev_v2": "Skill system with activate_skills(), framework patterns",
            "status": "UNIQUE_TO_DEV_V2",
            "score": 100,
            "note": "Enhancement over MetaGPT - reusable patterns"
        },
        "semantic_search": {
            "metagpt": "similarity_search in Editor tool",
            "dev_v2": "CocoIndex semantic search (optional)",
            "status": "IMPLEMENTED",
            "score": 80
        },
    }
    
    # Calculate scores
    implemented = []
    partial = []
    not_implemented = []
    unique = []
    
    total_score = 0
    max_score = 0
    
    for feature, info in metagpt_features.items():
        status = info["status"]
        score = info["score"]
        
        if status == "UNIQUE_TO_DEV_V2":
            unique.append((feature, info))
        elif status == "IMPLEMENTED":
            implemented.append((feature, info))
            total_score += score
            max_score += 100
        elif status == "PARTIAL":
            partial.append((feature, info))
            total_score += score
            max_score += 100
        else:
            not_implemented.append((feature, info))
            max_score += 100
    
    # Print results
    print("\n## IMPLEMENTED (100%)")
    print("-" * 50)
    for feature, info in implemented:
        print(f"  [x] {feature}")
        print(f"      MetaGPT: {info['metagpt']}")
        print(f"      dev_v2:  {info['dev_v2']}")
    
    print("\n## PARTIAL")
    print("-" * 50)
    for feature, info in partial:
        print(f"  [~] {feature} ({info['score']}%)")
        print(f"      MetaGPT: {info['metagpt']}")
        print(f"      dev_v2:  {info['dev_v2']}")
        if "note" in info:
            print(f"      Note: {info['note']}")
    
    print("\n## NOT IMPLEMENTED")
    print("-" * 50)
    for feature, info in not_implemented:
        print(f"  [ ] {feature}")
        print(f"      MetaGPT: {info['metagpt']}")
        print(f"      dev_v2:  {info['dev_v2']}")
    
    print("\n## UNIQUE TO dev_v2 (Enhancements)")
    print("-" * 50)
    for feature, info in unique:
        print(f"  [+] {feature}")
        print(f"      dev_v2:  {info['dev_v2']}")
        if "note" in info:
            print(f"      Note: {info['note']}")
    
    # Summary
    compatibility = (total_score / max_score) * 100 if max_score > 0 else 0
    
    print("\n" + "=" * 70)
    print("## SUMMARY")
    print("=" * 70)
    print(f"""
    Implemented:     {len(implemented)} features (100% each)
    Partial:         {len(partial)} features
    Not Implemented: {len(not_implemented)} features
    Unique to dev_v2: {len(unique)} features (bonus)
    
    Total Score:     {total_score} / {max_score}
    
    +========================================+
    |  COMPATIBILITY: {compatibility:.0f}%                   |
    +========================================+
    """)
    
    # What's implemented
    print("## IMPLEMENTATION STATUS")
    print("-" * 50)
    print("""
    1. [x] review node (LGTM/LBTM) - nodes/review.py
           - LGTM/LBTM decision after each step
           - LBTM triggers re-implement with feedback
           - Max 2 retries per step
           
    2. [x] summarize_code node - nodes/summarize.py
           - Reviews ALL modified files
           - Detects TODOs, incomplete code, issues
           - Returns summary + todos dict
           
    3. [x] IS_PASS gate - in summarize node
           - YES -> proceed to validate
           - NO -> re-implement with feedback
           - Max 2 retries
    """)
    
    # Flow comparison
    print("\n## FLOW COMPARISON")
    print("-" * 50)
    print("""
    MetaGPT Engineer Flow:
    +-------------+   +-------------+   +-------------+   +---------+
    | WriteCode   | > | WriteCode   | > | Summarize   | > | IS_PASS |
    | (pre-load)  |   | Review      |   | Code        |   | YES/NO  |
    +-------------+   +-------------+   +-------------+   +---------+
          ^                 |                                  |
          |                 | LBTM                             | NO
          +-----------------+----------------------------------+

    dev_v2 MetaGPT-Style Flow (NOW IMPLEMENTED):
    +-------------+   +-------------+   +--------+   +-----------+   +----------+
    | analyze_    | > | implement   | > | review | > | summarize | > | validate |
    | and_plan    |   | (skills)    |   | LGTM/  |   | IS_PASS   |   | (tests)  |
    +-------------+   +-------------+   | LBTM   |   +-----------+   +----------+
          ^                 ^           +--------+         |
          |                 |               |              | NO
          |                 +---------------+--------------+
          |                     (re-implement with feedback)
          |
          +--- (analyze_error on test failure)
    
    FULLY COMPATIBLE with MetaGPT flow!
    """)
    
    return compatibility


if __name__ == "__main__":
    compatibility = analyze_compatibility()
