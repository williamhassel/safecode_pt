from celery import shared_task
from .models import GenerationRequest, GeneratedChallenge
from .docker_runner import run_in_container

def make_mvp_secure_bundle():
    # Hardcoded MVP example. Replace this with LLM generation once the loop works.
    secure_code = """\
import sqlite3

def get_user(conn, username: str):
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    return cur.fetchall()
"""
    tests = """\
import sqlite3
from snippet import get_user

def test_get_user_param_query_not_bypass():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    cur.execute("INSERT INTO users(username) VALUES ('alice'), ('bob')")
    conn.commit()

    # normal
    assert get_user(conn, "alice") == [(1, "alice")]

    # injection attempt should not return both rows
    rows = get_user(conn, "' OR 1=1 --")
    assert rows == []
"""
    return secure_code, tests

def mutate_to_insecure(secure_code: str) -> str:
    # Minimal “injection”: unsafe string formatting
    return secure_code.replace(
        'cur.execute("SELECT id, username FROM users WHERE username = ?", (username,))',
        'cur.execute(f"SELECT id, username FROM users WHERE username = \'{username}\'")'
    )

@shared_task
def generate_challenge(generation_id: int):
    gr = GenerationRequest.objects.get(id=generation_id)
    gr.status = "running"
    gr.save(update_fields=["status"])

    try:
        secure_code, tests = make_mvp_secure_bundle()

        secure_results = run_in_container({"code": secure_code, "tests": tests})

        insecure_code = mutate_to_insecure(secure_code)
        insecure_results = run_in_container({"code": insecure_code, "tests": tests})

        # Compute vulnerable line(s) deterministically (MVP heuristic)
        vuln_lines = []
        for i, line in enumerate(insecure_code.splitlines(), start=1):
            if "cur.execute(f" in line:
                vuln_lines.append(i)

        options = [
            {"lines": vuln_lines, "label": "Unsafe query construction allows SQL injection."},
            {"lines": [max(1, vuln_lines[0]-1)], "label": "Input handling line (distractor)."},
            {"lines": [min(len(insecure_code.splitlines()), vuln_lines[0]+1)], "label": "Return line (distractor)."},
            {"lines": [1], "label": "Import line (distractor)."},
        ]

        artifact = {
            "language": "python",
            "vuln_type": "sqli",
            "difficulty": "easy",
            "secure_code": secure_code,
            "insecure_code": insecure_code,
            "vulnerable_lines": vuln_lines,
            "options": options,
            "tests": tests,
            "verification": {
                "secure": secure_results,
                "insecure": insecure_results,
            },
            "explanation": {
                "short": "The insecure version builds SQL by concatenating user input.",
                "fix": "Use parameterized queries with placeholders."
            }
        }

        GeneratedChallenge.objects.create(
            generation=gr,
            language="python",
            vuln_type="sqli",
            difficulty="easy",
            artifact=artifact,
        )

        gr.status = "done"
        gr.save(update_fields=["status"])

    except Exception as e:
        gr.status = "failed"
        gr.error = str(e)
        gr.save(update_fields=["status", "error"])
        raise
