import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

def main():
    print("=" * 70)
    print("  Starting UniMind AI with AegisOps Full Stack Project...")
    print("=" * 70)

    project_root = Path(__file__).parent.resolve()
    os.chdir(project_root)

    # Ensure Python Virtual Environment
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = sys.executable

    print("\n[1/3] Starting FastAPI Backend API Engine on http://localhost:8000 ...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = f"{project_root / 'backend'}{os.pathsep}{project_root}"

    backend_process = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=str(project_root / "backend"),
        env=backend_env,
    )

    time.sleep(3)

    print("\n[2/3] Starting React Frontend Dashboard on http://localhost:5173 ...")
    frontend_dir = project_root / "frontend"
    frontend_process = subprocess.Popen(
        ["cmd", "/c", "npm", "run", "dev"],
        cwd=str(frontend_dir),
    )

    time.sleep(3)

    print("\n" + "=" * 70)
    print("  SUCCESS: UNIMIND AI WITH AEGISOPS IS RUNNING!")
    print("=" * 70)
    print("  Frontend UI Dashboard      : http://localhost:5173")
    print("  Backend API Swagger Docs  : http://localhost:8000/docs")
    print("  Press Ctrl+C to stop servers.")
    print("=" * 70)

    try:
        webbrowser.open("http://localhost:5173")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping UniMind AI & AegisOps servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
