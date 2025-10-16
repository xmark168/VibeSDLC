"""
Models package.
Import all models here to ensure they are registered with SQLAlchemy.
"""

from app.models.user import User

__all__ = ["User"]
