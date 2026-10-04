from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers import auth, courses, insights, logs, profile


@asynccontextmanager
async def lifespan(_: FastAPI):
    # create_all is enough for v1; swap for Alembic migrations before any real deployment.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Padhotec API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (auth, profile, courses, logs, insights):
    app.include_router(module.router)


@app.get("/health")
def health():
    return {"status": "ok"}
