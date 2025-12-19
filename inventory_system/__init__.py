"""Simple SQLite-backed uniform inventory system for security teams.

Includes both CLI helpers and a Flask-powered web UI for daily issuance
and returns tracking.
"""

__version__ = "0.1.0"

__all__ = ["cli", "db", "operations", "web", "__version__"]
