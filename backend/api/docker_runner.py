# backend/api/docker_runner.py
import json
import subprocess
from typing import Any, Dict

IMAGE = "challenge-runner"  # <-- set to your real image tag

def run_in_container(job: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    payload = json.dumps(job)

    cmd = [
        "docker", "run", "--rm",
        "-i",                 # keep stdin open
        IMAGE,
        "python", "/work/runner.py"
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=payload,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Docker run timed out after {timeout}s") from e
    except FileNotFoundError as e:
        raise RuntimeError("Docker executable not found. Is Docker Desktop installed and in PATH?") from e

    if proc.returncode != 0:
        # Include both stderr and stdout for debugging; containers sometimes write errors to stdout.
        stderr = (proc.stderr or "")[:4000]
        stdout = (proc.stdout or "")[:4000]
        raise RuntimeError(f"Docker run failed (rc={proc.returncode}).\nSTDERR:\n{stderr}\nSTDOUT:\n{stdout}")

    # runner should print JSON; if not, surface a readable error
    try:
        return json.loads(proc.stdout or "")
    except json.JSONDecodeError as e:
        stdout = (proc.stdout or "")[:4000]
        stderr = (proc.stderr or "")[:4000]
        raise RuntimeError(
            "Container returned non-JSON output.\n"
            f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
        ) from e
