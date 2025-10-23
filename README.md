# safecode_pt
Prototype development for the master thesis

In order to run in browser \

cd safecode \

cd exports \

python -m http.server 8080 \

http://localhost:8080


/////

Backend startup

venv\Scripts\activate    

python manage.py migrate

python manage.py makemigrations

python manage.py runserver


////

Frontend startup

cd frontend

npm start
