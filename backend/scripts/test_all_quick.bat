@echo off
echo Testing all 10 OWASP vulnerability types
echo ==========================================

call venv\Scripts\activate.bat

echo.
echo [1/10] Testing SQL Injection...
python test_single_vuln.py sqli 2

echo.
echo [2/10] Testing XSS...
python test_single_vuln.py xss 2

echo.
echo [3/10] Testing Path Traversal...
python test_single_vuln.py path_traversal 2

echo.
echo [4/10] Testing Command Injection...
python test_single_vuln.py cmdi 2

echo.
echo [5/10] Testing XXE...
python test_single_vuln.py xxe 2

echo.
echo [6/10] Testing Insecure Deserialization...
python test_single_vuln.py insecure_deser 2

echo.
echo [7/10] Testing SSRF...
python test_single_vuln.py ssrf 2

echo.
echo [8/10] Testing Weak Crypto...
python test_single_vuln.py weak_crypto 2

echo.
echo [9/10] Testing Hardcoded Credentials...
python test_single_vuln.py hardcoded_creds 2

echo.
echo [10/10] Testing Authentication Bypass...
python test_single_vuln.py auth_bypass 2

echo.
echo ==========================================
echo Testing complete! Check test_output_*.json files for results
pause
