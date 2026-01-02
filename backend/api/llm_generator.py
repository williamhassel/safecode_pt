# backend/api/llm_generator.py
import os
import json
from typing import Any, Dict, Optional
from openai import OpenAI

_client: Optional[OpenAI] = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Set it in your environment before running generation."
            )
        _client = OpenAI(api_key=api_key)
    return _client

# Minimal JSON Schema for what you need back from the LLM
CHALLENGE_SCHEMA: Dict[str, Any] = {
    "name": "generated_challenge_bundle",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "language": {"type": "string", "enum": ["python"]},
            "vuln_type": {"type": "string", "enum": ["sqli"]},
            "difficulty": {"type": "string", "enum": ["easy", "medium"]},

            "secure_code": {"type": "string", "minLength": 1},
            "insecure_code": {"type": "string", "minLength": 1},
            "tests": {"type": "string", "minLength": 1},

            "vulnerable_lines": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1
            },

            "explanation": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "short": {"type": "string"},
                    "fix": {"type": "string"}
                },
                "required": ["short", "fix"]
            }
        },
        "required": [
            "language", "vuln_type", "difficulty",
            "secure_code", "insecure_code", "tests",
            "vulnerable_lines", "explanation"
        ]
    },
    "strict": True
}

SYSTEM_PROMPT = """You generate secure coding training challenges.
Return ONLY data that matches the provided JSON schema.

Constraints:
- language: Python 3.11
- Use sqlite3.
- secure_code MUST use parameterized query with placeholders.
- insecure_code MUST be vulnerable to SQL injection by unsafe string construction.
- tests MUST:
  (1) pass against secure_code
  (2) fail against insecure_code
- The tests should be deterministic and self-contained (sqlite3 :memory:).
- vulnerable_lines should point to the vulnerable statement(s) in insecure_code.
- Keep code minimal and readable for students.
"""

def generate_bundle_sqli_easy(seed_topic: str = "users table lookup") -> Dict[str, Any]:
    user_prompt = f"Create an easy SQL injection challenge about: {seed_topic}"

    resp = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        # Structured Outputs in Responses API are set under text.format
        text={
            "format": {
                "type": "json_schema",
                "json_schema": CHALLENGE_SCHEMA
            }
        },
        # Keep generation stable
        temperature=0.2,
    )

    # Responses API exposes combined text via output_text; for structured outputs this will be JSON
    data = json.loads(resp.output_text)
    return data


def generate_bundle_sqli_easy(seed_topic: str = "users table lookup") -> Dict[str, Any]:
    client = get_client()

    resp = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-5.2"),
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Create an easy SQL injection challenge about: {seed_topic}"},
        ],
        text={"format": {"type": "json_schema", "json_schema": CHALLENGE_SCHEMA}},
        temperature=0.2,
    )

    return json.loads(resp.output_text)