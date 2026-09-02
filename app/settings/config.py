import os
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID=os.getenv("PROJECT_ID")

DS_API_KEY=os.getenv("DS_API_KEY")
TOKEN_WHAPI=os.getenv("TOKEN_WHAPI")
PHONE_INTERNAL=os.getenv("PHONE_INTERNAL")

### NEW VARIABLES

# DB Schema
SCHEMA_ACCOUNTS=os.getenv("SCHEMA_ACCOUNTS")
SCHEMA_MERCADOLIBRE=os.getenv("SCHEMA_MERCADOLIBRE")
SCHEMA_INVENTORY=os.getenv("SCHEMA_INVENTORY")
SCHEMA_AI=os.getenv("SCHEMA_AI")
SCHEMA_TIENDANUBE = os.getenv("SCHEMA_TIENDANUBE")

# Database connection
INSTANCE_DB = os.getenv("INSTANCE_DB")  # Cloud SQL instance connection name
USER_DB = os.getenv("USER_DB")
PASSWORD_DB = os.getenv("PASSWORD_DB")
NAME_DB = os.getenv("NAME_DB")