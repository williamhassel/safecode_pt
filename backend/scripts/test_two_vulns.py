"""Quick test for XSS and SSRF"""
import os, sys
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, 'backend', '.env'))

import importlib.util
spec = importlib.util.spec_from_file_location("llm_generator", os.path.join(project_root, 'backend', 'api', 'llm_generator.py'))
llm_generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(llm_generator)

generate_challenge_bundle = llm_generator.generate_challenge_bundle

for vuln_type, seed in [("xss", "user comment display"), ("ssrf", "URL preview generator")]:
    print(f"\n{'='*60}\nTesting: {vuln_type.upper()}\n{'='*60}")
    try:
        bundle = generate_challenge_bundle(vuln_type, seed, "easy")
        s_lines = len(bundle["secure_code"].strip().splitlines())
        i_lines = len(bundle["insecure_code"].strip().splitlines())
        print(f"Secure: {s_lines} lines, Insecure: {i_lines} lines")
        if 20 <= s_lines <= 35 and 20 <= i_lines <= 35:
            print("[SUCCESS]")
        else:
            print(f"[FAIL] Length issue")
    except Exception as e:
        print(f"[FAIL] {str(e)[:200]}")
