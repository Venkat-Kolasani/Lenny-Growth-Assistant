from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.settings import settings

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)


class TraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("x-request-id") or uuid4().hex[:12]
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        response = await call_next(request)
        response.headers["X-Request-ID"] = trace_id
        structlog.contextvars.clear_contextvars()
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        with psycopg.connect(settings.database_url) as conn:
            conn.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS reasoning TEXT")
            conn.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS title TEXT")
            conn.execute("ALTER TABLE sessions ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")
            conn.commit()
    except Exception:
        pass
    try:
        with psycopg.connect(settings.database_url) as conn:
            conn.execute(
                "ALTER TABLE retrieval_traces DROP CONSTRAINT IF EXISTS retrieval_traces_message_id_fkey"
            )
            conn.execute(
                """
                ALTER TABLE retrieval_traces
                  ADD CONSTRAINT retrieval_traces_message_id_fkey
                  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
                """
            )
            conn.commit()
    except Exception:
        pass
    yield


app = FastAPI(title="Lenny Growth Assistant", lifespan=lifespan)
app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(sessions_router)
