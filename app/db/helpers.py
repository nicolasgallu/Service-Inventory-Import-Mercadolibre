from sqlalchemy import text
from app.db.engine import engine


def get_all(query, params=None):
    """Run a SELECT and return every row as a list of dicts."""
    with engine.begin() as conn:
        result = conn.execute(text(query), params or {})
        return [dict(row) for row in result.mappings()]


def get_one(query, params=None):
    """Run a SELECT and return a single row as a dict.

    Raises LookupError when the query returns no rows.
    """
    rows = get_all(query, params)
    if not rows:
        raise LookupError("Query returned no rows: " + query)
    return rows[0]


def execute(sql, params=None):
    """Run INSERT/UPDATE/DELETE and return the number of affected rows."""
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.rowcount