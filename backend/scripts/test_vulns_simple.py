"""
Simple direct test - imports only the generator function.

Usage (from project root with venv activated):
    python backend/scripts/test_vulns_simple.py
"""

import os
import sys
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


def test_vuln_type(vuln_type: str):
    """Test a single vulnerability type"""
    print(f"\n{'='*80}")
    print(f"Testing: {vuln_type.upper()}")
    print(f"{'='*80}")

    seed_topic = SEED_TOPICS[vuln_type]
    print(f"Seed topic: {seed_topic}")

    try:
        print(f"-> Generating challenge...")
        start_time = datetime.now()

        bundle = generate_challenge_bundle(
            vuln_type=vuln_type,
            seed_topic=seed_topic,
            difficulty="easy"
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"[OK] Generated in {elapsed:.1f}s")

        # Check code length
        secure_lines = len(bundle["secure_code"].strip().splitlines())
        insecure_lines = len(bundle["insecure_code"].strip().splitlines())

        print(f"-> Secure code: {secure_lines} lines")
        print(f"-> Insecure code: {insecure_lines} lines")

        # Validate length
        if secure_lines < 20 or insecure_lines < 20:
            print(f"[FAIL] Code too short (minimum 20 lines)")
            return False

        if secure_lines > 35 or insecure_lines > 35:
            print(f"[FAIL] Code too long (maximum 35 lines)")
            return False

        print(f"[OK] Code length valid")

        # Show preview
        print(f"\nSecure code preview (first 5 lines):")
        for i, line in enumerate(bundle["secure_code"].splitlines()[:5], 1):
            print(f"  {i}: {line}")
        print(f"  ...")

        print(f"\n[SUCCESS]")
        print(f"  Vulnerable lines: {bundle['vulnerable_lines']}")

        return True

    except Exception as e:
        print(f"[FAIL] {str(e)[:300]}")
        return False


def main():
    """Test all vulnerability types"""
    print("="*80)
    print("Testing All 10 OWASP Vulnerability Types")
    print("="*80)

    results = {}

    for vuln_type in VULN_TYPES:
        success = test_vuln_type(vuln_type)
        results[vuln_type] = success

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    successful = [v for v, s in results.items() if s]
    failed = [v for v, s in results.items() if not s]

    print(f"\n[OK] Successful: {len(successful)}/{len(VULN_TYPES)}")
    for v in successful:
        print(f"  - {v}")

    if failed:
        print(f"\n[FAIL] Failed: {len(failed)}/{len(VULN_TYPES)}")
        for v in failed:
            print(f"  - {v}")

    success_rate = len(successful) / len(VULN_TYPES) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
