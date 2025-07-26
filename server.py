import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel
from typing import Literal, Union
from google.cloud import logging as google_cloud_logging
from tracing import CloudTraceLoggingSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export

from gemini_adk_demo.database import init_db, engine, SessionLocal
from gemini_adk_demo import crud
from api.routers import newsletter, metrics, users
from api.exceptions import setup_exception_handlers

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

STREAMLIT_APP_URL = os.environ.get("STREAMLIT_APP_URL")
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR_NAME = os.path.basename(os.path.normpath(AGENT_DIR))

app_args = {"agents_dir": AGENT_DIR, "web": True}

provider = TracerProvider()
processor = export.BatchSpanProcessor(CloudTraceLoggingSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Create FastAPI app with appropriate arguments
app: FastAPI = get_fast_api_app(**app_args)

# Setup exception handlers
setup_exception_handlers(app)

# Initialize application state directly
app.state.request_cache = {}
app.state.rate_limiter = {}

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    """
    Middleware to cache requests and prevent duplicate function calls.
    Note: SSE endpoints are excluded from caching as they are streaming responses.
    """
    # Skip caching for SSE endpoints and streaming responses
    if request.url.path.endswith(
        "/run_sse"
    ) or "text/event-stream" in request.headers.get("accept", ""):
        return await call_next(request)

    if "X-Request-ID" in request.headers:
        request_id = request.headers["X-Request-ID"]
        if request_id in request.app.state.request_cache:
            return request.app.state.request_cache[request_id]

    response = await call_next(request)

    # Only cache non-streaming responses
    if "X-Request-ID" in request.headers and not hasattr(response, "body_iterator"):
        request.app.state.request_cache[request_id] = response

    return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to limit the number of requests per user.
    """
    user_email = request.headers.get("X-User-Email")
    if user_email:
        if user_email not in request.app.state.rate_limiter:
            request.app.state.rate_limiter[user_email] = []
        request.app.state.rate_limiter[user_email].append(time.time())
        if len(request.app.state.rate_limiter[user_email]) > 100:
            if (
                request.app.state.rate_limiter[user_email][-1]
                - request.app.state.rate_limiter[user_email][-101]
                < 60
            ):
                return JSONResponse(
                    status_code=429,
                    content={"message": "Too many requests"},
                )
    response = await call_next(request)
    return response

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    db = SessionLocal()
    try:
        request.state.db = db
        user_email = request.headers.get("X-User-Email")
        user_name = request.headers.get("X-User-Name")

        # The ADK by default forwards the user_id from the /run_sse payload to the /sessions endpoint.
        # We need to extract it from the request path.
        path_parts = request.url.path.split("/")
        user_id_from_path = None
        if "users" in path_parts and "sessions" in path_parts:
            try:
                user_id_index = path_parts.index("users") + 1
                user_id_from_path = int(path_parts[user_id_index])
            except (ValueError, IndexError):
                pass

        user = None
        if user_id_from_path:
            logger.log_text(
                f"db_session_middleware: Found user_id in path: {user_id_from_path}",
                severity="INFO",
            )
            user = crud.get_or_create_user(db, user_id=user_id_from_path)
        elif user_email:
            logger.log_text(
                f"db_session_middleware: Received user_email from header: {user_email}",
                severity="INFO",
            )
            user = crud.get_or_create_user(
                db, user_email=user_email, user_name=user_name
            )

        if user:
            request.state.user = user
            logger.log_text(
                f"db_session_middleware: User object set in request.state: {user.id}, {user.email}",
                severity="INFO",
            )
        else:
            logger.log_text(
                "db_session_middleware: Could not identify user.", severity="WARNING"
            )

        response = await call_next(request)
        return response
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    This is where we'll initialize the database.
    """
    logger.log_text("Application startup: Initializing database...", severity="INFO")
    try:
        init_db()
        logger.log_text("Database initialization successful.", severity="INFO")
    except Exception as e:
        logger.log_text(
            f"Fatal error during database initialization: {e}", severity="ERROR"
        )
        # Depending on the desired behavior, you might want to exit or handle this differently.
        # For now, we log it and let the app continue, though it will likely fail on DB operations.
        pass


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.log_text("Application shutdown: Disposing database engine.", severity="INFO")
    if engine:
        engine.dispose()

app.title = AGENT_DIR_NAME
app.description = f"API for interacting with the Agent {AGENT_DIR_NAME}"


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: Union[int, float]
    text: Union[str, None] = ""
    invocation_id: str
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal[AGENT_DIR_NAME] = AGENT_DIR_NAME
    user_id: str = ""


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}

app.include_router(newsletter.router)
app.include_router(metrics.router)
app.include_router(users.router)

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
