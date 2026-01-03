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
- Use sqlite3 for database operations with in-memory database (:memory:)
- secure_code MUST use parameterized queries (? or named placeholders)
- insecure_code MUST be vulnerable via: string formatting, dynamic query construction, LIKE injection, ORDER BY injection, etc.
- CRITICAL: Tests MUST set up the database schema and insert test data in a setup function or fixture
- Use pytest fixtures or setup code to create tables and populate test data
- Test should verify malicious input returns None/empty (secure) vs actual data (insecure)
- Example test pattern:
  ```python
  import sqlite3
  import pytest
  from snippet import get_user

  @pytest.fixture
  def setup_db():
      conn = sqlite3.connect(':memory:')
      c = conn.cursor()
      c.execute('CREATE TABLE users (id INTEGER, username TEXT, email TEXT)')
      c.execute('INSERT INTO users VALUES (1, "alice", "alice@example.com")')
      c.execute('INSERT INTO users VALUES (2, "bob", "bob@example.com")')
      conn.commit()
      conn.close()
      return ':memory:'

  def test_sqli(setup_db):
      # Normal query should work
      result = get_user(1)
      assert result is not None

      # SQL injection should be blocked (secure) or succeed (insecure)
      result = get_user("1 OR 1=1")
      assert result is None  # Secure blocks it, insecure allows it
  ```
- OR use in-memory shared database that both code and test can access
""",
    "xss": """
XSS (Cross-Site Scripting) constraints:
- Context: Simple HTML generation function (NO Flask/Django - not installed in container)
- secure_code MUST properly escape HTML output using ONLY Python's built-in html.escape()
- insecure_code MUST directly insert user input into HTML string without escaping
- Function should return HTML string, NOT render templates
- DO NOT import Flask, Django, or any web frameworks - use ONLY: import html
- CRITICAL: Both versions must define the SAME function name (e.g., 'render_comment')
- MANDATORY: Code MUST be 20-35 lines total. This is STRICTLY ENFORCED.
  * Include: imports (2-4 lines), docstrings (2-3 lines), function definition with multiple parameters
  * Add helper logic: timestamp formatting, default parameter handling, data validation
  * Include realistic HTML structure with multiple nested elements (header, body, footer, metadata)
  * Add CSS classes, data attributes, multiple user-provided fields
  * DO NOT create minimal functions - they will be REJECTED
- Test should verify malicious input like '<script>alert(1)</script>' is escaped (secure) vs rendered as-is (insecure)
- Example pattern:
  ```python
  # SECURE VERSION (secure_code):
  import html
  from datetime import datetime

  def render_user_comment(username, comment, timestamp=None):
      # Escape all user-provided content
      safe_username = html.escape(username)
      safe_comment = html.escape(comment)

      if timestamp is None:
          timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

      return f'''
      <div class="comment-container">
          <div class="comment-header">
              <span class="username">{safe_username}</span>
              <span class="timestamp">{timestamp}</span>
          </div>
          <div class="comment-body">
              <p>{safe_comment}</p>
          </div>
      </div>
      '''

  # INSECURE VERSION (insecure_code):
  from datetime import datetime

  def render_user_comment(username, comment, timestamp=None):
      # VULNERABLE: No escaping of user input!
      if timestamp is None:
          timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

      return f'''
      <div class="comment-container">
          <div class="comment-header">
              <span class="username">{username}</span>
              <span class="timestamp">{timestamp}</span>
          </div>
          <div class="comment-body">
              <p>{comment}</p>
          </div>
      </div>
      '''

  # TEST (imports the SAME function name from both versions):
  from snippet import render_user_comment

  def test_xss():
      # Normal input works
      result = render_user_comment('Alice', 'Hello world')
      assert 'Alice' in result
      assert 'Hello world' in result

      # Malicious input is escaped (secure) vs rendered (insecure)
      result = render_user_comment('Bob', '<script>alert(1)</script>')
      assert '<script>' not in result  # Passes on secure, fails on insecure
      assert '&lt;script&gt;' in result  # Passes on secure, fails on insecure
  ```
""",
    "path_traversal": """
PATH TRAVERSAL constraints:
- Context: File path validation (NOT actual file operations)
- secure_code MUST validate/sanitize paths (use os.path.basename(), check against whitelist, reject '..')
- insecure_code MUST accept paths with '../' sequences without validation
- Function should return a sanitized/validated path (str) or None if invalid
- DO NOT actually open/read files - just validate the path
- Test should verify:
  * Normal filename like 'document.txt' returns sanitized path (both versions)
  * Path with '../../../etc/passwd' returns None (secure) or the unsafe path (insecure)
- Example pattern:
  ```python
  def validate_file_path(filename):
      # Secure: reject paths with '..'
      if '..' in filename:
          return None
      return filename

  # Test
  def test_path_validation():
      assert validate_file_path('document.txt') == 'document.txt'
      assert validate_file_path('../../../etc/passwd') is None  # secure behavior
  ```
""",
    "cmdi": """
COMMAND INJECTION constraints:
- Context: Subprocess execution, shell commands, system calls
- secure_code MUST use shell=False with list arguments or input validation/escaping (using shlex.quote())
- insecure_code MUST pass unsanitized user input to shell commands with shell=True
- CRITICAL: Use ONLY built-in Unix commands that exist in containers: echo, ls, cat, pwd, date, whoami
- DO NOT use: ffmpeg, convert, imagemagick, or any external tools
- Test should use mock/patch to avoid actually executing commands
- Example test pattern:
  ```python
  from unittest.mock import patch, MagicMock

  @patch('subprocess.run')
  def test_command_injection(mock_run):
      mock_run.return_value = MagicMock(returncode=0, stdout='output')

      # Normal input should work
      result = function('safe.txt')
      assert result is not None

      # Malicious input with command injection attempt
      # Secure: should call with shell=False or sanitized input
      # Insecure: should call with shell=True and unsanitized input
      result = function('file; rm -rf /')

      # Check if shell=True was used (insecure behavior)
      calls = mock_run.call_args_list
      # Secure version: should use shell=False
      # Insecure version: should use shell=True (test will fail detecting this)
      assert all(not call.kwargs.get('shell', False) for call in calls)
  ```
""",
    "xxe": """
XXE (XML External Entity) constraints:
- Context: XML parsing
- secure_code MUST disable external entity processing (defusedxml or parser features)
- insecure_code MUST use unsafe XML parser that processes external entities
- Test should verify malicious XML with external entities is rejected (secure) vs processed (insecure)
""",
    "insecure_deser": """
INSECURE DESERIALIZATION constraints:
- Context: Pickle, YAML, or other deserialization
- secure_code MUST use safe alternatives (json.loads()) or validate before deserializing
- insecure_code MUST use pickle.loads() or yaml.load() on untrusted data
- Test should verify malicious payload fails to execute code (secure) vs executes (insecure)
""",
    "ssrf": """
SSRF (Server-Side Request Forgery) constraints:
- Context: Making HTTP requests based on user input
- secure_code MUST validate URLs against whitelist, block internal IPs
- insecure_code MUST directly use user-supplied URLs
- Test should verify requests to internal IPs like '127.0.0.1' are blocked (secure) vs allowed (insecure)
""",
    "weak_crypto": """
WEAK CRYPTOGRAPHY constraints:
- Context: Password hashing, encryption, token generation
- secure_code MUST use strong algorithms (bcrypt, scrypt, secrets module, Fernet)
- insecure_code MUST use weak algorithms (MD5, SHA1 for passwords, weak random)
- Test should verify strong crypto is used (secure) vs weak/predictable (insecure)
""",
    "hardcoded_creds": """
HARDCODED CREDENTIALS constraints:
- Context: Authentication, API keys, database connections
- secure_code MUST use environment variables or secure config management
- insecure_code MUST have credentials hardcoded in source
- Test should verify credentials aren't in source (secure) vs hardcoded (insecure)
""",
    "auth_bypass": """
AUTHENTICATION BYPASS constraints:
- Context: Login, session management, authorization checks
- secure_code MUST properly validate credentials and enforce authorization checks
- insecure_code MUST have flawed logic allowing bypass (e.g., always returns success, skips validation, weak checks)
- Test should verify that:
  * Normal valid credentials work for both versions
  * Invalid/malicious credentials are REJECTED (return None/False/raise exception) in secure version
  * Invalid/malicious credentials SUCCEED in insecure version (this causes the test to fail)
- Example: Test login('', '') should return None (secure) but return valid user (insecure, test fails)
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

=== CRITICAL CODE LENGTH REQUIREMENT - READ CAREFULLY ===
CODE MUST BE EXACTLY 20-35 LINES. This is MANDATORY and AUTOMATICALLY VERIFIED.
- Code under 20 lines will be AUTOMATICALLY REJECTED by the system
- Code over 35 lines will be AUTOMATICALLY REJECTED by the system
- Count your lines before responding - both secure_code and insecure_code must be 20-35 lines

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
