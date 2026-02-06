# Quick Start: Testing All 10 OWASP Vulnerability Types

This guide will help you quickly test all vulnerability types before your supervisor meeting.

---

## Prerequisites

Make sure your development environment is running:

```bash
# Terminal 1: Django
venv\Scripts\activate.ps1
python manage.py runserver

# Terminal 2: Redis
docker run -p 6379:6379 redis

# Terminal 3: Celery
venv\Scripts\activate.ps1
celery -A backend worker -l info -P solo
```

---

## Option 1: Quick Test (Recommended for Meeting Prep)

Test 2-3 specific vulnerability types to confirm the system works:

```bash
# Activate virtual environment
venv\Scripts\activate.ps1

# Test SQL Injection (should work)
python test_all_vulnerabilities.py --vuln-type sqli --attempts 2

# Test XSS (should work)
python test_all_vulnerabilities.py --vuln-type xss --attempts 2

# Test one new type (e.g., Path Traversal)
python test_all_vulnerabilities.py --vuln-type path_traversal --attempts 3
```

**Time Required:** ~5-10 minutes per type (10-30 minutes total)

---

## Option 2: Full Test Suite

Test all 10 vulnerability types systematically:

```bash
# Activate virtual environment
venv\Scripts\activate.ps1

# Run full test suite (default: 3 attempts per type)
python test_all_vulnerabilities.py
```

**Time Required:** ~30-90 minutes (depends on LLM response time and success rates)

**Output:** Results saved to `vulnerability_test_results.json`

---

## Option 3: Conservative Approach (Overnight)

Run with more attempts to get accurate success rates:

```bash
python test_all_vulnerabilities.py --attempts 5 --output overnight_results.json
```

**Time Required:** 1-3 hours

---

## Understanding the Output

### Terminal Output
```
================================================================================
Testing: SQLI
Seed topic: user authentication lookup
================================================================================

[Attempt 1/3]
  → Generating challenge bundle...
  ✓ Generated in 12.34s
  → Code length: secure=24 lines, insecure=24 lines
  ✓ Code length valid
  → Running tests on secure code...
  ✓ Secure code tests passed
  → Running tests on insecure code...
  ✓ Insecure code tests failed (as expected)

✓ SUCCESS: sqli challenge validated successfully!
```

### JSON Output Format
```json
{
  "timestamp": "2026-02-05T20:30:00",
  "total_tested": 10,
  "successful": 7,
  "failed": 3,
  "results": [
    {
      "vuln_type": "sqli",
      "success": true,
      "attempts": 1,
      "errors": [],
      "secure_line_count": 24,
      "insecure_line_count": 24,
      "secure_tests_passed": true,
      "insecure_tests_failed": true,
      "generation_time": 12.34
    }
  ]
}
```

---

## Common Issues & Solutions

### Issue: "ANTHROPIC_API_KEY is not set"
**Solution:** Check that `backend/.env` has your API key:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_PROVIDER=anthropic
```

### Issue: "Docker is not running"
**Solution:** Start Docker Desktop and ensure the daemon is running.

### Issue: "Code too short" errors
**Solution:** This is expected for some vulnerability types. The script will retry automatically. If it fails after 3 attempts, that type needs prompt refinement.

### Issue: "Tests pass on both secure and insecure"
**Solution:** The LLM didn't generate properly discriminating tests. This indicates the vulnerability type needs better prompt guidance.

### Issue: Redis connection refused
**Solution:** Make sure Redis is running in a separate terminal:
```bash
docker run -p 6379:6379 redis
```

---

## What to Report to Your Supervisor

After running tests, you can report:

1. **Number of working types:**
   - "X out of 10 vulnerability types are generating valid challenges"

2. **Success rates:**
   - "SQL Injection and XSS work on first attempt (100% success)"
   - "Path Traversal works after 2-3 attempts (60% success)"
   - "Command Injection needs prompt refinement (0% success)"

3. **Common failure modes:**
   - Code length violations
   - Test discrimination issues
   - Dependency problems

4. **Action plan:**
   - "Focus on 6-7 high-success types for user study"
   - "Refine prompts for medium-success types in Week 2"
   - "Defer low-success types or document as limitations"

---

## Quick Sanity Check (5 minutes)

If you're short on time before the meeting, just verify the system works:

```bash
# Test one known-working type
python test_all_vulnerabilities.py --vuln-type sqli --attempts 1

# Check if output file was created
ls -la vulnerability_test_results.json
```

If this works, you can confidently say:
- ✅ Testing infrastructure is operational
- ✅ At least one vulnerability type works
- ✅ Ready to test remaining types in Week 2

---

## Files Created Today

1. **[test_all_vulnerabilities.py](test_all_vulnerabilities.py)** - Automated testing script
2. **[VULNERABILITY_CHALLENGES.md](VULNERABILITY_CHALLENGES.md)** - Detailed analysis of each type
3. **[SUPERVISOR_MEETING_REPORT.md](SUPERVISOR_MEETING_REPORT.md)** - Meeting preparation document
4. **[QUICK_START_TESTING.md](QUICK_START_TESTING.md)** - This file
5. **Updated [CLAUDE.md](CLAUDE.md)** - Added testing documentation
6. **Updated [backend/api/tasks.py](backend/api/tasks.py)** - Enabled all 10 types

---

## Next Steps After Testing

1. Review `vulnerability_test_results.json`
2. Update `thesis_timeline_updated.md` with actual results
3. Prepare talking points for supervisor meeting
4. Plan Week 2 prompt refinement based on failures

Good luck with your testing and supervisor meeting! 🚀
