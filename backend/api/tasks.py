# backend/app/tasks.py
import logging
import random
from celery import shared_task
from django.db import transaction
from .models import GenerationRequest, GeneratedChallenge
from .docker_runner import run_in_container
from .llm_generator import generate_challenge_bundle
from .static_analysis import check_challenge_with_bandit

logger = logging.getLogger(__name__)

POOL_TARGET = 100       # total pooled challenges to maintain
POOL_MIN_PER_TYPE = 10  # minimum per vulnerability type
POOL_REFILL_THRESHOLD = 20  # trigger refill when total drops below this
REVIEW_QUEUE_TARGET = 10  # challenges pre-generated for admin review

MAX_LLM_ATTEMPTS = 5

CODE_MIN_LINES = 25
CODE_MAX_LINES = 60  # hard ceiling enforced here; prompts target 25-50

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

def _is_displayable_line(line: str) -> bool:
    """Return True if a line is an executable statement suitable as a distractor.

    Rejects blank lines, comment lines, and docstring delimiter lines so that
    the multiple-choice options never suggest a code comment is vulnerable.
    """
    s = line.strip()
    if not s:
        return False
    if s.startswith('#'):
        return False
    # Standalone triple-quote delimiters (opening or closing docstrings)
    if s in ('"""', "'''"):
        return False
    # Single-line docstrings that are pure string literals (not assignments)
    if (s.startswith('"""') and s.endswith('"""')) or (s.startswith("'''") and s.endswith("'''")):
        return False
    return True


def _build_distractor_options(bundle: dict, code_lines: list, vuln_lines: list) -> list:
    """Return 3 distractor option dicts using LLM-provided options where valid.

    Falls back to heuristic selection for any option the LLM got wrong.
    Each dict has the shape {"lines": [...], "label": ""}.
    """
    vuln_set = set(vuln_lines)
    total = len(code_lines)

    # --- Try LLM-generated distractors first ---
    valid: list[dict] = []
    for option in bundle.get("distractor_options", []):
        if not option:
            continue
        # Must not overlap with the answer
        if any(ln in vuln_set for ln in option):
            continue
        # All referenced lines must exist and be displayable
        if any(ln < 1 or ln > total for ln in option):
            continue
        if not all(_is_displayable_line(code_lines[ln - 1]) for ln in option):
            continue
        valid.append({"lines": list(option), "label": ""})
        if len(valid) == 3:
            break

    # --- Heuristic fallback for any missing slots ---
    candidate_lines = [
        ln for ln in range(1, total + 1)
        if ln not in vuln_set and _is_displayable_line(code_lines[ln - 1])
    ]

    while len(valid) < 3 and candidate_lines:
        # Spread across beginning, middle, end of the code
        positions = [0, len(candidate_lines) // 2, len(candidate_lines) - 1]
        for pos in positions:
            if len(valid) >= 3:
                break
            anchor = candidate_lines[pos]
            # Group 2 adjacent lines when the answer is also a range
            if len(vuln_lines) > 1 and anchor < total:
                lr = [anchor, anchor + 1] if anchor + 1 not in vuln_set else [anchor]
            else:
                lr = [anchor]
            candidate = {"lines": lr, "label": ""}
            if candidate not in valid:
                valid.append(candidate)

        # If we still need more, pick randomly from remaining candidates
        if len(valid) < 3:
            remaining = [ln for ln in candidate_lines
                         if not any(ln in d["lines"] for d in valid)]
            if remaining:
                anchor = random.choice(remaining)
                valid.append({"lines": [anchor], "label": ""})
            else:
                break

    # Pad with a safe fallback if we somehow still don't have 3
    while len(valid) < 3:
        valid.append({"lines": [1], "label": ""})

    return valid[:3]


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

            # Validate code length
            secure_line_count = len(secure_code.strip().splitlines())
            insecure_line_count = len(insecure_code.strip().splitlines())

            if secure_line_count < CODE_MIN_LINES or insecure_line_count < CODE_MIN_LINES:
                last_err = {
                    "attempt": attempt,
                    "error": "Code too short",
                    "secure_lines": secure_line_count,
                    "insecure_lines": insecure_line_count,
                }
                continue

            if secure_line_count > CODE_MAX_LINES or insecure_line_count > CODE_MAX_LINES:
                last_err = {
                    "attempt": attempt,
                    "error": "Code too long",
                    "secure_lines": secure_line_count,
                    "insecure_lines": insecure_line_count,
                }
                continue

            # --- Verification agent: Docker test execution ---
            secure_results = run_in_container({"code": secure_code, "tests": tests})
            insecure_results = run_in_container({"code": insecure_code, "tests": tests})

            secure_tests_passed = (
                secure_results.get("ok") and
                secure_results.get("tests", {}).get("returncode") == 0
            )
            insecure_tests_failed = (
                insecure_results.get("ok") and
                insecure_results.get("tests", {}).get("returncode") != 0
            )

            if secure_tests_passed and insecure_tests_failed:
                # --- Static analysis agent: Bandit ---
                bandit_result = check_challenge_with_bandit(insecure_code, secure_code, vuln_type)

                # --- Distractor generation (LLM-first, heuristic fallback) ---
                code_lines = insecure_code.splitlines()
                distractors = _build_distractor_options(bundle, code_lines, vuln_lines)

                all_options = [{"lines": vuln_lines, "label": "", "correct": True}] + \
                              [{"lines": d["lines"], "label": "", "correct": False} for d in distractors]
                random.shuffle(all_options)
                shuffled_options = [{"lines": o["lines"], "label": o["label"]} for o in all_options]

                artifact = {
                    **bundle,
                    "options": shuffled_options,
                    "verification": {
                        "secure": secure_results,
                        "insecure": insecure_results,
                        "attempt": attempt,
                        "bandit": bandit_result,
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

        if len(secure_code.strip().splitlines()) < CODE_MIN_LINES or \
                len(insecure_code.strip().splitlines()) < CODE_MIN_LINES:
            continue
        if len(secure_code.strip().splitlines()) > CODE_MAX_LINES or \
                len(insecure_code.strip().splitlines()) > CODE_MAX_LINES:
            continue

        # --- Verification agent: Docker test execution ---
        secure_results = run_in_container({"code": secure_code, "tests": tests})
        insecure_results = run_in_container({"code": insecure_code, "tests": tests})

        secure_ok = secure_results.get("ok") and secure_results.get("tests", {}).get("returncode") == 0
        insecure_ok = insecure_results.get("ok") and insecure_results.get("tests", {}).get("returncode") != 0

        if not (secure_ok and insecure_ok):
            continue

        # --- Static analysis agent: Bandit ---
        bandit_result = check_challenge_with_bandit(insecure_code, secure_code, vuln_type)

        # --- Distractor generation (LLM-first, heuristic fallback) ---
        code_lines = insecure_code.splitlines()
        distractors = _build_distractor_options(bundle, code_lines, vuln_lines)

        all_options = [{"lines": vuln_lines, "label": "", "correct": True}] + \
                      [{"lines": d["lines"], "label": "", "correct": False} for d in distractors]
        random.shuffle(all_options)
        shuffled_options = [{"lines": o["lines"], "label": o["label"]} for o in all_options]

        artifact = {
            **bundle,
            "options": shuffled_options,
            "verification": {
                "secure": secure_results,
                "insecure": insecure_results,
                "attempt": attempt,
                "bandit": bandit_result,
            },
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


@shared_task
def fill_review_queue_for_type(vuln_type, count=10):
    """Generate `count` challenges of a specific vulnerability type for the admin review queue."""
    logger.info("Review queue targeted fill: vuln_type=%s, count=%d", vuln_type, count)
    added = 0
    for _ in range(count):
        ch = _generate_and_save_challenge(vuln_type=vuln_type, is_pooled=False, status='pending_review')
        if ch:
            added += 1
    logger.info("Targeted fill complete. Added %d/%d %s challenges.", added, count, vuln_type)
    return added
