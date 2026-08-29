import json
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app.db.helpers import execute, get_one
from app.settings.config import SCHEMA_ACCOUNTS


EVENTS_TABLE = SCHEMA_ACCOUNTS + ".events"

MAX_ATTEMPTS = 10
RECLAIM_AFTER_SECONDS = 900


def claim(account_id, source, event_type, external_id, payload=None):
    """Try to become the worker in charge of this event.

    Returns the event id when we win, or None when someone else is already
    processing it.
    """
    _insert_pending(account_id, source, event_type, external_id, payload)
    return _try_claim(account_id, source, event_type, external_id)


def finish(event_id):
    _set_status(event_id, "done")


def fail(event_id):
    _set_status(event_id, "failed")


def heartbeat(event_id):
    """Keep a long-running event alive so it is not stolen while working."""
    execute(
        "UPDATE " + EVENTS_TABLE + " SET updated_at = NOW() WHERE id = :id",
        {"id": event_id},
    )


def _insert_pending(account_id, source, event_type, external_id, payload):
    sql = (
        "INSERT INTO " + EVENTS_TABLE
        + " (ecommerce_account_id, source, event_type, external_id, payload, status)"
        + " VALUES (:account_id, :source, :event_type, :external_id, :payload, 'pending')"
    )
    try:
        execute(sql, {
            "account_id": account_id,
            "source": source,
            "event_type": event_type,
            "external_id": external_id,
            "payload": _to_json(payload),
        })
    except IntegrityError:
        # The row already exists (duplicate delivery). Fine, the claim below
        # decides who owns it.
        pass


def _try_claim(account_id, source, event_type, external_id):
    stale_before = datetime.now() - timedelta(seconds=RECLAIM_AFTER_SECONDS)
    sql = (
        "UPDATE " + EVENTS_TABLE
        + " SET status = 'processing', updated_at = NOW(), attempts = attempts + 1"
        + " WHERE ecommerce_account_id = :account_id"
        + " AND source = :source"
        + " AND event_type = :event_type"
        + " AND external_id = :external_id"
        + " AND ("
        + "     status = 'pending'"
        + "     OR (status = 'processing' AND updated_at < :stale_before)"
        + "     OR (status = 'failed' AND attempts < :max_attempts)"
        + " )"
    )
    rowcount = execute(sql, {
        "account_id": account_id,
        "source": source,
        "event_type": event_type,
        "external_id": external_id,
        "stale_before": stale_before,
        "max_attempts": MAX_ATTEMPTS,
    })
    if rowcount == 1:
        return _event_id(account_id, source, event_type, external_id)
    return None


def _event_id(account_id, source, event_type, external_id):
    sql = (
        "SELECT id FROM " + EVENTS_TABLE
        + " WHERE ecommerce_account_id = :account_id"
        + " AND source = :source"
        + " AND event_type = :event_type"
        + " AND external_id = :external_id"
    )
    row = get_one(sql, {
        "account_id": account_id,
        "source": source,
        "event_type": event_type,
        "external_id": external_id,
    })
    return row["id"]


def _set_status(event_id, status):
    execute(
        "UPDATE " + EVENTS_TABLE
        + " SET status = :status, updated_at = NOW() WHERE id = :id",
        {"status": status, "id": event_id},
    )


def _to_json(payload):
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload
    return json.dumps(payload)