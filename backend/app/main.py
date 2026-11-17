"""FastAPI application entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive API docs: http://localhost:8000/docs
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import analytics, auth, transactions


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates tables on startup. For a production app, use migrations (Alembic) instead.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Finance Dashboard API",
    description="Import bank statements, categorise spending and see where your money goes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(analytics.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
