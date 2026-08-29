from sqlalchemy import create_engine, text
from google.cloud.sql.connector import Connector
from app.utils.logger import logger
from app.settings.config import (
    INSTANCE_DB, 
    USER_DB, 
    PASSWORD_DB, 
    NAME_DB, 
    SCHEMA_INVENTORY
    )

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



def get_businesses():
    """Test database connection and retrieve businesses."""

    with engine.begin() as conn:
        logger.info("Extracting businesses.")

        result = conn.execute(
            text("""
                SELECT *
                FROM platform_accounts.businesses;
            """)
        )

        data = [dict(row) for row in result.mappings()]

        print(data )




def get_tienda_nube_id(id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data from item: {id}.")
        result = conn.execute(
            text(f"""
                SELECT 
                    attribute_id,
                    product_id,
                    item_id
                FROM tienda_nube.product_status
                LEFT JOIN (
                SELECT 
                    id as attribute_id,
                    item_id
                FROM tienda_nube.attributes) as b using (attribute_id)
                WHERE product_id = {id};
            """)
        )
        data = [dict(row) for row in result.mappings()][0]
        return data


def get_item_data(item_id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data from item: {item_id}.")
        result = conn.execute(
            text(f"""
                SELECT * FROM {SCHEMA_INVENTORY}.product_catalog_sync
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


def get_order(order_id, platform):
    """Checking if order exists in DB
    Returns True if exists otherwise False."""
    with engine.begin() as conn:
        logger.info(f"Getting order from orders table in {platform}.")
        result = conn.execute(
            text(f"""
                SELECT
                id
                FROM {platform}.orders
                WHERE id = {order_id};
            """)
        )
    try:
        if [dict(row) for row in result.mappings()][0]:
            return True
        else:
            return False
    except:
        return False

def insert_order(order, platform):
    with engine.begin() as conn:
        logger.info(f"Saving order in orders table in {platform}.")
        conn.execute(
            text(f"""
                INSERT IGNORE INTO {platform}.orders (id, data, created_at)
                VALUES (:id, :data, :created_at)
            """),order) 
        logger.info("Load Completed.")


def get_method(data):
    """returns a single row of a get sql"""
    with engine.begin() as conn:

        q_columns = ', '.join(data.get('q_columns'))
        q_from = data.get('q_from')
        q_join =  ' '.join(data.get('q_join', ''))
        q_where  = data.get('q_where', '')
        q_limit  = data.get('q_limit', '')

        result = conn.execute(
            text(f"""
                SELECT 
                {q_columns} 
                {q_from} 
                {q_join} 
                {q_where} 
                {q_limit}
                """)
            )
        data = [dict(row) for row in result.mappings()]
        if data:
            logger.info("Data extraction completed.")
            return data
        else:
            logger.info("Data extraction is empty.")
            return None


def upsert_method(data: dict, schema: str, table: str):
    """
    Dynamic Upsert Method.

    Args:
        data: Dict con la estructura:
              {
                  "id": {"value": 1, "type": "integer"},
                  "name": {"value": "John", "type": "varchar"},
                  "active": {"value": True, "type": "boolean"}
              }
        schema: Nombre del schema.
        table: Nombre de la tabla.
    """

    try:
        fields = list(data.keys())

        values = []
        update_clauses = []
        params = {}

        logger.info("Preparing Data to Upsert.")

        id_val = data[fields[0]]["value"]

        for field in fields:
            value = data[field]["value"]
            value_type = data[field]["type"]

            if value is None:
                values.append("NULL")

                if field != fields[0]:
                    update_clauses.append(f"{field} = NULL")

            elif value_type == "boolean":
                values.append(f":{field}")
                params[field] = value

                if field != fields[0]:
                    update_clauses.append(f"{field} = :{field}")

            else:
                values.append(f"CAST(:{field} AS {value_type})")
                params[field] = value

                if field != fields[0]:
                    update_clauses.append(
                        f"{field} = CAST(:{field} AS {value_type})"
                    )

        query = text(f"""
            INSERT INTO {schema}.{table} ({', '.join(fields)})
            VALUES ({', '.join(values)})
            ON DUPLICATE KEY UPDATE
                {', '.join(update_clauses)}
        """)

        logger.info(f"Upsert of Record {id_val} on {schema}.{table}")

        with engine.begin() as conn:
            conn.execute(query, params)

        logger.info("Upsert Completed.")

    except Exception as e:
        logger.error(f"Error during data load: {e}")
        raise

def update_method(data: dict, schema: str, table: str):
    """
    Dynamic Update Method.

    Args:
        data: Dict con la estructura:
              {
                  "id": {"value": 1, "type": "integer"},
                  "name": {"value": "John", "type": "varchar"},
                  "active": {"value": True, "type": "boolean"}
              }
        schema: Nombre del schema.
        table: Nombre de la tabla.
    """

    try:
        fields = list(data.keys())

        id_field = fields[0]
        id_value = data[id_field]["value"]

        set_clauses = []
        params = {"id_value": id_value}

        for field in fields[1:]:
            value = data[field]["value"]
            value_type = data[field]["type"]

            if value is None:
                set_clauses.append(f"{field} = NULL")

            elif value_type == "boolean":
                set_clauses.append(f"{field} = :{field}")
                params[field] = value

            else:
                set_clauses.append(
                    f"{field} = CAST(:{field} AS {value_type})"
                )
                params[field] = value

        query = text(f"""
            UPDATE {schema}.{table}
            SET {", ".join(set_clauses)}
            WHERE {id_field} = :id_value
        """)

        logger.info(f"Updating record {id_value} on {schema}.{table}")

        with engine.begin() as conn:
            conn.execute(query, params)

        logger.info("Update completed.")

    except Exception as e:
        logger.error(f"Error during data load: {e}")
        raise

