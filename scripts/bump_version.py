import sys
import toml
from pathlib import Path

def bump_version(bump_type):
    p = Path("pyproject.toml")
    if not p.exists():
        print("pyproject.toml not found")
        sys.exit(1)
        
    data = toml.loads(p.read_text())
    current_version = data["project"]["version"]
    major, minor, patch = map(int, current_version.split("."))
    
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        print(f"Unknown bump type: {bump_type}")
        sys.exit(1)
        
    new_version = f"{major}.{minor}.{patch}"
    data["project"]["version"] = new_version
    
    with open(p, "w") as f:
        toml.dump(data, f)
        
    print(new_version)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py [major|minor|patch]")
        sys.exit(1)
    
    bump_version(sys.argv[1])
