#!/usr/bin/env python3
"""
UniMind AI + AegisOps: Professional Enterprise Supervisor & Quickstart Script.
Cross-platform orchestrator (Windows, macOS, Linux) with automated preflight checks,
graceful process tree termination, and unified observability logging.
"""
import sys
import os
import signal
import socket
import subprocess
import time
import webbrowser
from pathlib import Path


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a network port is already bound by an active process."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_python_executable(project_root: Path) -> Path:
    """Detects active virtual environment Python across Windows and POSIX systems."""
    candidates = [
        project_root / ".venv" / "Scripts" / "python.exe",
        project_root / ".venv" / "bin" / "python",
        project_root / "venv" / "Scripts" / "python.exe",
        project_root / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return Path(sys.executable)


def terminate_process_tree(proc: subprocess.Popen):
    """Gracefully kills a process and all its spawned children across platforms."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main():
    print("=" * 75)
    print("  🏛️  UniMind AI + AegisOps Unified Enterprise Platform Supervisor")
    print("=" * 75)

    project_root = Path(__file__).parent.resolve()
    os.chdir(project_root)

    # 1. Detect Python Executable
    venv_python = find_python_executable(project_root)
    print(f"\n[Preflight] Using Python Runtime: {venv_python}")

    # 2. Port Preflight Verification
    backend_port = 8000
    frontend_port = 5173

    if is_port_in_use(backend_port):
        print(f"[Warning] Port {backend_port} is already in use. Backend might encounter binding errors.")
    if is_port_in_use(frontend_port):
        print(f"[Warning] Port {frontend_port} is already in use. Vite may choose another port.")

    # 3. Frontend Dependencies Preflight
    frontend_dir = project_root / "frontend"
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("[Preflight] 'node_modules' not found in frontend/. Installing dependencies...")
        npm_install_cmd = ["npm.cmd" if os.name == "nt" else "npm", "install"]
        subprocess.run(npm_install_cmd, cwd=str(frontend_dir), check=False)

    # 4. Launch FastAPI Backend Engine
    print(f"\n[1/2] Starting FastAPI Enterprise Backend on http://localhost:{backend_port} ...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = f"{project_root / 'backend'}{os.pathsep}{project_root}"

    backend_process = subprocess.Popen(
        [
            str(venv_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            str(backend_port),
            "--reload",
        ],
        cwd=str(project_root / "backend"),
        env=backend_env,
    )

    # Wait for backend to initialize
    time.sleep(2.5)

    # 5. Launch React 18 + Vite Frontend Dashboard
    print(f"[2/2] Starting React Frontend Dashboard on http://localhost:{frontend_port} ...")
    npm_cmd = ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"]
    frontend_process = subprocess.Popen(
        npm_cmd,
        cwd=str(frontend_dir),
        shell=os.name == "nt",
    )

    time.sleep(2.0)

    print("\n" + "=" * 75)
    print("  🚀 PLATFORM ONLINE: UNIMIND AI + AEGISOPS IS READY")
    print("=" * 75)
    print(f"  📊 Frontend UI Dashboard      : http://localhost:{frontend_port}")
    print(f"  📚 Backend API Swagger Docs  : http://localhost:{backend_port}/docs")
    print(f"  🔍 Health Probe Endpoint      : http://localhost:{backend_port}/health")
    print(f"  🔑 Default Admin Credentials  : admin / password")
    print("=" * 75)
    print("  Press Ctrl+C to gracefully terminate all platform servers.\n")

    try:
        webbrowser.open(f"http://localhost:{frontend_port}")
        while True:
            # Monitor if child processes prematurely died
            if backend_process.poll() is not None:
                print("\n[Notice] Backend process terminated.")
                break
            if frontend_process.poll() is not None:
                print("\n[Notice] Frontend process terminated.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Shutdown] Received interrupt signal. Stopping UniMind AI & AegisOps servers...")
    finally:
        terminate_process_tree(backend_process)
        terminate_process_tree(frontend_process)
        print("[Shutdown] All platform servers cleanly terminated. Goodbye.")


if __name__ == "__main__":
    main()
