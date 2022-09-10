source ./venv/Scripts/activate
echo ' ⚡ Activated virtual environment'
export FLASK_DEBUG=1
export FLASK_ENV=development
export FLASK_APP=app.py

flask run --port 5000
