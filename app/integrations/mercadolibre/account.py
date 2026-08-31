from app.db.helpers import get_one
from app.settings.config import SCHEMA_ACCOUNTS

ACCOUNTS_TABLE = SCHEMA_ACCOUNTS + ".ecommerce_accounts"

class UnknownAccount(Exception):
    """Raised when a Meli user_id has no matching account."""

def resolve_account_by_meli_user(user_id):
    """Return the account (as a dict) that owns this MercadoLibre user_id.

    Raises UnknownAccount when no account matches.
    """
    sql = (
        "SELECT * FROM " + ACCOUNTS_TABLE
        + " WHERE external_account_id = :user_id"
        + " AND platform = 'mercadolibre'"
    )
    try:
        return get_one(sql, {"user_id": str(user_id)})
    except LookupError:
        raise UnknownAccount("No account for Meli user_id " + str(user_id))