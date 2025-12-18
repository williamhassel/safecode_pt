import json, os, subprocess, tempfile, sys
from typing import Any, Dict, List, Optional

def run(cmd: List[str], cwd: str, timeout: int = 60, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr, "timeout": False}
    except subprocess.TimeoutExpired as e:
        return {"cmd": cmd, "returncode": 124, "stdout": e.stdout or "", "stderr": (e.stderr or "") + "\n[runner] Command timed out.", "timeout": True}

def main():
    raw = (sys.stdin.read() or "").strip()
    if not raw:
        print(json.dumps({"ok": False, "error": "No JSON received on stdin", "tests": None, "bandit": None, "semgrep": None, "pip_audit": None}))
        return

    job = json.loads(raw)
    code = job["code"]
    tests = job["tests"]

    out = {"ok": False, "error": None, "tests": None, "bandit": None, "semgrep": None, "pip_audit": None}

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "snippet.py"), "w", encoding="utf-8") as f:
            f.write(code)

        os.mkdir(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "test_snippet.py"), "w", encoding="utf-8") as f:
            f.write(tests)

        # Ensure snippet.py is importable during pytest collection
        env = dict(os.environ)
        env["PYTHONPATH"] = d + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        out["tests"] = run(["pytest", "-q"], cwd=d, timeout=60, env=env)
        out["bandit"] = run(["bandit", "-q", "-r", "."], cwd=d, timeout=60, env=env)
        out["semgrep"] = run(["semgrep", "--config", "p/python", "."], cwd=d, timeout=120, env=env)
        out["pip_audit"] = run(["pip-audit"], cwd=d, timeout=60, env=env)

    out["ok"] = True
    print(json.dumps(out))

if __name__ == "__main__":
    main()