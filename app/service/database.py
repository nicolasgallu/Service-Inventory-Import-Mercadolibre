from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector
from app.settings.config import INSTANCE_DB, USER_DB, PASSWORD_DB, NAME_DB
from app.utils.logger import logger

##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
##CAMBIAR ESQUEMAS FIJOS A PARAMETROS 
##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


def getconn():
    connector = Connector() 
    return connector.connect(
        INSTANCE_DB,
        "pymysql",
        user=USER_DB,
        password=PASSWORD_DB,
        db=NAME_DB,
    )   

engine = create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=2,
    )

def get_item_data(item_id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data from item: {item_id}.")
        result = conn.execute(
            text(f"""
                SELECT * FROM app_import.product_catalog_sync
                WHERE id = {item_id};
            """)
        )
        data = [dict(row) for row in result.mappings()][0]
        if data:
            logger.info("Data extraction completed.")
            return data
        else:
            logger.info("Data extraction failed.")
            return None
        

def load_ai_response(item_id, field ,ai_response):
    """writting field description or title using ai reply,
    this is part from the pre-publish event."""
    with engine.begin() as conn:
        logger.info(f"Saving {field} for item: {item_id}.")
        conn.execute(
            text(f"""
                UPDATE app_import.product_catalog_sync SET 
                {field} = :ai_response
                WHERE id = {item_id}
            """),ai_response) 
        logger.info("Load Completed.")


def load_failed_status(item_id, item_metadata):
    with engine.begin() as conn:
        logger.info(f"Saving status & reason for item: {item_id}.")
        conn.execute(
            text(f"""
                UPDATE app_import.product_catalog_sync SET 
                 status = :status,
                 reason = :reason
                WHERE id = {item_id}
            """),item_metadata) 
        logger.info("Load Completed.")


#LOGICA PARA ESCRIBIR MELI ID
def load_meli_data(item_id, item_metadata):
    with engine.begin() as conn:
        logger.info(f"Saving Meli ID & Permalink for item: {item_id}.")
        conn.execute(
            text(f"""
                UPDATE app_import.product_catalog_sync SET 
                 meli_id = :meli_id,
                 permalink = :permalink,
                 status = :status,
                 reason = :reason,
                 remedy = :remedy

                WHERE id = {item_id}
            """),item_metadata) 
        logger.info("Load Completed.")

#//////////////MELI ORDERS LOGIC//////////////

def get_order(order_id):
    """Checking if order exists in DB
    Returns True if exists otherwise False."""
    with engine.begin() as conn:
        logger.info("Getting order from DB.")
        result = conn.execute(
            text(f"""
                SELECT
                id
                FROM mercadolibre.orders
                WHERE id = {order_id};
            """)
        )
    try:
        # Intentamos obtener el primer elemento directamente
        [dict(row) for row in result.mappings()][0]
        return True
    except IndexError:
        # Si la lista estaba vacía, el índice [0] no existe y devuelve False
        return False

def insert_order(order):
    with engine.begin() as conn:
        logger.info("Saving Order in DB.")
        conn.execute(
            text("""
                INSERT INTO mercadolibre.orders (id, data, created_at)
                VALUES (:id, :data, :created_at)
            """),order) 
        logger.info("Load Completed.")

def get_bitcram_data(meli_id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data from Meli_ID: {meli_id}.")
        result = conn.execute(
            text(f"""
                SELECT
                id,
                cost
                FROM app_import.product_catalog_sync
                WHERE meli_id = '{meli_id}';
            """)
        )
        data = [dict(row) for row in result.mappings()][0]
        if data:
            logger.info("Data extraction completed.")
            return data
        else:
            logger.info("Data extraction failed.")
            return None