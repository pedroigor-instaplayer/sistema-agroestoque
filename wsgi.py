"""Ponto de entrada WSGI para produção:  gunicorn wsgi:app"""
from agroestoque import create_app

app = create_app()
