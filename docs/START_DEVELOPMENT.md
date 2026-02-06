# Starting SafeCode Development Environment

Follow these steps in order to start all required services:

## Step 1: Start Redis (Terminal 1)
```bash
docker run -p 6379:6379 redis
```
Leave this running.

## Step 2: Start Django Backend (Terminal 2)
```bash
# Navigate to project root
cd e:\_uni\11\safecode_pt

# Activate virtual environment
venv\Scripts\activate

# Run Django server
python manage.py runserver
```
Django will run on http://localhost:8000

## Step 3: Start Celery Worker (Terminal 3)
```bash
# Navigate to project root
cd e:\_uni\11\safecode_pt

# Activate virtual environment
venv\Scripts\activate

# Start Celery worker
celery -A backend worker --loglevel=info --pool=solo
```
Watch this terminal for challenge generation logs.

## Step 4: Start React Frontend (Terminal 4)
```bash
# Navigate to frontend
cd e:\_uni\11\safecode_pt\frontend

# Start React dev server
npm start
```
Frontend will run on http://localhost:3000

## Verify Everything is Running

1. Redis: Should show "Ready to accept connections"
2. Django: Should show "Starting development server at http://127.0.0.1:8000/"
3. Celery: Should show "celery@hostname ready"
4. React: Should open browser to http://localhost:3000

## Ready to Test!

Once all services are running, you can test challenge generation:
1. Go to http://localhost:3000/game
2. Click "Generate New Challenge"
3. Watch the Celery terminal for generation progress
4. Challenge should appear after 10-30 seconds
