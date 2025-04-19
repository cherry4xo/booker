import os
import uuid
import logging
import errno

from tortoise.contrib.fastapi import register_tortoise
from aerich import Command, exceptions as aerich_exceptions
from fastapi import FastAPI

from app import settings

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # set to DEBUG to capture all logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

def get_tortoise_config() -> dict:
    app_list = ["app.models", "aerich.models"]
    config = {
        "connections": settings.DB_CONNECTIONS,
        "apps": {
            "models": {
                "models": app_list,
                "default_connection": "default"
            }
        }
    }   
    return config

TORTOISE_ORM = get_tortoise_config()
MIGRATION_LOCATION = "./migrations"
AERICH_COMMAND = Command(tortoise_config=TORTOISE_ORM, app="models", location=MIGRATION_LOCATION)
MODELS_MIGRATION_PATH = os.path.join(AERICH_COMMAND.location, AERICH_COMMAND.app)

def register_db(app: FastAPI, db_url: str = None) -> None:
    db_url = db_url or settings.DB_URL
    app_list = ["app.models", "aerich.models"]
    register_tortoise(
        app,
        db_url=db_url,
        modules={"models": app_list},
        generate_schemas=True,
        add_exception_handlers=True
    )

async def upgrade_db(app: FastAPI, db_url: str = None):
    """
    Initializes Aerich and applies any pending migrations.
    Should be run during application startup.
    """
    logger.info("Initializing database and applying migrations...")
    logger.debug("Using Aerich config: %s", TORTOISE_ORM)
    logger.debug("Migrations base location: %s", AERICH_COMMAND.location)
    logger.debug("App-specific migration path: %s", MODELS_MIGRATION_PATH)
    logger.debug("Current working directory: %s", os.getcwd())

    try:
        try:
            os.makedirs(AERICH_COMMAND.location, exist_ok=True)
            logger.info(f"Ensured base migration directory exists: {AERICH_COMMAND.location}")
        except OSError as e:
            logger.error(f"Could not create base migration directory {AERICH_COMMAND.location}: {e}", exc_info=True)
            raise

        logger.info("Running 'aerich init-db' to ensure schema table exists...")
        try:
            await AERICH_COMMAND.init_db(safe=True) # safe=True prevents error if table already exists
            logger.info("'aerich init-db' finished.")
        except Exception as init_db_exc:
            logger.critical(f"Failed during 'aerich init-db': {init_db_exc}", exc_info=True)
            raise # If we can't even ensure the table, stop here.

        logger.info("Running 'aerich init'...")
        await AERICH_COMMAND.init()
        logger.info("'aerich init' finished.")

        if not os.path.isdir(MODELS_MIGRATION_PATH):
            logger.error(f"Directory '{MODELS_MIGRATION_PATH}' was STILL NOT found after 'aerich init'.")
            logger.error("This indicates a persistent issue with 'aerich init' creating the directory/initial file.")
            raise FileNotFoundError(f"Aerich failed to create migration directory '{MODELS_MIGRATION_PATH}' during 'init'.")
        else:
            logger.info(f"Verified app-specific directory exists: {MODELS_MIGRATION_PATH}")

        logger.info("Running 'aerich upgrade'...")
        await AERICH_COMMAND.upgrade(run_in_transaction=True)
        logger.info("'aerich upgrade' finished.")
        logger.info("Database migrations applied successfully.")

    except aerich_exceptions.MigrationNotInitialized as e:
        logger.critical(f"Caught MigrationNotInitialized during upgrade phase, which is unexpected after init: {e}", exc_info=True)
        raise

    except FileNotFoundError as e:
        logger.critical(f"Migration directory check failed: {e}", exc_info=True)
        print(f"FATAL: Missing migration directory: {e}")
        raise

    except Exception as e:
        logger.critical("Failed to apply database migrations due to an unexpected error.", exc_info=True)
        print(f"FATAL: Failed to apply migrations: {e}")
        raise

async def init(app: FastAPI):
    await upgrade_db(app)
    register_db(app)
    logger.debug("Connected to db")