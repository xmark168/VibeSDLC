#!/usr/bin/env python3
"""Debug dependency identification"""

from pathlib import Path

def identify_deps(current_file: str, created_files: list) -> list:
    dependencies = []
    current_file = current_file.replace("\\", "/")
    created_files = [f.replace("\\", "/") for f in created_files]
    
    current_name = Path(current_file).stem
    print(f"Current file: {current_file}")
    print(f"Current name (stem): {current_name}")
    
    if "/repositories/" in current_file:
        base_name = current_name.replace("Repository", "")
        print(f"Base name: {base_name}")
        print(f"Looking for models with '{base_name.lower()}' in name...")
        
        for created in created_files:
            print(f"  Checking: {created}")
            if "/models/" in created:
                print(f"    Is a model file")
                if base_name.lower() in created.lower():
                    print(f"    ✅ Match! '{base_name.lower()}' found in '{created.lower()}'")
                    dependencies.append(created)
                else:
                    print(f"    ❌ No match: '{base_name.lower()}' not in '{created.lower()}'")
    
    return dependencies

# Test
created_files = [
    "src/models/User.js",
    "src/repositories/userRepository.js",
    "src/services/authService.js"
]

current = "src/repositories/userRepository.js"
deps = identify_deps(current, created_files)

print(f"\nResult: {deps}")

