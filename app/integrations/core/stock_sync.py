from app.integrations.bitcram.client import BitcramError, post_sale_doc


class StockSyncError(Exception):
    """The provider definitively rejected the movement (safe to retry)."""


def post_stock_movement(provider_config, internal_code, quantity, unit_price):
    """Post one movement to the business's configured stock system.

    Returns the provider's doc id, or None when there is nothing to post
    (record-only). Raises StockSyncError on a definitive rejection; any
    other exception means the result is ambiguous (maybe committed).
    """
    provider_config = provider_config or {}
    provider = provider_config.get("provider", "none")
    config = provider_config.get("config", {})

    if provider == "bitcram":
        try:
            return post_sale_doc(config, internal_code, quantity, unit_price)
        except BitcramError as exc:
            raise StockSyncError(str(exc))

    if provider == "none":
        return None

    raise StockSyncError("Unknown stock sync provider: " + str(provider))