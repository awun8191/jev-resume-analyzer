"""Vercel entrypoint. The app lives in app/main.py; Vercel loads `app` from here."""

from app.main import app

__all__ = ["app"]
