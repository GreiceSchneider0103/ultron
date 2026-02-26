"""Legacy compatibility models module.

The project no longer keeps SQLAlchemy models in `api.src.db.models`.
Use Pydantic contracts from `api.src.types.listing` instead.
"""

from api.src.types.listing import *  # noqa: F401,F403
