# Syncs a product's MeLi pictures into GCS and stores their public URLs in the DB.
import io
import requests
from PIL import Image
from google.cloud import storage
from sqlalchemy import text
from app.settings.config import SCHEMA_INVENTORY
from app.integrations.mercadolibre.product_handler import get_data_for_meli
from app.integrations.core.credentials import get_access_token
from app.db.engine import engine
from app.utils.logger import logger

# --- CONFIGURATION ---
BUCKET_NAME = "pictures_ecommerce_guiaslocales"  # must be publicly readable (see notes below)
MAX_PICTURES = 10                   # max images stored per product
IMAGES_TABLE = f"{SCHEMA_INVENTORY}.product_images"


def _download_as_png(url):
    """Download one image and convert it to PNG, all in memory (no disk I/O)."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    buffer = io.BytesIO()
    with Image.open(io.BytesIO(resp.content)) as img:
        img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def _save_product_images(product_id, urls):
    """Replace the product's image rows with the new URLs in one transaction."""
    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM {IMAGES_TABLE} WHERE product_id = :product_id"),
            {"product_id": product_id},
        )
        if urls:
            conn.execute(
                text(f"INSERT INTO {IMAGES_TABLE} (product_id, url) VALUES (:product_id, :url)"),
                [{"product_id": product_id, "url": url} for url in urls],
            )


def meli_ai_pictures(payload):
    """
    Entry point for the Cloud Function.
    1. Fetch up to MAX_PICTURES pictures from the product's MeLi item.
    2. Upload them to GCS: {BUCKET_NAME}/{product_id}/1.png ... N.png
    3. Replace the product_images DB rows with the new public URLs.
    """
    logger.info("executing mvp meli pictures job")

    try:
        product_id = payload.get("product_id")
        account_id = payload.get("account_id")

        token = get_access_token(account_id).get("access_token")
        product_data = get_data_for_meli(product_id)
        meli_id = product_data.get("meli_id")

        if not meli_id:
            logger.info(f"Product {product_id} is not published on MeLi, nothing to do.")
            return "Product not published on MeLi", 200

        # 1. Get the pictures from MeLi (capped at MAX_PICTURES)
        resp = requests.get(
            f"https://api.mercadolibre.com/items/{meli_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        resp.raise_for_status()
        pictures = resp.json().get("pictures", [])[:MAX_PICTURES]

        if not pictures:
            logger.info(f"No images found for MeLi item {meli_id}")
            return "No images found", 200

        # 2. Remove previous images and upload the new ones to GCS
        client = storage.Client()  # uses the Cloud Function's service account
        bucket = client.bucket(BUCKET_NAME)
        prefix = f"{product_id}/"

        for old_blob in bucket.list_blobs(prefix=prefix):
            old_blob.delete()

        urls = []
        for idx, pic in enumerate(pictures, start=1):
            img_url = pic.get("secure_url") or pic.get("url")
            png_buffer = _download_as_png(img_url)

            blob = bucket.blob(f"{prefix}{idx}.png")
            blob.upload_from_file(png_buffer, content_type="image/png")
            urls.append(blob.public_url)
            logger.info(f"Uploaded gs://{BUCKET_NAME}/{blob.name}")

        # 3. Save the public URLs in the DB
        _save_product_images(product_id, urls)

        return "Success", 200

    except Exception as e:
        logger.error(f"Error in mvp_meli_pictures: {str(e)}")
        return f"Internal Error: {str(e)}", 500