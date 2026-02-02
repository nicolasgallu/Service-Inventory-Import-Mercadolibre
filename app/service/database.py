from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector
from app.settings.config import INSTANCE_DB, USER_DB, PASSWORD_DB, NAME_DB
from app.utils.logger import logger


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

#LOGICA PARA ACCEDER A DATOS DEL ITEM.
def get_item_data(item_id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data of item: {item_id} from DB")
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
        

#LOGICA PARA ESCRIBIR DATOS DEL ITEM.
def load_item_metadata(item_id, item_metadata):
    with engine.begin() as conn:
        logger.info(f"Saving description & brand for item: {item_id} in DB")
        conn.execute(
            text(f"""
                UPDATE app_import.product_catalog_sync SET 
                 description = :description,
                 brand = :brand
                WHERE id = {item_id}
            """),item_metadata) 

        logger.info("Load Completed.")


#LOGICA PARA ESCRIBIR MELI ID
def load_meli_id(item_id, meli_id):
    with engine.begin() as conn:
        logger.info(f"Saving Meli ID from item: {item_id} in DB")
        conn.execute(
            text(f"""
                UPDATE app_import.product_catalog_sync SET 
                 meli_id = :meli_id
                WHERE id = {item_id}
            """),meli_id) 

        logger.info("Load Completed.")

