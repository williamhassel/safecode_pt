#!/usr/bin/env python
"""
Test script to systematically verify all 10 OWASP vulnerability types.

This script generates one challenge for each vulnerability type and validates:
1. LLM generates valid JSON
2. Code meets length requirements (20-35 lines)
3. Tests pass on secure code
4. Tests fail on insecure code

Usage:
    python test_all_vulnerabilities.py [--vuln-type TYPE] [--attempts N]

Examples:
    python test_all_vulnerabilities.py                    # Test all types
    python test_all_vulnerabilities.py --vuln-type sqli   # Test only SQL injection
    python test_all_vulnerabilities.py --attempts 3       # Try 3 times per type
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from backend.api.llm_generator import generate_challenge_bundle
from backend.api.docker_runner import run_in_container

# All vulnerability types to test
ALL_VULN_TYPES = [
    "sqli",
    "xss",
    "path_traversal",
    "cmdi",
    "xxe",
    "insecure_deser",
    "ssrf",
    "weak_crypto",
    "hardcoded_creds",
    "auth_bypass",
]

# Seed topics for testing
TEST_SEED_TOPICS = {
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


class VulnTestResult:
    """Container for test results"""
    def __init__(self, vuln_type: str):
        self.vuln_type = vuln_type
        self.success = False
        self.attempts = 0
        self.errors: List[str] = []
        self.secure_line_count = 0
        self.insecure_line_count = 0
        self.secure_tests_passed = False
        self.insecure_tests_failed = False
        self.generation_time = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vuln_type": self.vuln_type,
            "success": self.success,
            "attempts": self.attempts,
            "errors": self.errors,
            "secure_line_count": self.secure_line_count,
            "insecure_line_count": self.insecure_line_count,
            "secure_tests_passed": self.secure_tests_passed,
            "insecure_tests_failed": self.insecure_tests_failed,
            "generation_time": round(self.generation_time, 2),
        }


def test_vulnerability_type(vuln_type: str, max_attempts: int = 3, difficulty: str = "easy") -> VulnTestResult:
    """
    Test a single vulnerability type by generating a challenge and validating it.

    Args:
        vuln_type: The vulnerability type to test
        max_attempts: Maximum number of generation attempts
        difficulty: Challenge difficulty level

    Returns:
        VulnTestResult object with test results
    """
    result = VulnTestResult(vuln_type)
    seed_topic = TEST_SEED_TOPICS.get(vuln_type, "generic application")

    print(f"\n{'='*80}")
    print(f"Testing: {vuln_type.upper()}")
    print(f"Seed topic: {seed_topic}")
    print(f"{'='*80}")

    for attempt in range(1, max_attempts + 1):
        result.attempts = attempt
        print(f"\n[Attempt {attempt}/{max_attempts}]")

        try:
            # Step 1: Generate challenge bundle
            print(f"  → Generating challenge bundle...")
            start_time = datetime.now()
            bundle = generate_challenge_bundle(
                vuln_type=vuln_type,
                seed_topic=seed_topic,
                difficulty=difficulty
            )
            result.generation_time = (datetime.now() - start_time).total_seconds()
            print(f"  ✓ Generated in {result.generation_time:.2f}s")

            # Step 2: Validate code length
            secure_code = bundle["secure_code"]
            insecure_code = bundle["insecure_code"]
            tests = bundle["tests"]

            result.secure_line_count = len(secure_code.strip().splitlines())
            result.insecure_line_count = len(insecure_code.strip().splitlines())

            print(f"  → Code length: secure={result.secure_line_count} lines, insecure={result.insecure_line_count} lines")

            if result.secure_line_count < 20 or result.insecure_line_count < 20:
                error = f"Code too short (min 20 lines required)"
                print(f"  ✗ {error}")
                result.errors.append(error)
                continue

            if result.secure_line_count > 35 or result.insecure_line_count > 35:
                error = f"Code too long (max 35 lines allowed)"
                print(f"  ✗ {error}")
                result.errors.append(error)
                continue

            print(f"  ✓ Code length valid")

            # Step 3: Run tests on secure code
            print(f"  → Running tests on secure code...")
            secure_results = run_in_container({"code": secure_code, "tests": tests})

            secure_ok = bool(secure_results.get("ok", False))
            result.secure_tests_passed = secure_ok and secure_results.get("tests", {}).get("returncode") == 0

            if not result.secure_tests_passed:
                error = f"Secure code tests failed: {secure_results.get('tests', {}).get('stderr', 'Unknown error')[:200]}"
                print(f"  ✗ {error}")
                result.errors.append(error)
                continue

            print(f"  ✓ Secure code tests passed")

            # Step 4: Run tests on insecure code
            print(f"  → Running tests on insecure code...")
            insecure_results = run_in_container({"code": insecure_code, "tests": tests})

            insecure_ok = bool(insecure_results.get("ok", False))
            result.insecure_tests_failed = insecure_ok and insecure_results.get("tests", {}).get("returncode") != 0

            if not result.insecure_tests_failed:
                error = f"Insecure code tests should fail but passed"
                print(f"  ✗ {error}")
                result.errors.append(error)
                continue

            print(f"  ✓ Insecure code tests failed (as expected)")

            # Success!
            result.success = True
            print(f"\n✓ SUCCESS: {vuln_type} challenge validated successfully!")
            return result

        except Exception as e:
            error = f"Exception during generation: {str(e)[:200]}"
            print(f"  ✗ {error}")
            result.errors.append(error)
            continue

    # All attempts failed
    print(f"\n✗ FAILED: {vuln_type} failed after {max_attempts} attempts")
    return result


def print_summary(results: List[VulnTestResult]):
    """Print a summary of all test results"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\nTotal: {len(results)} vulnerability types tested")
    print(f"✓ Successful: {len(successful)}/{len(results)}")
    print(f"✗ Failed: {len(failed)}/{len(results)}")

    if successful:
        print(f"\n{'='*80}")
        print("SUCCESSFUL TYPES:")
        print(f"{'='*80}")
        for r in successful:
            print(f"  ✓ {r.vuln_type:20s} - {r.attempts} attempt(s), {r.generation_time:.1f}s")

    if failed:
        print(f"\n{'='*80}")
        print("FAILED TYPES:")
        print(f"{'='*80}")
        for r in failed:
            print(f"  ✗ {r.vuln_type:20s} - {r.attempts} attempt(s)")
            if r.errors:
                print(f"     Last error: {r.errors[-1][:100]}")

    # Calculate success rate
    success_rate = (len(successful) / len(results) * 100) if results else 0
    print(f"\n{'='*80}")
    print(f"SUCCESS RATE: {success_rate:.1f}%")
    print(f"{'='*80}\n")


def save_results_to_file(results: List[VulnTestResult], filename: str = "vulnerability_test_results.json"):
    """Save test results to JSON file"""
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_tested": len(results),
        "successful": len([r for r in results if r.success]),
        "failed": len([r for r in results if not r.success]),
        "results": [r.to_dict() for r in results]
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Results saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Test all OWASP vulnerability types in SafeCode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--vuln-type",
        choices=ALL_VULN_TYPES,
        help="Test only a specific vulnerability type"
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=3,
        help="Maximum attempts per vulnerability type (default: 3)"
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium"],
        default="easy",
        help="Challenge difficulty level (default: easy)"
    )
    parser.add_argument(
        "--output",
        default="vulnerability_test_results.json",
        help="Output file for results (default: vulnerability_test_results.json)"
    )

    args = parser.parse_args()

    # Determine which types to test
    vuln_types_to_test = [args.vuln_type] if args.vuln_type else ALL_VULN_TYPES

    print("="*80)
    print("SafeCode Vulnerability Type Testing")
    print("="*80)
    print(f"Testing {len(vuln_types_to_test)} vulnerability type(s)")
    print(f"Max attempts per type: {args.attempts}")
    print(f"Difficulty: {args.difficulty}")
    print(f"Output file: {args.output}")

    # Run tests
    results = []
    for vuln_type in vuln_types_to_test:
        result = test_vulnerability_type(vuln_type, max_attempts=args.attempts, difficulty=args.difficulty)
        results.append(result)

    # Print summary
    print_summary(results)

    # Save results
    save_results_to_file(results, args.output)

    # Exit with appropriate code
    failed_count = len([r for r in results if not r.success])
    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
