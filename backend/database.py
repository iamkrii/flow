"""Database backend selector.

The implementation modules are deliberately separate:

* :mod:`database_sqlite` is the temporary local fallback and uses sqlite3.
* :mod:`database_oracle` is the production backend and uses
  Flask-SQLAlchemy with python-oracledb.

The rest of the application imports this small facade, so changing
``DB_MODE`` does not mix connection or ORM code between the two engines.
"""
from . import config


if config.DB_MODE == "oracle":
    from .database_oracle import *  # noqa: F401,F403
else:
    from .database_sqlite import *  # noqa: F401,F403
