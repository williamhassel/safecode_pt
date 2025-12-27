# safecode_pt
Prototype development for the master thesis

In order to run in browser \

cd safecode \

cd exports \

python -m http.server 8080 \

http://localhost:8080


/////

## Backend startup

In root:

venv\Scripts\activate.ps1    

python manage.py makemigrations

python manage.py migrate

python manage.py runserver

/////

## Message broker: Redis

In new terminal:
docker run -p 6379:6379 redis

/////

## Background worker: Celery

In new terminal:
celery -A backend worker -l info -P solo

/////

## Frontend startup

cd frontend

(First time only:)
npm install


npm start