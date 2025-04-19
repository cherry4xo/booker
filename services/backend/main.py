import uvicorn 

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.fill import run_seeding
from app.db import init
from app import settings
from app.routes.auditorium import router as auditorium_router
from app.routes.availability import router as availability_router
from app.routes.booking import router as booking_router
from app.routes.equipment import router as equipment_router
from app.routes.users import router as users_router


def init_middlewares(app: FastAPI):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS
    )


app = FastAPI()


main_app_lifespan = app.router.lifespan_context
@asynccontextmanager
async def lifespan_wrapper(app):
    await init(app)
    await run_seeding()
    async with main_app_lifespan(app) as maybe_state:
        yield maybe_state
app.router.lifespan_context = lifespan_wrapper

init_middlewares(app)
app.include_router(auditorium_router, prefix="/auditoriums", tags=["auditorium"])
app.include_router(availability_router, prefix="/availability", tags=["availability"])
app.include_router(booking_router, prefix="/bookings", tags=["booking"])
app.include_router(equipment_router, prefix="/equipment", tags=["equipment"])
app.include_router(users_router, prefix="/users", tags=["users"])

# if __name__ == "__main__":
#     uvicorn.run(app, host=settings.API_HOST, port=int(settings.API_PORT))