# SafeCode: Master Thesis Project

## Project Overview
SafeCode is an educational web application for learning secure coding practices. It presents users with code challenges containing security vulnerabilities (OWASP Top 10), allowing them to identify and fix these issues. The system uses LLM-powered challenge generation to create diverse, realistic security scenarios.

**Thesis Context**: This is a master's thesis prototype exploring gamified secure coding education with AI-generated challenges.

## Architecture

### Tech Stack
- **Backend**: Django (Python 3.11), Django REST Framework
- **Frontend**: React (JavaScript)
- **Database**: SQLite (db.sqlite3)
- **Task Queue**: Celery with Redis broker
- **Container Runtime**: Docker (for code execution sandboxing)
- **LLM Providers**: Anthropic Claude API (primary), OpenAI (fallback)

### Directory Structure
```
safecode_pt/
├── backend/                # Django application
│   ├── api/               # Core API logic
│   │   ├── models.py     # Challenge, Result, Certificate, GeneratedChallenge
│   │   ├── views.py      # API endpoints
│   │   ├── tasks.py      # Celery async tasks
│   │   ├── llm_generator.py  # LLM challenge generation
│   │   └── docker_runner.py  # Sandboxed code execution
│   ├── settings.py        # Django configuration
│   └── .env              # API keys (git-ignored)
├── frontend/              # React application
│   └── src/
│       ├── pages/        # React pages
│       └── api/          # API client
├── challenge_runner/      # Code execution utilities
├── safecode/             # Additional exports/assets
└── db.sqlite3            # SQLite database
```

## Core Features

### 1. Challenge System
- **Static Challenges**: Predefined coding challenges stored in database
- **Generated Challenges**: AI-generated challenges using Claude/GPT-4
- Vulnerability types: SQL injection, XSS, path traversal, command injection, XXE, insecure deserialization, SSRF, weak crypto, hardcoded credentials, auth bypass
- Difficulty levels: Easy, Medium, Hard

### 2. Challenge Generation Pipeline
1. User requests new challenge via frontend
2. Request queued in `GenerationRequest` model
3. Celery task (`tasks.py`) calls LLM generator
4. `llm_generator.py` generates secure + insecure code + tests
5. Docker runner validates tests pass on secure code, fail on insecure code
6. Challenge stored in `GeneratedChallenge` model
7. Frontend polls for completion and displays challenge

### 3. Code Validation
- User submits solution via frontend
- Backend runs solution against test cases in Docker container
- Results stored in `Result` model with score and correctness
- Certificate generation when user reaches threshold (100+ challenges, 80%+ accuracy)

## Current State & Known Issues

### Working Features
- Challenge generation with Claude API (configured)
- Basic frontend game page
- User authentication system
- Static challenge storage and retrieval
- Certificate issuance logic

### Configuration
- **LLM Provider**: Currently using Anthropic (Claude 3.5 Sonnet)
- **API Key**: Stored in `backend/.env` as `ANTHROPIC_API_KEY`
- **Model**: `claude-3-5-sonnet-20241022`

### Recent Changes
- Switched from OpenAI to Anthropic due to credit issues
- Updated `.gitignore` to exclude `.env` files
- Removed cache files and database from version control
- Improved challenge generation prompts for better code quality

## Development Workflow

### Starting the Development Environment
```bash
# 1. Activate Python virtual environment
venv\Scripts\activate.ps1

# 2. Start Django server
python manage.py runserver

# 3. Start Redis (separate terminal)
docker run -p 6379:6379 redis

# 4. Start Celery worker (separate terminal)
celery -A backend worker -l info -P solo

# 5. Start React frontend (separate terminal)
cd frontend
npm start

# 6. (Optional) Start export server for browser files
cd safecode/exports
python -m http.server 8080
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Key Models

### Challenge
- Predefined challenges with title, description, difficulty
- Legacy system for static challenges

### GeneratedChallenge
- AI-generated challenges
- Fields: `language`, `vuln_type`, `difficulty`, `artifact` (JSON containing code/tests)
- Linked to `GenerationRequest` for status tracking

### GenerationRequest
- Tracks async challenge generation
- Status: queued → running → done/failed
- Stores logs and error messages

### Result
- User attempt records
- Links to either static `Challenge` or `GeneratedChallenge`
- Tracks score, correctness, timestamp

### Certificate
- Issued when user meets criteria (100+ questions, 80%+ accuracy)
- Contains verification code (UUID)
- Records accuracy and total questions at time of issue

## Important Code Patterns

### LLM Challenge Generation
- See [backend/api/llm_generator.py](backend/api/llm_generator.py)
- Supports multiple providers (OpenAI, Anthropic)
- Enforces strict code length requirements (20-35 lines)
- Uses vulnerability-specific guidance prompts
- Validates generated code meets security requirements

### Docker Sandboxing
- See [backend/api/docker_runner.py](backend/api/docker_runner.py)
- Executes untrusted code in isolated containers
- Runs pytest on both secure and insecure versions
- Validates that tests pass on secure code, fail on insecure code

## Thesis Research Questions (Context)
1. How can LLM-generated challenges provide diverse, realistic security scenarios?
2. What gamification elements improve learning outcomes in secure coding education?
3. How effective is immediate feedback (test-driven validation) for security learning?
4. Can certificate systems motivate sustained engagement?

## Design Principles
- **Realism**: Challenges should reflect real-world vulnerability patterns
- **Diversity**: Avoid repetitive challenges through varied contexts and scenarios
- **Incremental Learning**: Progress from easy to complex vulnerabilities
- **Immediate Feedback**: Test-driven validation provides instant correctness signals
- **Sandboxed Execution**: Never trust user-submitted or LLM-generated code

## Development Priorities & Next Steps

### Week 1 Status (Feb 5, 2026)
- [x] All 10 OWASP vulnerability types implemented in schema
- [x] All 10 vulnerability types enabled for testing
- [x] Created systematic testing script ([test_all_vulnerabilities.py](test_all_vulnerabilities.py))
- [x] Documented challenges for each vulnerability type ([VULNERABILITY_CHALLENGES.md](VULNERABILITY_CHALLENGES.md))
- [ ] Run comprehensive tests on all 10 vulnerability types
- [ ] Identify which types work reliably (target: 6-7 types)

### High Priority (Week 2)
- [ ] Test all 10 vulnerability types and document success rates
- [ ] Refine prompts for failing vulnerability types
- [ ] Set up logging infrastructure for user interaction tracking
- [ ] Improve frontend UX for generated challenges (loading states, error handling)
- [ ] Implement pre-generated challenge pool (eliminate user-facing latency)

### Medium Priority (Weeks 3-5)
- [ ] Add verification agent improvements
- [ ] Implement static analysis agent (Bandit integration)
- [ ] Add pedagogical review agent
- [ ] Enhance test validation (ensure tests are truly discriminating)
- [ ] Implement challenge difficulty progression system

### Low Priority / Research
- [ ] A/B test different gamification approaches
- [ ] Collect user interaction metrics for thesis analysis
- [ ] Compare learning outcomes: static vs generated challenges
- [ ] Add hints system for stuck users

## Testing Vulnerability Types

### Running the Test Suite
Test all 10 vulnerability types systematically:
```bash
# Test all vulnerability types
python test_all_vulnerabilities.py

# Test a specific vulnerability type
python test_all_vulnerabilities.py --vuln-type sqli

# Run with more attempts per type
python test_all_vulnerabilities.py --attempts 5

# Save results to custom file
python test_all_vulnerabilities.py --output my_results.json
```

### Understanding Test Results
The test script validates four key criteria for each vulnerability type:
1. LLM generates valid JSON matching the schema
2. Generated code meets length requirements (20-35 lines)
3. Tests pass on secure code (returncode 0)
4. Tests fail on insecure code (returncode ≠ 0)

Results are saved to JSON and include:
- Success/failure status
- Number of attempts needed
- Error messages
- Code line counts
- Test execution results

### Vulnerability Type Documentation
See [VULNERABILITY_CHALLENGES.md](VULNERABILITY_CHALLENGES.md) for detailed information about:
- Implementation patterns for each vulnerability
- Expected success rates
- Known challenges and issues
- Testing strategy and priorities

## Common Tasks & Commands

### Switching LLM Providers
Edit `backend/.env`:
```env
# Use Anthropic (current)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key

# Use OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
```
Then restart Django and Celery.

### Testing Challenge Generation
1. Navigate to `http://localhost:3000/game`
2. Click "Generate New Challenge"
3. Wait 10-30 seconds for LLM generation
4. Check Celery logs for detailed generation process

### Debugging Failed Generations
1. Check Celery terminal for error messages
2. Verify API key is valid and has credits
3. Check `GenerationRequest` model in Django admin for logs
4. Common issues:
   - Code length violations (must be 20-35 lines)
   - Tests don't discriminate between secure/insecure versions
   - Invalid JSON from LLM response

### Adding New Vulnerability Types
1. Add vulnerability to `vuln_type` enum in [llm_generator.py:62-74](backend/api/llm_generator.py#L62-L74)
2. Add guidance in `VULN_GUIDANCE` dict [llm_generator.py:107-322](backend/api/llm_generator.py#L107-L322)
3. Update schema if needed
4. Test generation with new type

## Security Considerations
- Never execute user code outside Docker containers
- API keys must stay in `.env` (git-ignored)
- Generated code is untrusted - always validate before execution
- Frontend should sanitize all user inputs
- Rate limit challenge generation to prevent API abuse

## Testing
- Use pytest for backend tests
- Docker must be running for integration tests
- Test both secure and insecure code variants
- Validate LLM outputs match schema

## Git Workflow
- Main branch: `master`
- Current branch: `master`
- Untracked files: SETUP_API.md (setup documentation)

## Resources
- Django docs: https://docs.djangoproject.com/
- React docs: https://react.dev/
- Anthropic API: https://docs.anthropic.com/
- OWASP Top 10: https://owasp.org/www-project-top-ten/

---

## Notes for Claude Code
- Always use the virtual environment (`venv`) for Python operations
- Remember to restart Django and Celery after changing backend code
- Frontend hot-reloads automatically (React dev server)
- Check both Django logs and Celery logs when debugging
- Database is SQLite - use Django ORM or `python manage.py dbshell`
- When adding features, consider thesis evaluation metrics
- Code quality matters - this is academic work that will be reviewed
