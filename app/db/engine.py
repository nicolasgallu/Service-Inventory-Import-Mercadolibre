from urllib.parse import quote_plus
from sqlalchemy import create_engine
from app.settings.config import (
    INSTANCE_DB,
    NAME_DB,
    PASSWORD_DB,
    USER_DB,
)

_connector = None


def _get_connector():
    global _connector
    if _connector is None:
        from google.cloud.sql.connector import Connector
        _connector = Connector()
    return _connector


def _cloud_sql_connection():
    return _get_connector().connect(
        INSTANCE_DB,
        "pymysql",
        user=USER_DB,
        password=PASSWORD_DB,
        db=NAME_DB,
    )


def _build_engine():
    # Cloud SQL
    return create_engine(
        "mysql+pymysql://",
        creator=_cloud_sql_connection,
        pool_pre_ping=True,
        pool_size=8,
        max_overflow=4,
    )

engine = _build_engine()