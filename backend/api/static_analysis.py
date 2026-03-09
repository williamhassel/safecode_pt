"""Static analysis agent using Bandit for Python vulnerability verification.

This agent runs as part of the agentic pipeline after Docker test validation.
It confirms that the insecure code actually triggers expected vulnerability
warnings, and that the secure code is clean. For vulnerability types that
Bandit cannot detect (XSS, SSRF, auth_bypass), the check is skipped.
"""
import json
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Bandit test IDs that correspond to each vulnerability type.
# Empty list means Bandit cannot reliably detect this type.
VULN_TYPE_TO_BANDIT_TESTS: dict[str, list[str]] = {
    "sqli":            ["B608"],              # hardcoded SQL expressions
    "cmdi":            ["B602", "B605", "B606", "B607"],  # subprocess with shell
    "xxe":             ["B313", "B314", "B315", "B316", "B317", "B318", "B319", "B320"],
    "insecure_deser":  ["B301", "B302"],      # pickle usage
    "weak_crypto":     ["B303", "B304", "B305"],  # md5/sha1
    "hardcoded_creds": ["B105", "B106", "B107"],  # hardcoded passwords/secrets
    # Bandit has limited coverage for the types below
    "path_traversal":  [],
    "xss":             [],
    "ssrf":            [],
    "auth_bypass":     [],
}


def _run_bandit_on_code(code: str) -> dict:
    """Write code to a temp file, run bandit, return parsed results."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        proc = subprocess.run(
            ["bandit", "-r", tmp_path, "-f", "json", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        try:
            data = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except json.JSONDecodeError:
            data = {}

        issues = data.get("results", [])
        return {
            "ran": True,
            "issues": issues,
            "issue_ids": [i.get("test_id") for i in issues],
        }
    except FileNotFoundError:
        return {"ran": False, "reason": "bandit not installed"}
    except subprocess.TimeoutExpired:
        return {"ran": False, "reason": "bandit timeout"}
    except Exception as exc:
        return {"ran": False, "reason": str(exc)}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def check_challenge_with_bandit(
    insecure_code: str, secure_code: str, vuln_type: str
) -> dict:
    """Run Bandit on both code versions and return a structured result.

    Returns a dict with:
      - skipped (bool): True if Bandit cannot assess this vuln type
      - passed (bool|None): True if insecure is flagged AND secure is clean
      - insecure_flagged (bool): Bandit found expected issues in insecure code
      - secure_clean (bool): Bandit found no expected issues in secure code
      - insecure / secure: raw Bandit output dicts
    """
    expected_tests = VULN_TYPE_TO_BANDIT_TESTS.get(vuln_type, [])

    if not expected_tests:
        return {
            "skipped": True,
            "reason": f"Bandit has no test IDs mapped for {vuln_type}",
            "passed": None,
        }

    insecure_result = _run_bandit_on_code(insecure_code)
    secure_result = _run_bandit_on_code(secure_code)

    if not insecure_result.get("ran") or not secure_result.get("ran"):
        reason = insecure_result.get("reason") or secure_result.get("reason", "unknown")
        return {
            "skipped": True,
            "reason": f"Bandit unavailable: {reason}",
            "passed": None,
            "insecure": insecure_result,
            "secure": secure_result,
        }

    insecure_ids = set(insecure_result["issue_ids"])
    secure_ids = set(secure_result["issue_ids"])
    expected_set = set(expected_tests)

    insecure_flagged = bool(insecure_ids & expected_set)
    secure_clean = not bool(secure_ids & expected_set)
    passed = insecure_flagged and secure_clean

    if not passed:
        if not insecure_flagged:
            logger.warning(
                "Bandit did not flag insecure %s code (expected %s, found %s)",
                vuln_type, expected_tests, list(insecure_ids),
            )
        if not secure_clean:
            logger.warning(
                "Bandit flagged secure %s code (expected clean, found %s)",
                vuln_type, list(secure_ids & expected_set),
            )

    return {
        "skipped": False,
        "passed": passed,
        "insecure_flagged": insecure_flagged,
        "secure_clean": secure_clean,
        "expected_tests": expected_tests,
        "insecure": insecure_result,
        "secure": secure_result,
    }
