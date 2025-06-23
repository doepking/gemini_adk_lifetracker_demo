import os
import logging
import sqlalchemy
from sqlalchemy.orm import sessionmaker
from google.cloud.sql.connector import Connector, IPTypes
import pg8000
from dotenv import load_dotenv

# Import Base from models, it's needed for init_db
from .models import Base

# Load environment variables from .env file first
load_dotenv()

# Configure logging
logger = logging.getLogger("app")

# --- Database Configuration and Setup ---
INSTANCE_CONNECTION_NAME = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
DB_USER = os.environ.get("CLOUD_SQL_USER")
DB_PASS = os.environ.get("CLOUD_SQL_PASSWORD")
DB_NAME = os.environ.get("CLOUD_SQL_DATABASE_NAME")
PRIVATE_IP = os.environ.get("PRIVATE_IP")

# Validate that all required environment variables are set.
if not all([INSTANCE_CONNECTION_NAME, DB_USER, DB_PASS, DB_NAME]):
    logger.critical("Database environment variables are not fully set.")
    # This is a fatal error, so we raise an exception to stop the application.
    raise ValueError("Database environment variables are not fully set.")

connector = Connector()

def _get_db_connection(db_name: str) -> pg8000.dbapi.Connection:
    """Helper function to establish a database connection."""
    ip_type = IPTypes.PRIVATE if PRIVATE_IP == "True" else IPTypes.PUBLIC
    try:
        return connector.connect(
            INSTANCE_CONNECTION_NAME,
            "pg8000",
            user=DB_USER,
            password=DB_PASS,
            db=db_name,
            ip_type=ip_type,
        )
    except Exception as e:
        logger.error(f"Error connecting to database in _get_db_connection: {e}", exc_info=True)
        raise

def create_database_if_not_exists():
    """Connects to the default 'postgres' db and creates the target DB if it doesn't exist."""
    try:
        logger.info("Attempting to connect to 'postgres' database to check for target DB.")
        initial_conn = _get_db_connection("postgres")
        initial_conn.autocommit = True
        cursor = initial_conn.cursor()
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        if not cursor.fetchone():
            logger.info(f"Database '{DB_NAME}' not found. Creating it now.")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info(f"Database '{DB_NAME}' created successfully.")
        else:
            logger.info(f"Database '{DB_NAME}' already exists.")
        cursor.close()
        initial_conn.close()
    except Exception as e:
        logger.error(f"Error in create_database_if_not_exists: {e}", exc_info=True)
        raise

# Create the database if it doesn't exist when the module is loaded.
create_database_if_not_exists()

def getconn() -> pg8000.dbapi.Connection:
    """Establishes a connection to the application's Cloud SQL database."""
    try:
        return _get_db_connection(DB_NAME)
    except Exception as e:
        logger.error(f"Error connecting to database in getconn: {e}", exc_info=True)
        raise

# Create the SQLAlchemy engine at the module level.
engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
    pool_recycle=1800,
    pool_pre_ping=True,
    connect_args={"timeout": 30},
    pool_timeout=30
)

# Create a session factory at the module level.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    Creates database tables based on SQLAlchemy models.
    This should be called from the application startup event.
    """
    try:
        logger.info("Creating database tables based on models...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        raise

def get_db():
    """
    Generator function for FastAPI dependency injection to get a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
