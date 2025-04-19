# services/backend/tests/conftest.py
import pytest
import pytest_asyncio
from tortoise import Tortoise, connections

MODELS = [
    "app.models",
    "aerich.models"
]

@pytest_asyncio.fixture(scope="function", autouse=True)
async def initialize_db_test(request):
    """
    Initializes an in-memory SQLite database for each test function.
    """
    db_url = "sqlite://:memory:"
    print(f"--- Initializing DB for {request.node.name} ---")

    config = {
        "connections": {"default": db_url},
        "apps": {
            "models": {
                "models": MODELS,
                "default_connection": "default",
            }
        },
    }

    try:
        await Tortoise.init(
            config=config,
            _create_db=True
        )
        await Tortoise.generate_schemas(
            safe=False
        )
        print(f"--- DB Initialized and Schemas Generated for {request.node.name} ---")
    except Exception as e:
        print(f"!!!!!! DB Initialization failed for {request.node.name}: {e}")
        raise

    yield 

    await connections.close_all(discard=True) 