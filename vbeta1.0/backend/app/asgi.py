"""Explicit ASGI entrypoint for the autonomous application.

Importing :mod:`app.main` exposes only the factory and therefore never opens
or recovers the operational database. A server creates the real application by
importing this module.
"""

from .main import create_app


app = create_app()
