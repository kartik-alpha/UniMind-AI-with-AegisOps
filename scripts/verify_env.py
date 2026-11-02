import sys
import os
from pathlib import Path

def run_verification():
    print("=" * 60)
    print("  UniMind AI & AegisOps - Phase 0 Environment Verification")
    print("=" * 60)
    
    # 1. Check Python Version
    py_version = sys.version_info
    print(f"\n[1/4] Python Version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 10):
        print("   WARNING: Python 3.10+ recommended for best compatibility.")
    else:
        print("   Python version is compatible.")

    # 2. Check Directory Structure
    required_dirs = [
        "backend/app/core",
        "backend/app/api/v1/endpoints",
        "backend/app/models",
        "backend/app/schemas",
        "backend/app/services",
        "backend/app/db",
        "frontend",
        "ai",
        "rag",
        "ml",
        "aegisops",
        "services",
        "monitoring",
        "kubernetes",
        "scripts",
        "docs"
    ]
    print("\n[2/4] Checking Directory Structure:")
    all_dirs_exist = True
    for d in required_dirs:
        if not Path(d).exists():
            print(f"  Missing folder: {d}")
            all_dirs_exist = False
    if all_dirs_exist:
        print("   All project directories exist.")

    # 3. Check Files
    required_files = [
        ".gitignore",
        ".env.example",
        ".env",
        "backend/requirements.txt"
    ]
    print("\n[3/4] Checking Required Files:")
    all_files_exist = True
    for f in required_files:
        if not Path(f).is_file():
            print(f"  Missing file: {f}")
            all_files_exist = False
        else:
            print(f"  Found file: {f}")

    # 4. Check Virtual Environment
    print("\n[4/4] Virtual Environment Status:")
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        print("   Virtual environment is ACTIVE.")
    else:
        print("    Virtual environment is NOT active. Please activate .venv before installing requirements.")

    print("\n" + "=" * 60)
    if all_dirs_exist and all_files_exist:
        print(" PHASE 0 FOUNDATION VERIFIED SUCCESSFULLY!")
    else:
        print(" Some checks failed. Please check the items marked with ❌ above.")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()