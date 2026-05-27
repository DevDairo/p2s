"""
Punto de entrada de la aplicación.
Flask lo usa automáticamente con FLASK_APP=app:create_app.
Este archivo existe para poder correr directamente con: python run.py
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
