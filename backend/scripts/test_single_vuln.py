#!/usr/bin/env python
"""
Standalone test script for individual vulnerability types.
Does not require Django setup - just tests LLM generation directly.

Usage:
    python test_single_vuln.py sqli
    python test_single_vuln.py xss
"""

import os
import sys
import json
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv('backend/.env')

# Import the generator directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backend.api.llm_generator import generate_challenge_bundle

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


def test_vuln_type(vuln_type: str, max_attempts: int = 3):
    """Test a single vulnerability type"""
    print(f"\n{'='*80}")
    print(f"Testing: {vuln_type.upper()}")
    print(f"{'='*80}")

    seed_topic = SEED_TOPICS.get(vuln_type, "generic application")

    for attempt in range(1, max_attempts + 1):
        print(f"\n[Attempt {attempt}/{max_attempts}]")

        try:
            # Generate challenge
            print(f"  → Generating challenge bundle...")
            start_time = datetime.now()
            bundle = generate_challenge_bundle(
                vuln_type=vuln_type,
                seed_topic=seed_topic,
                difficulty="easy"
            )
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"  ✓ Generated in {elapsed:.2f}s")

            # Check code length
            secure_lines = len(bundle["secure_code"].strip().splitlines())
            insecure_lines = len(bundle["insecure_code"].strip().splitlines())

            print(f"  → Code length: secure={secure_lines} lines, insecure={insecure_lines} lines")

            if secure_lines < 20 or insecure_lines < 20:
                print(f"  ✗ Code too short (min 20 lines)")
                continue

            if secure_lines > 35 or insecure_lines > 35:
                print(f"  ✗ Code too long (max 35 lines)")
                continue

            print(f"  ✓ Code length valid")

            # Show snippet of generated code
            print(f"\n  Secure code preview:")
            for i, line in enumerate(bundle["secure_code"].splitlines()[:5], 1):
                print(f"    {i}: {line}")
            print(f"    ...")

            print(f"\n  ✓ SUCCESS: {vuln_type} generated valid challenge!")
            print(f"\n  Vulnerability type: {bundle['vuln_type']}")
            print(f"  Difficulty: {bundle['difficulty']}")
            print(f"  Vulnerable lines: {bundle['vulnerable_lines']}")

            # Save full output
            output_file = f"test_output_{vuln_type}.json"
            with open(output_file, 'w') as f:
                json.dump(bundle, f, indent=2)
            print(f"\n  Full output saved to: {output_file}")

            return True

        except Exception as e:
            print(f"  ✗ Error: {str(e)[:200]}")
            continue

    print(f"\n✗ FAILED: {vuln_type} failed after {max_attempts} attempts")
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_single_vuln.py <vuln_type>")
        print(f"Available types: {', '.join(VULN_TYPES)}")
        sys.exit(1)

    vuln_type = sys.argv[1]

    if vuln_type not in VULN_TYPES:
        print(f"Error: Unknown vulnerability type: {vuln_type}")
        print(f"Available types: {', '.join(VULN_TYPES)}")
        sys.exit(1)

    max_attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    success = test_vuln_type(vuln_type, max_attempts)
    sys.exit(0 if success else 1)
