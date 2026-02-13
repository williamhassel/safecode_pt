# backend/api/llm_generator.py
import os
import json
from typing import Any, Dict, Optional, Literal

# Support both OpenAI and Anthropic
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    Anthropic = None  # type: ignore

_openai_client: Optional["OpenAI"] = None  # type: ignore
_anthropic_client: Optional["Anthropic"] = None  # type: ignore

LLMProvider = Literal["openai", "anthropic"]

def get_provider() -> LLMProvider:
    """Determine which LLM provider to use based on environment variables."""
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if provider not in ["openai", "anthropic"]:
        raise RuntimeError(f"Invalid LLM_PROVIDER: {provider}. Must be 'openai' or 'anthropic'")
    return provider

def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI package not installed. Run: pip install openai")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def get_anthropic_client() -> Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError("Anthropic package not installed. Run: pip install anthropic")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        _anthropic_client = Anthropic(api_key=api_key)
    return _anthropic_client

# Minimal JSON Schema for what you need back from the LLM
CHALLENGE_SCHEMA: Dict[str, Any] = {
    "name": "generated_challenge_bundle",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "language": {"type": "string", "enum": ["python"]},
            "vuln_type": {"type": "string", "enum": [
                "sqli",           # SQL Injection
                "xss",            # Cross-Site Scripting
                "path_traversal", # Path Traversal / Directory Traversal
                "cmdi",           # Command Injection
                "xxe",            # XML External Entity
                "insecure_deser", # Insecure Deserialization
                "ssrf",           # Server-Side Request Forgery
                "weak_crypto",    # Weak Cryptographic Algorithm
                "hardcoded_creds",# Hard-coded Credentials
                "auth_bypass",    # Broken Authentication
            ]},
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

# Vulnerability-specific guidance
VULN_GUIDANCE = {
    "sqli": """
SQL INJECTION constraints:
- The function takes a database CONNECTION object and a user-provided search value as parameters
- secure_code MUST use parameterized queries: cursor.execute("SELECT ... WHERE col = ?", (value,))
- insecure_code MUST use f-string: cursor.execute(f"SELECT ... WHERE col = {value}")
- The function should NOT create tables or insert data - it only queries an existing database
- CRITICAL: Aim for exactly 25 lines per version. Do NOT exceed 30 lines.
- Include: module docstring (3 lines), import sqlite3 + typing, function with docstring, query logic, error handling
- The TEST must create the in-memory database, create table, insert rows, then call the function
- Test verifies: normal input returns data, SQL injection input like "1 OR 1=1" returns None (secure) vs all rows (insecure)
""",
    "xss": """
XSS (Cross-Site Scripting) constraints:
- Context: HTML generation function using ONLY built-in html module (NO Flask/Django)
- secure_code MUST use html.escape() on user input before inserting into HTML
- insecure_code MUST insert user input directly into HTML without escaping
- CRITICAL: Both versions must be IDENTICAL except for html.escape() calls
- BOTH versions MUST have ALL of these sections (copy-paste structure between versions):
  1. Module docstring (3 lines)
  2. import html / from typing import Optional (2 lines)
  3. Blank line (1 line)
  4. Function def with 3 parameters: title, content, author (1 line)
  5. Function docstring with Args/Returns (4 lines)
  6. Input validation for None/empty with defaults (2-3 lines)
  7. HTML string construction with 4 tags: div, h1, p, span (5-6 lines)
  8. Return statement (1 line)
- This gives 22-26 lines per version. BOTH versions must be 20-30 lines. Do NOT exceed 30.
- Test verifies '<script>alert(1)</script>' is escaped (secure) vs present as-is (insecure)
""",
    "path_traversal": """
PATH TRAVERSAL constraints:
- Context: File path validation function (VALIDATION ONLY - NO actual file I/O)
- secure_code MUST reject '..', use os.path.basename(), validate input
- insecure_code MUST accept user paths without directory traversal checks
- CRITICAL: Both versions must be IDENTICAL except for the security checks
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. import os / from typing import Optional (2 lines)
  3. Blank line, allowed extensions list (2 lines)
  4. Function def with base_dir parameter (1 line)
  5. Function docstring (4-5 lines)
  6. Null/empty check (2 lines)
  7. Security checks in secure / comments in insecure (3-4 lines)
  8. Path construction with os.path.join (2-3 lines)
  9. Return statement (1 line)
- This gives 22-25 lines per version. BOTH versions MUST be 20-30 lines. DO NOT open/read files.
- CRITICAL: Code under 20 lines will be REJECTED. Include ALL numbered sections above.
- Test verifies '../../etc/passwd' returns None (secure) vs path string (insecure, test fails)
""",
    "cmdi": """
COMMAND INJECTION constraints:
- Context: System command execution using subprocess module
- secure_code MUST use shell=False with list arguments: ['ls', '-l', user_input]
- insecure_code MUST use shell=True with string formatting: f"ls -l {user_input}"
- CRITICAL: Use ONLY built-in Unix commands: echo, ls, cat, pwd, date, whoami (NO ffmpeg, convert, imagemagick!)
- CRITICAL: Both versions must be IDENTICAL except for shell=True vs shell=False
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. import subprocess / import shlex / from typing import Optional (3 lines)
  3. Blank line (1 line)
  4. Function def taking command_input parameter (1 line)
  5. Function docstring with Args/Returns (4-5 lines)
  6. Input validation for None/empty (2 lines)
  7. Input sanitization with shlex in secure / comment in insecure (2 lines)
  8. Try block: subprocess.run call with shell=False (secure) or shell=True (insecure) (3-4 lines)
  9. Process and return result (2 lines)
  10. Except block with error handling (2-3 lines)
- This gives 24-28 lines per version. BOTH versions must be 20-30 lines.
- Tests MUST use unittest.mock.patch to mock subprocess.run - NEVER execute real commands
- Test must verify secure uses shell=False and insecure uses shell=True
""",
    "xxe": """
XXE (XML External Entity) constraints:
- Context: XML parsing with xml.etree.ElementTree (built-in)
- secure_code MUST disable external entities or reject DTD declarations
- insecure_code MUST use default parser without entity restrictions
- DO NOT use defusedxml (not installed) - use xml.etree.ElementTree ONLY
- CRITICAL: Both versions must be IDENTICAL except for the entity/DTD check
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. import xml.etree.ElementTree as ET / from typing import Optional, Dict (2 lines)
  3. Blank line (1 line)
  4. Function def taking xml_string parameter (1 line)
  5. Function docstring with Args/Returns (4-5 lines)
  6. Input validation for None/empty (2 lines)
  7. DTD/entity check in secure / comment placeholder in insecure (3-4 lines)
  8. Try block: parse XML with ET.fromstring (2 lines)
  9. Extract 2-3 fields from parsed tree using findtext (3-4 lines)
  10. Build result dict (2 lines)
  11. Return result dict (1 line)
  12. Except block with error handling (2-3 lines)
- This gives 24-30 lines per version. BOTH versions must be 20-30 lines.
- Test provides XML with <!ENTITY> or <!DOCTYPE>, verifies secure blocks it
""",
    "insecure_deser": """
INSECURE DESERIALIZATION constraints:
- Context: Data deserialization function
- secure_code MUST use json.loads() for safe deserialization
- insecure_code MUST use pickle.loads() on untrusted data (vulnerable)
- CRITICAL: Both versions must be IDENTICAL except for json vs pickle usage
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. imports: json/pickle, base64, from typing import Optional, Dict (2 lines)
  3. Blank line (1 line)
  4. Function def taking data_string parameter (1 line)
  5. Function docstring with Args/Returns (4-5 lines)
  6. Input validation for None/empty (2 lines)
  7. Try block: decode base64 (2 lines)
  8. Deserialize: json.loads in secure / pickle.loads in insecure (1-2 lines)
  9. Validate result type is dict (2 lines)
  10. Return result (1 line)
  11. Except block with error handling (2-3 lines)
- This gives 22-27 lines per version. CRITICAL: Do NOT exceed 30 lines.
- Test provides base64-encoded JSON data and verifies both can parse it
- Test also provides pickle-specific data that only insecure version processes unsafely
""",
    "ssrf": """
SSRF (Server-Side Request Forgery) constraints:
- Context: URL validation function (validation only, DO NOT make actual HTTP requests)
- secure_code MUST validate URLs and block internal/private IPs
- insecure_code MUST accept any URL without checking the IP
- CRITICAL: Both versions must have IDENTICAL structure. The ONLY difference is:
  secure has an if-block checking IP against blocked prefixes, insecure has a comment instead
- Keep it SIMPLE. Do NOT use socket.gethostbyname. Just check the hostname string directly.
- BOTH versions MUST follow this EXACT structure (aim for 24 lines each):
  1. Module docstring (3 lines)
  2. from urllib.parse import urlparse / from typing import Optional (2 lines)
  3. Blank line (1 line)
  4. Function def taking url parameter (1 line)
  5. Function docstring (3 lines)
  6. Input validation for None/empty (2 lines)
  7. parsed = urlparse(url), check scheme (3 lines)
  8. hostname = parsed.hostname (1 line)
  9. IP check: secure checks hostname against ("127.0.0.1","localhost","10.","192.168.") / insecure has comment (3 lines)
  10. Return url (1 line)
- CRITICAL: Do NOT exceed 30 lines. Aim for exactly 24 lines. Keep docstrings SHORT (1-line).
- Use ONLY urllib.parse (no socket, no requests)
- Test verifies http://127.0.0.1/admin returns None (secure) vs URL string (insecure, test fails)
""",
    "weak_crypto": """
WEAK CRYPTOGRAPHY constraints:
- Context: Password hashing function
- secure_code MUST use hashlib.sha256 WITH salt (using secrets module)
- insecure_code MUST use hashlib.md5 WITHOUT salt
- DO NOT use bcrypt/scrypt (not installed) - use built-in hashlib and secrets modules
- CRITICAL: Both versions must be IDENTICAL except for the hash algorithm and salt
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. import hashlib / import secrets / from typing import Tuple (2 lines)
  3. Blank line (1 line)
  4. Function def taking password parameter (1 line)
  5. Function docstring with Args/Returns explaining it returns (hash, salt) tuple (4-5 lines)
  6. Input validation for None/empty (2 lines)
  7. Generate salt in secure / empty salt in insecure (2 lines)
  8. Hash computation: sha256 with salt (secure) / md5 without salt (insecure) (2-3 lines)
  9. Return (hash_hex, salt) tuple (1 line)
- This gives 20-25 lines per version. BOTH versions must be 20-30 lines.
- Test verifies: secure returns non-empty salt, insecure returns empty salt
- Test also checks that same password produces different hashes with secure (due to random salt)
""",
    "hardcoded_creds": """
HARDCODED CREDENTIALS constraints:
- Context: Configuration/connection setup function
- secure_code MUST use os.environ.get() to read credentials from environment variables
- insecure_code MUST have hardcoded credential strings directly in source code
- CRITICAL: Both versions must be IDENTICAL except for how credentials are obtained
- BOTH versions MUST have ALL of these sections (copy-paste structure):
  1. Module docstring (3 lines)
  2. import os / from typing import Dict (2 lines)
  3. Blank line (1 line)
  4. APP_NAME constant string (1 line)
  5. Blank line (1 line)
  6. Function def get_db_config taking no parameters (1 line)
  7. Function docstring with Returns (4 lines)
  8. Get username: os.environ.get("DB_USERNAME", "guest") in secure / "admin" in insecure (1 line)
  9. Get password: os.environ.get("DB_PASSWORD", "") in secure / "secret123" in insecure (1 line)
  10. Get host: os.environ.get("DB_HOST", "localhost") in both (1 line)
  11. Build config dict with username/password/host/app_name (3 lines)
  12. Return config (1 line)
- This gives 22-26 lines per version. CRITICAL: Do NOT exceed 28 lines. Do NOT raise ValueError.
- CRITICAL TEST REQUIREMENT: The test MUST set environment variables BEFORE calling the secure function:
  os.environ["DB_USERNAME"] = "env_user"
  os.environ["DB_PASSWORD"] = "env_pass"
  config = get_db_config()
  assert config["username"] == "env_user"   # secure: reads from env
  assert config["password"] == "env_pass"   # secure: reads from env
  # insecure test: config["username"] == "admin" (hardcoded literal)
- Use os.environ.get() with defaults (empty string or "guest") - NOT raise ValueError
""",
    "auth_bypass": """
AUTHENTICATION BYPASS constraints:
- Context: Login/authentication validation function
- secure_code MUST validate BOTH username AND password (use 'and' logic)
- insecure_code MUST have logic flaw: use 'or' instead of 'and'
- CRITICAL: Both versions must be IDENTICAL except for 'and' vs 'or' in the check
- BOTH versions MUST follow this EXACT structure (aim for 24 lines each):
  1. Module docstring (3 lines)
  2. import hashlib / from typing import Optional, Dict (2 lines)
  3. Blank line + USER_DB = one-line dict with 2 users (2 lines)
  4. Blank line (1 line)
  5. Function def taking username, password (1 line)
  6. Function docstring (3 lines)
  7. Input validation for None/empty (2 lines)
  8. Hash password, lookup user in USER_DB (2 lines)
  9. Check credentials: 'and' (secure) vs 'or' (insecure) (2-3 lines)
  10. Return result (1 line)
- CRITICAL: Aim for exactly 24 lines. Maximum 30 lines. Keep USER_DB on ONE line.
- Test verifies wrong password returns None (secure) but returns user (insecure, test fails)
""",
}

BASE_SYSTEM_PROMPT = """You generate secure coding training challenges for OWASP vulnerabilities.
Return ONLY data that matches the provided JSON schema.

UNIVERSAL Constraints:
- language: Python 3.11
- tests MUST:
  (1) ALL tests pass when run against secure_code (pytest returns 0)
  (2) AT LEAST ONE test fails when run against insecure_code (pytest returns non-zero)
  (3) import from 'snippet' module (e.g., 'from snippet import function_name')
- The tests should be deterministic and self-contained
- vulnerable_lines should point to the vulnerable statement(s) in insecure_code
- CRITICAL: Both secure_code and insecure_code must define the EXACT SAME function name

=== CRITICAL CODE LENGTH REQUIREMENT - READ CAREFULLY ===
CODE MUST BE EXACTLY 20-35 LINES. This is MANDATORY and AUTOMATICALLY VERIFIED.
- Code under 20 lines will be AUTOMATICALLY REJECTED by the system
- Code over 35 lines will be AUTOMATICALLY REJECTED by the system
- BOTH secure_code AND insecure_code must be 20-35 lines - count before responding!
- CRITICAL: Make both versions SAME LENGTH (within 1-2 lines) - they should have identical structure
- The ONLY difference between versions should be the security fix itself
- Use empty lines, multi-line docstrings, helper functions, and detailed logic to reach 20 lines in BOTH versions

HOW TO REACH 20+ LINES (REQUIRED):
1. Add module-level docstring (3-4 lines)
2. Import statements (2-3 lines): import os, import sys, from datetime import datetime, etc.
3. Helper functions or constants (3-5 lines)
4. Main function with docstring (2-3 lines for docstring)
5. Function parameters with defaults (spread across multiple lines if needed)
6. Input validation logic (2-3 lines)
7. Core functionality (5-8 lines)
8. Error handling or logging (2-3 lines)
9. Return statement with formatting (1-2 lines)

EXAMPLE STRUCTURE (24 lines total):
Line 1: Module docstring start
Line 2: Docstring content
Line 3: Docstring end
Line 4: Empty line
Line 5: import sqlite3
Line 6: from typing import Optional
Line 7: Empty line
Line 8: def get_user_by_id(user_id: int, db_path: str = "users.db"):
Line 9:     Function docstring
Line 10-15: More docstring (Args, Returns, etc)
Line 16:     Input validation
Line 17:     Create connection
Line 18:     Execute query
Line 19:     Fetch result
Line 20:     Close connection
Line 21:     return result
Lines 22-24: Additional logic, error handling, etc.

- IMPORTANT: Test code will run against code saved as 'snippet.py', so use 'from snippet import ...'

VARIETY REQUIREMENTS:
- Create DIVERSE scenarios - vary function names, variable names, contexts
- Use creative, realistic application scenarios that fit the vulnerability type
- Vary what functions return (values, None, exceptions, etc.)
- Make challenges educational and representative of real vulnerabilities

CRITICAL TEST REQUIREMENTS:
- Write EXACTLY ONE test function (not separate test_secure and test_insecure)
- The SAME test will run against BOTH secure_code and insecure_code
- Test should assert SECURE behavior (what should happen)
- Secure code passes the test, insecure code FAILS the test

Example test pattern:
```python
def test_security_check():
    # Normal operation should work
    assert function('safe_input') == expected_result

    # Malicious input should be handled securely
    # Secure: returns None/raises exception/blocks attack
    # Insecure: allows attack, returns data, executes code
    assert function('malicious_input') is None  # or appropriate secure behavior
```
"""

def generate_with_openai(vuln_type: str, seed_topic: str, difficulty: str = "easy") -> Dict[str, Any]:
    """Generate challenge using OpenAI API."""
    client = get_openai_client()

    # Build the system prompt
    system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + VULN_GUIDANCE.get(vuln_type, "")
    user_prompt = f"Create a {difficulty} {vuln_type} challenge about: {seed_topic}"

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-2024-08-06"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": CHALLENGE_SCHEMA
        },
        temperature=0.7,
    )

    content = resp.choices[0].message.content
    return json.loads(content)

def generate_with_anthropic(vuln_type: str, seed_topic: str, difficulty: str = "easy") -> Dict[str, Any]:
    """Generate challenge using Anthropic Claude API."""
    client = get_anthropic_client()

    # Build the system prompt with vulnerability-specific guidance
    system_prompt = BASE_SYSTEM_PROMPT + "\n\n" + VULN_GUIDANCE.get(vuln_type, "")
    user_prompt = f"Create a {difficulty} {vuln_type} challenge about: {seed_topic}"

    # Claude doesn't support structured outputs yet, so we use a detailed prompt
    full_prompt = f"""{system_prompt}

User request: {user_prompt}

You MUST respond with valid JSON matching this exact schema:
{{
  "language": "python",
  "vuln_type": "{vuln_type}",
  "difficulty": "{difficulty}",
  "secure_code": "complete Python code implementing the secure version",
  "insecure_code": "complete Python code with the vulnerability",
  "tests": "complete Python test code that imports from 'snippet' module",
  "vulnerable_lines": [array of line numbers in insecure_code],
  "explanation": {{
    "short": "brief description of the vulnerability",
    "fix": "how to fix it"
  }}
}}

CRITICAL: The test code MUST import from 'snippet' module, like:
from snippet import function_name

NOT from 'secure_code' or 'insecure_code' - those modules don't exist!

Respond ONLY with the JSON, no other text."""

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=4096,
        temperature=0.8,  # Higher temperature for more variety
        messages=[
            {"role": "user", "content": full_prompt}
        ]
    )

    # Extract JSON from response
    content = response.content[0].text

    # Claude might wrap JSON in markdown, so let's extract it
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    # Fix Claude's malformed JSON
    import re

    # Claude is producing Python-style strings instead of JSON
    # Strategy: Extract each code field and manually build proper JSON

    try:
        # Try parsing as-is first
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # If that fails, manually extract fields using regex
    def extract_field(field_name, text):
        # Match: "field_name": "value" or "field_name": """value"""
        # Handle multi-line strings with various quote styles
        patterns = [
            rf'"{field_name}":\s*"""(.*?)"""',  # Triple quotes
            rf'"{field_name}":\s*"(.*?)"(?=\s*[,}}])',  # Regular quotes, non-greedy
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                value = match.group(1)
                # Unescape Python-style escapes and re-escape for JSON
                value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
                return value
        return None

    # Extract all fields
    language = extract_field("language", content) or "python"
    vuln_type = extract_field("vuln_type", content) or "sqli"
    difficulty = extract_field("difficulty", content) or "easy"
    secure_code = extract_field("secure_code", content)
    insecure_code = extract_field("insecure_code", content)
    tests = extract_field("tests", content)

    # Extract vulnerable_lines array
    vuln_lines_match = re.search(r'"vulnerable_lines":\s*\[(.*?)\]', content, re.DOTALL)
    vulnerable_lines = []
    if vuln_lines_match:
        lines_str = vuln_lines_match.group(1)
        vulnerable_lines = [int(x.strip()) for x in lines_str.split(',') if x.strip().isdigit()]

    # Extract explanation object
    short_exp = extract_field("short", content) or "SQL injection vulnerability"
    fix_exp = extract_field("fix", content) or "Use parameterized queries"

    if not all([secure_code, insecure_code, tests]):
        raise ValueError(f"Could not extract required fields from Claude's response. Content: {content[:500]}")

    # Build proper JSON structure
    return {
        "language": language,
        "vuln_type": vuln_type,
        "difficulty": difficulty,
        "secure_code": secure_code,
        "insecure_code": insecure_code,
        "tests": tests,
        "vulnerable_lines": vulnerable_lines if vulnerable_lines else [1],
        "explanation": {
            "short": short_exp,
            "fix": fix_exp
        }
    }

def generate_challenge_bundle(vuln_type: str, seed_topic: str, difficulty: str = "easy") -> Dict[str, Any]:
    """Generate a challenge bundle for any vulnerability type using the configured LLM provider.

    Args:
        vuln_type: The vulnerability type (sqli, xss, path_traversal, cmdi, etc.)
        seed_topic: The application context/scenario for the challenge
        difficulty: Challenge difficulty level (easy, medium)

    Returns:
        Dictionary containing secure_code, insecure_code, tests, and metadata
    """
    provider = get_provider()

    if provider == "openai":
        return generate_with_openai(vuln_type, seed_topic, difficulty)
    elif provider == "anthropic":
        return generate_with_anthropic(vuln_type, seed_topic, difficulty)
    else:
        raise RuntimeError(f"Unsupported provider: {provider}")

# Legacy function for backward compatibility
def generate_bundle_sqli_easy(seed_topic: str = "users table lookup") -> Dict[str, Any]:
    """DEPRECATED: Use generate_challenge_bundle instead."""
    return generate_challenge_bundle("sqli", seed_topic, "easy")
