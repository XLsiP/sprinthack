import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import Base, SessionLocal, engine
from routers import associates, credentials, evidence, health, stats, verify
from status import refresh_statuses


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        refresh_statuses(db)
    yield


app = FastAPI(title="Beacon Credentialing Tracker", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

for module in (health, associates, credentials, evidence, stats, verify):
    app.include_router(module.router, prefix="/api")
