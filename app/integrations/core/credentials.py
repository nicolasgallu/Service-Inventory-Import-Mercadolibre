from app.db.helpers import get_one
from app.settings.config import SCHEMA_ACCOUNTS

CREDENTIALS_TABLE = SCHEMA_ACCOUNTS + ".credentials"
ACCOUNTS_TABLE = SCHEMA_ACCOUNTS + ".accounts"


class UnknownAccount(Exception):
    """Raised when an user_id has no matching account."""

def get_account_owner(user_id, platform):
    """Return the account (as a dict) that owns this user_id on the given platform.

    Raises UnknownAccount when no account matches.
    """
    sql = (
        "SELECT * FROM " + ACCOUNTS_TABLE
        + " WHERE external_account_id = :user_id AND platform = :platform"
    )
    try:
        return get_one(sql, {"user_id": str(user_id), "platform": platform})
    except LookupError:
        raise UnknownAccount(f"No {platform} account for id " + str(user_id))



def get_access_token(account_id):
    """Read the account's current Meli token from the credentials table."""
    sql = (
        "SELECT access_token FROM " + CREDENTIALS_TABLE
        + " WHERE account_id = :account_id"
    )
    row = get_one(sql, {"account_id": account_id})
    return row