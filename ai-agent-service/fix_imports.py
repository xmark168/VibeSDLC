#!/usr/bin/env python3
"""
Fix relative imports to absolute imports in planner subagent
"""

import os
import re

def fix_imports_in_file(filepath):
    """Fix relative imports in a single file."""
    print(f"Fixing imports in: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix relative imports patterns
    patterns = [
        # from ..state import -> from app.agents.developer.planner.state import
        (r'from \.\.state import', 'from app.agents.developer.planner.state import'),
        
        # from ..tools import -> from app.agents.developer.planner.tools import
        (r'from \.\.tools import', 'from app.agents.developer.planner.tools import'),
        
        # from ..utils import -> from app.agents.developer.planner.utils import
        (r'from \.\.utils import', 'from app.agents.developer.planner.utils import'),
        
        # from .tools import -> from app.agents.developer.planner.tools import
        (r'from \.tools import', 'from app.agents.developer.planner.tools import'),
        
        # from .utils import -> from app.agents.developer.planner.utils import
        (r'from \.utils import', 'from app.agents.developer.planner.utils import'),
        
        # from .nodes import -> from app.agents.developer.planner.nodes import
        (r'from \.nodes import', 'from app.agents.developer.planner.nodes import'),
        
        # from ....templates.prompts.developer.planner import -> from app.templates.prompts.developer.planner import
        (r'from \.\.\.\.templates\.prompts\.developer\.planner import', 'from app.templates.prompts.developer.planner import'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Write back if changed
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Fixed imports in {filepath}")
        return True
    else:
        print(f"  ⏭️  No changes needed in {filepath}")
        return False

def main():
    """Fix imports in all planner files."""
    print("🔧 Fixing relative imports in planner subagent...")
    
    planner_dir = "app/agents/developer/planner"
    
    # Files to fix
    files_to_fix = [
        # Main files
        f"{planner_dir}/__init__.py",
        f"{planner_dir}/agent.py",
        f"{planner_dir}/state.py",
        
        # Nodes
        f"{planner_dir}/nodes/__init__.py",
        f"{planner_dir}/nodes/initialize.py",
        f"{planner_dir}/nodes/parse_task.py",
        f"{planner_dir}/nodes/analyze_codebase.py",
        f"{planner_dir}/nodes/map_dependencies.py",
        f"{planner_dir}/nodes/generate_plan.py",
        f"{planner_dir}/nodes/validate_plan.py",
        f"{planner_dir}/nodes/finalize.py",
        
        # Tools
        f"{planner_dir}/tools/__init__.py",
        f"{planner_dir}/tools/code_analysis.py",
        f"{planner_dir}/tools/dependency_tools.py",
        f"{planner_dir}/tools/planning_tools.py",
        
        # Utils
        f"{planner_dir}/utils/__init__.py",
        f"{planner_dir}/utils/prompts.py",
        f"{planner_dir}/utils/validators.py",
        
        # Test
        f"{planner_dir}/test_planner.py",
    ]
    
    fixed_count = 0
    total_count = 0
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            total_count += 1
            if fix_imports_in_file(filepath):
                fixed_count += 1
        else:
            print(f"  ⚠️  File not found: {filepath}")
    
    print(f"\n📊 Summary:")
    print(f"  Total files processed: {total_count}")
    print(f"  Files with fixes: {fixed_count}")
    print(f"  Files unchanged: {total_count - fixed_count}")
    
    if fixed_count > 0:
        print(f"\n✅ Import fixes completed! Fixed {fixed_count} files.")
    else:
        print(f"\n✅ All imports are already correct!")

if __name__ == "__main__":
    main()
