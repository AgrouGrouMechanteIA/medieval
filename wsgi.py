from app import create_app
app = create_app()
# Gunicorn common name is "app" or "application"; PythonAnywhere uses "application"
application = app
