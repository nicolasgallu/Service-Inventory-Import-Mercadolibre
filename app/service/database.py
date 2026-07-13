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


def get_ai_prompt(field):
    with engine.begin() as conn:
        logger.info(f"Extracting AI prompt: {field}.")
        result = conn.execute(
            text(f"""
                SELECT 
                    {field}
                FROM mercadolibre.prompts
                LIMIT1;
            """)
        )
        data = [dict(row) for row in result.mappings()][0]
        logger.info("Extraction Complete.")
        return data


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
            return data[0]
        else:
            logger.info("Data extraction failed.")
            return None


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


def upsert_method(data:dict, schema:str, table:str):
    """Dinamic Upsert Method.

        Attributes:
            data: dict, with the fields and values.
            in db, and the values required. (note, first key value would always be take as ID)
            schema: str, name of the schema in db.
            table: str, name of the table in db.
    """

    try:
        with engine.begin() as conn:
            fields = [i for i in data.keys()]
            logger.info("Preparing Data to Upsert.")
            aux_query = ""
            values = ""
            
            def _casting_value(field):
                value = data.get(field).get('value')
                value_type = data.get(field).get('type')
                if value_type == 'boolean':
                    return str(value)
                elif value == None:
                    return ''
                else:
                    return f"CAST('{value}' AS {value_type})"
            
            for field in fields:
                value = data.get(field)
                if field == fields[0]:
                    values += _casting_value(field) + ", "
                    id_val = data.get(field).get('value')
                    continue
                if field == fields[-1]:
                    value_casted = _casting_value(field)
                    values += value_casted
                    aux_query+= f"{field} = {value_casted}"
                else:
                    value_casted = _casting_value(field)
                    values += f"{value_casted}, "
                    aux_query+= f"{field} = {value_casted}, "
            
            logger.info(f"Upsert of Record {id_val} on {schema}.{table}")
            conn.execute(text(f"""
                INSERT INTO {schema}.{table} ({', '.join(fields)})
                VALUES ({values})
                ON DUPLICATE KEY UPDATE
                {aux_query}
            """))
            logger.info("Upsert Completed.")

    except Exception as e:
        logger.error(f"Error during data load: {str(e)}")
        raise e



def update_method(data:dict, schema:str, table:str):
    """Dinamic Update Method.

        Attributes:
            data: dict, with the fields and values.
            in db, and the values required. (note, first key value would always be take as ID)
            schema: str, name of the schema in db.
            table: str, name of the table in db.
    """
    aux_query = ""
    def _casting_value(field, data):
        nonlocal aux_query
        value= data.get(field).get('value')
        value_type= data.get(field).get('type')
        if value_type == 'boolean':
            aux_query+= f"{field} = {value}"
        elif value == None:
        #elif value_type == 'null':
            aux_query+= f"{field} = null"
        else:
            aux_query+= f"{field} = CAST('{value}' AS {value_type})"

    try:
        with engine.begin() as conn:
            fields = [i for i in data.keys()]
                       
            logger.info("Preparing Data to update.")
            for field in fields:
                if field == fields[0]:
                    id_field = field
                    id_val = data.get(field).get('value')

                elif field == fields[-1]:
                    _casting_value(field, data)
                else:
                    _casting_value(field, data)
                    aux_query+=","
            
            logger.info(f"Updating Record {id_val} on {schema}.{table}")
            conn.execute(text(f"""
                UPDATE {schema}.{table}
                SET {aux_query}
                WHERE {id_field} = {id_val}
            """))
            logger.info("Update Completed.")

    except Exception as e:
        logger.error(f"Error during data load: {str(e)}")
        raise e


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


def get_bitcram_data(meli_id):
    """"""
    with engine.begin() as conn:
        logger.info(f"Extracting data from Meli_ID: {meli_id}.")
        result = conn.execute(
            text(f"""
                    with 
                    first_match  as (
                    select 
                      a.meli_id,
                      a.id,
                      a.cost,
                      1 as aux_priority 
                      from {SCHEMA_INVENTORY}.product_catalog_sync as a
                      where a.meli_id = '{meli_id}'
                      limit 1
                      ),
                    
                    second_match as (
                    
                      select 
                      a.meli_id,
                      b.id,
                      b.cost,
                      2 as aux_priority 
                      from mercadolibre.catalog_listing as a
                      left join {SCHEMA_INVENTORY}.product_catalog_sync as b on a.meli_id = b.meli_id
                      where a.catalog_product_id in (
                        select catalog_product_id 
                        from mercadolibre.catalog_listing 
                        where meli_id = '{meli_id}') and b.id is not null
                        limit 1
                    ),
                    
                    final as (
                      select * from first_match
                      union all
                      select * from second_match),
                    
                    ranked_results as (
                      select 
                        *,
                        row_number() over(partition by meli_id order by aux_priority asc) as rn
                      from final
                    )
                    
                    select
                    id,
                    cost
                    from ranked_results 
                    where rn = 1
            """)
        )
        data = [dict(row) for row in result.mappings()][0]
        if data:
            logger.info("Data extraction completed.")
            return data
        else:
            logger.info("Data extraction failed.")
            return None