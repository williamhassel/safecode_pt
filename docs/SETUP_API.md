# API Setup Guide

## Setting up Claude (Anthropic) API

### Step 1: Edit the .env file

Open the file: `backend\.env`

Replace `your_api_key_here` with your actual Anthropic API key:

```env
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

### Step 2: Restart your servers

After updating the `.env` file, you need to restart both Django and Celery:

1. **Stop Django server** (if running): Press `Ctrl+C` in the Django terminal
2. **Stop Celery worker** (if running): Press `Ctrl+C` in the Celery terminal

3. **Restart Django**:
   ```bash
   python manage.py runserver
   ```

4. **Restart Celery**:
   ```bash
   celery -A backend worker --loglevel=info --pool=solo
   ```

### Step 3: Test challenge generation

1. Go to your game page in the browser: `http://localhost:3000/game`
2. Click the "Generate New Challenge" button
3. Wait 10-30 seconds for Claude to generate the challenge
4. The new challenge should appear automatically!

## Switching between OpenAI and Claude

To switch back to OpenAI (if you add credits later), edit `backend\.env`:

```env
# Change this line:
LLM_PROVIDER=openai

# And add your OpenAI key:
OPENAI_API_KEY=sk-your-openai-key-here
```

Then restart Django and Celery servers.

## Troubleshooting

### "ANTHROPIC_API_KEY is not set" error
- Make sure you saved the `.env` file after editing
- Restart both Django and Celery servers
- Check that the key doesn't have quotes around it

### Challenge generation fails
- Check Celery logs for detailed error messages
- Verify your API key is valid at https://console.anthropic.com/
- Make sure you have credits remaining in your account

### Environment variables not loading
- Make sure the `.env` file is in the `backend/` directory
- Check that `python-dotenv` is installed: `pip list | findstr dotenv`
- Verify the settings.py file has the dotenv import
