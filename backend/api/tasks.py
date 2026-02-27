# backend/app/tasks.py
import logging
import random
from celery import shared_task
from django.db import transaction
from .models import GenerationRequest, GeneratedChallenge
from .docker_runner import run_in_container
from .llm_generator import generate_challenge_bundle

logger = logging.getLogger(__name__)

POOL_TARGET = 100       # total pooled challenges to maintain
POOL_MIN_PER_TYPE = 10  # minimum per vulnerability type
POOL_REFILL_THRESHOLD = 20  # trigger refill when total drops below this
REVIEW_QUEUE_TARGET = 10  # challenges pre-generated for admin review

MAX_LLM_ATTEMPTS = 5

# OWASP Top 10 vulnerability types to generate
# All 10 types enabled for testing and verification
VULNERABILITY_TYPES = [
    "sqli",           # SQL Injection - Works perfectly, self-contained with sqlite3
    "xss",            # Cross-Site Scripting - Works well with html.escape()
    "path_traversal", # Path Traversal - Focuses on path validation
    "cmdi",           # Command Injection - Uses mocking or built-in commands only
    "xxe",            # XML External Entity - XML parsing vulnerabilities
    "insecure_deser", # Insecure Deserialization - Pickle/YAML deserialization
    "ssrf",           # Server-Side Request Forgery - URL validation issues
    "weak_crypto",    # Weak Cryptography - Weak algorithms and hashing
    "hardcoded_creds",# Hard-coded Credentials - Credentials in source code
    "auth_bypass",    # Authentication Bypass - Broken authentication logic
]

# Seed topics mapped to vulnerability types
SEED_TOPICS_BY_VULN = {
    "sqli": [
        "user authentication lookup",
        "product search query",
        "blog post retrieval",
        "customer order search",
        "employee records lookup",
    ],
    "xss": [
        "user comment display",
        "blog post rendering",
        "search result display",
        "user profile page",
        "notification messages",
    ],
    "path_traversal": [
        "file download handler",
        "image upload viewer",
        "document retrieval",
        "static file server",
        "backup file access",
    ],
    "cmdi": [
        "image processing utility",
        "file conversion tool",
        "system diagnostics",
        "backup creation",
        "report generator",
    ],
    "xxe": [
        "XML upload processor",
        "config file parser",
        "data import handler",
        "API request parser",
        "document converter",
    ],
    "insecure_deser": [
        "session data handler",
        "cache storage system",
        "user preferences loader",
        "job queue processor",
        "data migration tool",
    ],
    "ssrf": [
        "URL preview generator",
        "webhook handler",
        "image proxy service",
        "external API client",
        "feed aggregator",
    ],
    "weak_crypto": [
        "password hashing system",
        "token generator",
        "session ID creator",
        "API key generator",
        "encryption utility",
    ],
    "hardcoded_creds": [
        "database connection",
        "API client setup",
        "external service auth",
        "admin account creation",
        "backup system config",
    ],
    "auth_bypass": [
        "login validator",
        "permission checker",
        "admin access control",
        "API authentication",
        "session validator",
    ],
}

@shared_task
def generate_challenge(generation_id: int):
    gr = GenerationRequest.objects.get(id=generation_id)
    gr.status = "running"
    gr.save(update_fields=["status"])

    try:
        last_err = None

        for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
            # Pick a random vulnerability type
            vuln_type = random.choice(VULNERABILITY_TYPES)

            # Pick a seed topic appropriate for this vulnerability type
            seed_topics = SEED_TOPICS_BY_VULN.get(vuln_type, ["generic application"])
            seed_topic = random.choice(seed_topics)

            # Generate the challenge bundle
            bundle = generate_challenge_bundle(
                vuln_type=vuln_type,
                seed_topic=seed_topic,
                difficulty="easy"
            )

            secure_code = bundle["secure_code"]
            insecure_code = bundle["insecure_code"]
            tests = bundle["tests"]
            vuln_lines = bundle["vulnerable_lines"]

            # Validate code length before testing (must be 20-35 lines)
            secure_line_count = len(secure_code.strip().splitlines())
            insecure_line_count = len(insecure_code.strip().splitlines())

            if secure_line_count < 20 or insecure_line_count < 20:
                last_err = {
                    "attempt": attempt,
                    "error": "Code too short",
                    "secure_lines": secure_line_count,
                    "insecure_lines": insecure_line_count,
                    "message": "Generated code must be at least 20 lines"
                }
                continue  # Try again

            if secure_line_count > 35 or insecure_line_count > 35:
                last_err = {
                    "attempt": attempt,
                    "error": "Code too long",
                    "secure_lines": secure_line_count,
                    "insecure_lines": insecure_line_count,
                    "message": "Generated code must be at most 35 lines"
                }
                continue  # Try again

            secure_results = run_in_container({"code": secure_code, "tests": tests})
            insecure_results = run_in_container({"code": insecure_code, "tests": tests})

            # Check if docker runner completed successfully
            secure_ok = bool(secure_results.get("ok", False))
            insecure_ok = bool(insecure_results.get("ok", False))

            # Check if tests passed (returncode 0 = all tests passed)
            secure_tests_passed = secure_ok and secure_results.get("tests", {}).get("returncode") == 0
            insecure_tests_failed = insecure_ok and insecure_results.get("tests", {}).get("returncode") != 0

            # Your acceptance criteria:
            # secure code tests must pass, insecure code tests must fail
            if secure_tests_passed and insecure_tests_failed:
                # Generate intelligent distractor options based on the code structure
                code_lines = insecure_code.splitlines()
                total_lines = len(code_lines)

                # Collect all unique line numbers that aren't the vulnerability
                all_line_numbers = set(range(1, total_lines + 1))
                vuln_line_set = set(vuln_lines)
                available_lines = sorted(all_line_numbers - vuln_line_set)

                # Don't use labels - they give away too much
                # Just provide line numbers and let users analyze the code
                vuln_label = ""  # No label for correct answer

                # Determine if we should use line ranges or single lines
                # If the vulnerable lines are a range, make distractors ranges too
                use_ranges = len(vuln_lines) > 1

                # Generate distractor options from different parts of the code
                distractors = []

                # Select lines that have actual code on them (not blank or just braces)
                candidate_lines = []
                for line_num in available_lines:
                    line_content = code_lines[line_num - 1].strip() if line_num <= total_lines else ""
                    # Only include lines with meaningful content
                    if line_content and not line_content in ['{', '}', '(', ')', '"""', "'''", "''", '""']:
                        candidate_lines.append(line_num)

                # Create 3 distractor options
                if len(candidate_lines) >= 3:
                    # Spread distractors across beginning, middle, and end
                    anchor_lines = [
                        candidate_lines[0],  # Beginning
                        candidate_lines[len(candidate_lines) // 2],  # Middle
                        candidate_lines[-1] if len(candidate_lines) > 1 else candidate_lines[0],  # End
                    ]

                    for anchor_line in anchor_lines:
                        if use_ranges:
                            # Create a range of 2-3 lines around the anchor
                            range_size = random.choice([2, 3])
                            start_line = max(1, anchor_line - random.randint(0, 1))
                            end_line = min(total_lines, start_line + range_size - 1)

                            # Make sure it doesn't overlap with vulnerable lines
                            line_range = list(range(start_line, end_line + 1))
                            if not any(line in vuln_lines for line in line_range):
                                distractors.append({"lines": line_range, "label": ""})
                        else:
                            # Use single lines, but sometimes group 2-3 adjacent lines
                            if random.random() < 0.5 and anchor_line < total_lines - 1:
                                # Group 2-3 lines
                                range_size = random.choice([2, 3])
                                line_range = [anchor_line + i for i in range(min(range_size, total_lines - anchor_line + 1))]
                                if not any(line in vuln_lines for line in line_range):
                                    distractors.append({"lines": line_range, "label": ""})
                            else:
                                # Single line
                                distractors.append({"lines": [anchor_line], "label": ""})

                # If we don't have enough distractors, add more
                while len(distractors) < 3:
                    if candidate_lines:
                        anchor_line = random.choice(candidate_lines)
                        if random.random() < 0.6:  # 60% chance of range
                            range_size = random.choice([2, 3])
                            start_line = max(1, anchor_line - random.randint(0, 1))
                            end_line = min(total_lines, start_line + range_size - 1)
                            line_range = list(range(start_line, end_line + 1))
                            if not any(line in vuln_lines for line in line_range):
                                new_distractor = {"lines": line_range, "label": ""}
                                if new_distractor not in distractors:
                                    distractors.append(new_distractor)
                        else:
                            new_distractor = {"lines": [anchor_line], "label": ""}
                            if new_distractor not in distractors:
                                distractors.append(new_distractor)
                    else:
                        distractors.append({"lines": [1], "label": ""})
                        break

                # Build options list with correct answer and distractors
                all_options = [
                    {"lines": vuln_lines, "label": vuln_label, "correct": True},
                ] + [{"lines": d["lines"], "label": d["label"], "correct": False} for d in distractors]

                # Shuffle the options so correct answer isn't always first
                random.shuffle(all_options)

                # Remove the "correct" flag before sending to frontend
                shuffled_options = [{"lines": opt["lines"], "label": opt["label"]} for opt in all_options]

                # Build final options list: correct answer + distractors
                artifact = {
                    **bundle,
                    "options": shuffled_options,
                    "verification": {
                        "secure": secure_results,
                        "insecure": insecure_results,
                        "attempt": attempt,
                    },
                }

                with transaction.atomic():
                    GeneratedChallenge.objects.create(
                        generation=gr,
                        language=bundle["language"],
                        vuln_type=bundle["vuln_type"],
                        difficulty=bundle["difficulty"],
                        artifact=artifact,
                    )
                    gr.status = "done"
                    gr.save(update_fields=["status"])

                return  # success

            last_err = {
                "attempt": attempt,
                "secure_tests_passed": secure_tests_passed,
                "insecure_tests_failed": insecure_tests_failed,
                "secure_results": secure_results,
                "insecure_results": insecure_results,
            }

        # If we get here, all attempts failed acceptance criteria
        raise RuntimeError(f"LLM bundle failed verification after {MAX_LLM_ATTEMPTS} attempts: {last_err}")

    except Exception as e:
        gr.status = "failed"
        gr.error = str(e)
        gr.save(update_fields=["status", "error"])
        raise


def _generate_and_save_challenge(vuln_type=None, is_pooled=False, status='pending_review'):
    """Generate a single validated challenge and save it to the database.

    Returns the GeneratedChallenge instance on success, or None on failure.
    """
    if vuln_type is None:
        vuln_type = random.choice(VULNERABILITY_TYPES)

    seed_topics = SEED_TOPICS_BY_VULN.get(vuln_type, ["generic application"])

    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        seed_topic = random.choice(seed_topics)
        try:
            bundle = generate_challenge_bundle(
                vuln_type=vuln_type,
                seed_topic=seed_topic,
                difficulty="easy",
            )
        except Exception as exc:
            logger.warning("Challenge generation attempt %d/%d failed (LLM error): %s", attempt, MAX_LLM_ATTEMPTS, exc)
            continue

        secure_code = bundle["secure_code"]
        insecure_code = bundle["insecure_code"]
        tests = bundle["tests"]
        vuln_lines = bundle["vulnerable_lines"]

        if len(secure_code.strip().splitlines()) < 20 or len(insecure_code.strip().splitlines()) < 20:
            continue
        if len(secure_code.strip().splitlines()) > 35 or len(insecure_code.strip().splitlines()) > 35:
            continue

        secure_results = run_in_container({"code": secure_code, "tests": tests})
        insecure_results = run_in_container({"code": insecure_code, "tests": tests})

        secure_ok = secure_results.get("ok") and secure_results.get("tests", {}).get("returncode") == 0
        insecure_ok = insecure_results.get("ok") and insecure_results.get("tests", {}).get("returncode") != 0

        if not (secure_ok and insecure_ok):
            continue

        # Build distractor options
        code_lines = insecure_code.splitlines()
        total_lines = len(code_lines)
        all_line_numbers = set(range(1, total_lines + 1))
        vuln_line_set = set(vuln_lines)
        available_lines = sorted(all_line_numbers - vuln_line_set)
        use_ranges = len(vuln_lines) > 1

        candidate_lines = [
            ln for ln in available_lines
            if code_lines[ln - 1].strip() and code_lines[ln - 1].strip() not in ['{', '}', '(', ')', '"""', "'''", "''", '""']
        ]

        distractors = []
        if len(candidate_lines) >= 3:
            anchors = [candidate_lines[0], candidate_lines[len(candidate_lines) // 2], candidate_lines[-1]]
            for anchor in anchors:
                if use_ranges:
                    start = max(1, anchor - random.randint(0, 1))
                    end = min(total_lines, start + random.choice([2, 3]) - 1)
                    lr = list(range(start, end + 1))
                    if not any(l in vuln_lines for l in lr):
                        distractors.append({"lines": lr, "label": ""})
                else:
                    if random.random() < 0.5 and anchor < total_lines - 1:
                        sz = random.choice([2, 3])
                        lr = [anchor + i for i in range(min(sz, total_lines - anchor + 1))]
                        if not any(l in vuln_lines for l in lr):
                            distractors.append({"lines": lr, "label": ""})
                    else:
                        distractors.append({"lines": [anchor], "label": ""})

        while len(distractors) < 3:
            anchor = random.choice(candidate_lines) if candidate_lines else 1
            distractors.append({"lines": [anchor], "label": ""})

        all_options = [{"lines": vuln_lines, "label": "", "correct": True}] + \
                      [{"lines": d["lines"], "label": "", "correct": False} for d in distractors]
        random.shuffle(all_options)
        shuffled_options = [{"lines": o["lines"], "label": o["label"]} for o in all_options]

        artifact = {
            **bundle,
            "options": shuffled_options,
            "verification": {"secure": secure_results, "insecure": insecure_results, "attempt": attempt},
        }

        gr = GenerationRequest.objects.create(status="done")
        ch = GeneratedChallenge.objects.create(
            generation=gr,
            language=bundle["language"],
            vuln_type=bundle["vuln_type"],
            difficulty=bundle["difficulty"],
            artifact=artifact,
            is_pooled=is_pooled,
            status=status,
        )
        logger.info("Generated %s challenge #%d (status=%s, is_pooled=%s)", vuln_type, ch.id, status, is_pooled)
        return ch

    logger.warning("Failed to generate %s challenge after %d attempts", vuln_type, MAX_LLM_ATTEMPTS)
    return None


def _generate_one_pooled_challenge(vuln_type=None):
    """Generate a single validated challenge and add it directly to the pool."""
    return _generate_and_save_challenge(vuln_type=vuln_type, is_pooled=True, status='approved')


@shared_task
def populate_challenge_pool():
    """Fill the challenge pool up to POOL_TARGET (POOL_MIN_PER_TYPE per vuln type)."""
    counts = {vt: GeneratedChallenge.objects.filter(is_pooled=True, vuln_type=vt).count()
              for vt in VULNERABILITY_TYPES}
    total = sum(counts.values())
    logger.info("Pool populate started. Current counts: %s (total=%d)", counts, total)

    added = 0
    for vuln_type in VULNERABILITY_TYPES:
        needed = max(0, POOL_MIN_PER_TYPE - counts[vuln_type])
        for _ in range(needed):
            ch = _generate_one_pooled_challenge(vuln_type=vuln_type)
            if ch:
                added += 1

    logger.info("Pool populate complete. Added %d challenges.", added)
    return added


@shared_task
def refill_pool_if_low():
    """Periodic task: top up the pool if total drops below POOL_REFILL_THRESHOLD."""
    total = GeneratedChallenge.objects.filter(is_pooled=True).count()
    logger.info("Pool refill check: %d pooled challenges available.", total)
    if total < POOL_REFILL_THRESHOLD:
        logger.info("Pool below threshold (%d), triggering populate.", POOL_REFILL_THRESHOLD)
        populate_challenge_pool.delay()


@shared_task
def fill_review_queue():
    """Generate challenges for the admin review queue up to REVIEW_QUEUE_TARGET."""
    pending = GeneratedChallenge.objects.filter(status='pending_review').count()
    needed = max(0, REVIEW_QUEUE_TARGET - pending)
    logger.info("Review queue fill started. Pending=%d, needed=%d", pending, needed)

    added = 0
    for _ in range(needed):
        ch = _generate_and_save_challenge(is_pooled=False, status='pending_review')
        if ch:
            added += 1

    logger.info("Review queue fill complete. Added %d challenges.", added)
    return added
