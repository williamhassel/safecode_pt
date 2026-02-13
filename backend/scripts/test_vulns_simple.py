"""
Simple direct test - imports only the generator function.

Usage (from project root with venv activated):
    python backend/scripts/test_vulns_simple.py
    python backend/scripts/test_vulns_simple.py --attempts 3
    python backend/scripts/test_vulns_simple.py --type xss --attempts 5
"""

import os
import sys
import argparse
from datetime import datetime

# Setup path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, 'backend', '.env'))

# Import directly from the module file to avoid backend.__init__
import importlib.util
spec = importlib.util.spec_from_file_location(
    "llm_generator",
    os.path.join(project_root, 'backend', 'api', 'llm_generator.py')
)
llm_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_generator)

generate_challenge_bundle = llm_generator.generate_challenge_bundle

# Test data
VULN_TYPES = [
    "sqli", "xss", "path_traversal", "cmdi", "xxe",
    "insecure_deser", "ssrf", "weak_crypto", "hardcoded_creds", "auth_bypass"
]

SEED_TOPICS = {
    "sqli": "user authentication lookup",
    "xss": "user comment display",
    "path_traversal": "file download handler",
    "cmdi": "system diagnostics",
    "xxe": "XML upload processor",
    "insecure_deser": "session data handler",
    "ssrf": "URL preview generator",
    "weak_crypto": "password hashing system",
    "hardcoded_creds": "database connection",
    "auth_bypass": "login validator",
}


def test_single_attempt(vuln_type: str, attempt: int, max_attempts: int):
    """Run one generation attempt. Returns (success, details_dict)."""
    seed_topic = SEED_TOPICS[vuln_type]

    try:
        print(f"  Attempt {attempt}/{max_attempts} ... ", end="", flush=True)
        start_time = datetime.now()

        bundle = generate_challenge_bundle(
            vuln_type=vuln_type,
            seed_topic=seed_topic,
            difficulty="easy"
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        secure_lines = len(bundle["secure_code"].strip().splitlines())
        insecure_lines = len(bundle["insecure_code"].strip().splitlines())

        if secure_lines < 20 or insecure_lines < 20:
            print(f"FAIL  secure={secure_lines} insecure={insecure_lines}  (too short, min 20)")
            return False, {"reason": "too_short", "secure": secure_lines, "insecure": insecure_lines}

        if secure_lines > 35 or insecure_lines > 35:
            print(f"FAIL  secure={secure_lines} insecure={insecure_lines}  (too long, max 35)")
            return False, {"reason": "too_long", "secure": secure_lines, "insecure": insecure_lines}

        print(f"OK    secure={secure_lines} insecure={insecure_lines}  ({elapsed:.1f}s)")
        return True, {"secure": secure_lines, "insecure": insecure_lines, "time": elapsed}

    except Exception as e:
        print(f"ERROR {str(e)[:100]}")
        return False, {"reason": "exception", "error": str(e)[:200]}


def test_vuln_type(vuln_type: str, max_attempts: int):
    """Test a vulnerability type with multiple attempts. Returns (successes, attempts, details)."""
    print(f"\n{'='*80}")
    print(f" {vuln_type.upper()}")
    print(f"{'='*80}")

    successes = 0
    details = []

    for attempt in range(1, max_attempts + 1):
        success, info = test_single_attempt(vuln_type, attempt, max_attempts)
        details.append(info)
        if success:
            successes += 1

    rate = (successes / max_attempts) * 100
    print(f"  Result: {successes}/{max_attempts} passed ({rate:.0f}%)")
    return successes, max_attempts, details


def main():
    parser = argparse.ArgumentParser(description="Test OWASP vulnerability types")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per type (default: 3)")
    parser.add_argument("--type", type=str, choices=VULN_TYPES, help="Test only one type")
    args = parser.parse_args()

    types_to_test = [args.type] if args.type else VULN_TYPES

    print("=" * 80)
    print(f"Testing {len(types_to_test)} vulnerability type(s), {args.attempts} attempt(s) each")
    print("=" * 80)

    results = {}
    for vuln_type in types_to_test:
        successes, attempts, details = test_vuln_type(vuln_type, args.attempts)
        results[vuln_type] = (successes, attempts, details)

    # Summary
    print("\n" + "=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print(f"\n  {'Type':<20} {'Pass Rate':<15} {'Result'}")
    print(f"  {'-'*20} {'-'*15} {'-'*10}")

    all_reliable = True
    for vuln_type in types_to_test:
        successes, attempts, details = results[vuln_type]
        rate = (successes / attempts) * 100
        status = "OK" if successes == attempts else ("PARTIAL" if successes > 0 else "FAIL")
        if successes < attempts:
            all_reliable = False
        print(f"  {vuln_type:<20} {successes}/{attempts} ({rate:3.0f}%)      {status}")

    total_s = sum(r[0] for r in results.values())
    total_a = sum(r[1] for r in results.values())
    print(f"\n  Overall: {total_s}/{total_a} ({total_s/total_a*100:.0f}%)")

    return 0 if all_reliable else 1


if __name__ == "__main__":
    sys.exit(main())
