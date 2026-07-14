"""Loja e-commerce API — responsibility-layered Flask application.

Public entry point is `create_app`, the composition root. Importing this package
does not open a database, seed data, or start a server.
"""
from .app_factory import create_app

__all__ = ["create_app"]
