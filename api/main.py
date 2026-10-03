import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import scheduler
from db import Base, SessionLocal, engine, ensure_indexes
from routers import alerts, associates, credentials, evidence, health, jobs, stats, verify
from status import refresh_statuses


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    ensure_indexes()
    with SessionLocal() as db:
        refresh_statuses(db)
    scheduler.start()
    yield
    scheduler.shutdown()


def cors_settings() -> dict:
    """Allowed browser origins: a comma-separated CORS_ORIGINS list, plus an optional CORS_ORIGIN_REGEX."""
    origins = [o.strip().rstrip("/") for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]
    return {
        "allow_origins": [o for o in origins if o],
        "allow_origin_regex": os.environ.get("CORS_ORIGIN_REGEX", "").strip() or None,
    }


app = FastAPI(title="Beacon Credentialing Tracker", lifespan=lifespan)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        "%s: %s" % (".".join(str(part) for part in error["loc"]), error["msg"])
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "; ".join(errors)})


app.add_middleware(
    CORSMiddleware,
    **cors_settings(),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

for module in (health, alerts, associates, credentials, evidence, jobs, stats, verify):
    app.include_router(module.router, prefix="/api")
