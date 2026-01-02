# backend/app/tasks.py
from celery import shared_task
from django.db import transaction
from .models import GenerationRequest, GeneratedChallenge
from .docker_runner import run_in_container
from .llm_generator import generate_bundle_sqli_easy

MAX_LLM_ATTEMPTS = 3

@shared_task
def generate_challenge(generation_id: int):
    gr = GenerationRequest.objects.get(id=generation_id)
    gr.status = "running"
    gr.save(update_fields=["status"])

    try:
        last_err = None

        for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
            bundle = generate_bundle_sqli_easy(seed_topic="username lookup")

            secure_code = bundle["secure_code"]
            insecure_code = bundle["insecure_code"]
            tests = bundle["tests"]
            vuln_lines = bundle["vulnerable_lines"]

            secure_results = run_in_container({"code": secure_code, "tests": tests})
            insecure_results = run_in_container({"code": insecure_code, "tests": tests})

            secure_ok = bool(secure_results.get("ok", False))
            insecure_ok = bool(insecure_results.get("ok", False))

            # Your acceptance criteria:
            # secure must pass, insecure must fail
            if secure_ok and (not insecure_ok):
                artifact = {
                    **bundle,
                    "options": [
                        {"lines": vuln_lines, "label": "Unsafe query construction allows SQL injection."},
                        {"lines": [max(1, vuln_lines[0] - 1)], "label": "Input-handling line (distractor)."},
                        {"lines": [min(len(insecure_code.splitlines()), vuln_lines[0] + 1)], "label": "Return/flow line (distractor)."},
                        {"lines": [1], "label": "Import line (distractor)."},
                    ],
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
                "secure_ok": secure_ok,
                "insecure_ok": insecure_ok,
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
