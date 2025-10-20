#!/usr/bin/env python3
"""
Debug script để check prompts content
"""

def debug_backend_prompt():
    """Debug BACKEND_FILE_MODIFICATION_PROMPT"""
    
    prompts_file = "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
    
    with open(prompts_file, 'r') as f:
        content = f.read()
    
    # Extract BACKEND_FILE_MODIFICATION_PROMPT
    start_marker = "BACKEND_FILE_MODIFICATION_PROMPT = \"\"\""
    end_marker = "\"\"\"\n\n# Frontend File Modification Prompt"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        backend_prompt = content[start_idx:end_idx]
        print("BACKEND_FILE_MODIFICATION_PROMPT:")
        print("=" * 60)
        print(backend_prompt)
        print("=" * 60)
        
        # Check for logical flow
        search_text = "MAINTAIN the logical flow: imports → configuration → middleware → routes → exports"
        if search_text in backend_prompt:
            print("✅ Found logical flow text")
        else:
            print("❌ Logical flow text not found")
            print("Searching for similar patterns...")
            if "logical flow" in backend_prompt:
                print("Found 'logical flow' somewhere")
                # Find the line
                lines = backend_prompt.split('\n')
                for i, line in enumerate(lines):
                    if "logical flow" in line.lower():
                        print(f"Line {i}: {line}")
            else:
                print("No 'logical flow' found at all")

def debug_frontend_prompt():
    """Debug FRONTEND_FILE_MODIFICATION_PROMPT"""
    
    prompts_file = "ai-agent-service/app/agents/developer/implementor/utils/prompts.py"
    
    with open(prompts_file, 'r') as f:
        content = f.read()
    
    # Extract FRONTEND_FILE_MODIFICATION_PROMPT
    start_marker = "FRONTEND_FILE_MODIFICATION_PROMPT = \"\"\""
    end_marker = "\"\"\"\n\n# Generic File Modification Prompt"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx)
    
    if start_idx != -1 and end_idx != -1:
        frontend_prompt = content[start_idx:end_idx]
        print("\nFRONTEND_FILE_MODIFICATION_PROMPT:")
        print("=" * 60)
        print(frontend_prompt)
        print("=" * 60)
        
        # Check for logical flow
        search_text = "MAINTAIN the logical flow: imports → types → components → exports"
        if search_text in frontend_prompt:
            print("✅ Found logical flow text")
        else:
            print("❌ Logical flow text not found")
            print("Searching for similar patterns...")
            if "logical flow" in frontend_prompt:
                print("Found 'logical flow' somewhere")
                # Find the line
                lines = frontend_prompt.split('\n')
                for i, line in enumerate(lines):
                    if "logical flow" in line.lower():
                        print(f"Line {i}: {line}")
            else:
                print("No 'logical flow' found at all")

if __name__ == "__main__":
    debug_backend_prompt()
    debug_frontend_prompt()
