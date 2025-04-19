# services/backend/tests/conftest.py
import pytest
import pytest_asyncio
from tortoise import Tortoise, connections

# Define the models Tortoise should know about for tests
MODELS = [
    "app.models", # Your application models
    "aerich.models" # Required by Tortoise/Aerich
]

@pytest_asyncio.fixture(scope="function", autouse=True)
async def initialize_db_test(request):
    """
    Initializes an in-memory SQLite database for each test function.
    """
    db_url = "sqlite://:memory:" # Use in-memory SQLite for tests
    print(f"--- Initializing DB for {request.node.name} ---") # Debugging print

    config = {
        "connections": {"default": db_url}, # Use the memory DB URL
        "apps": {
            "models": {
                "models": MODELS,
                "default_connection": "default",
            }
        },
        # "timezone": "UTC", # Add if needed
    }

    try:
        await Tortoise.init(
            config=config,
            _create_db=True # <<< Ensure DB is created (needed for sqlite :memory:)
        )
        await Tortoise.generate_schemas(
            safe=False # <<< Generate schema even if tables exist (cleans slate)
        )
        print(f"--- DB Initialized and Schemas Generated for {request.node.name} ---") # Debugging
    except Exception as e:
        print(f"!!!!!! DB Initialization failed for {request.node.name}: {e}")
        raise

    yield # Test runs here

    # print(f"--- Finalizing DB for {request.node.name} ---") # Debugging
    await connections.close_all(discard=True) 


# Optional: If you prefer manual control instead of autouse=True
# You can use the initializer/finalizer from tortoise.contrib.test
# @pytest_asyncio.fixture(scope="function")
# async def db_init_manual():
#     db_url = "sqlite://:memory:"
#     initializer(MODELS, db_url=db_url, app_label="models")
#     yield
#     finalizer()
# Then mark tests needing DB with @pytest.mark.usefixtures("db_init_manual")