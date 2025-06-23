import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel
from typing import Literal
from google.cloud import logging as google_cloud_logging
from tracing import CloudTraceLoggingSpanExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider, export
from fastapi import Depends
from sqlalchemy.orm import Session

from gemini_adk_demo.shared_libraries.database import init_db, engine, SessionLocal, get_db
from gemini_adk_demo.shared_libraries import crud, schemas

logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Prepare arguments for get_fast_api_app
app_args = {"agents_dir": AGENT_DIR, "web": True}

provider = TracerProvider()
processor = export.BatchSpanProcessor(CloudTraceLoggingSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Create FastAPI app with appropriate arguments
app: FastAPI = get_fast_api_app(**app_args)

# Initialize application state
app.state.request_cache = {}
app.state.rate_limiter = {}

@app.middleware("http")
async def cache_middleware(request: Request, call_next):
    """
    Middleware to cache requests and prevent duplicate function calls.
    """
    if "X-Request-ID" in request.headers:
        request_id = request.headers["X-Request-ID"]
        if request_id in request.app.state.request_cache:
            return request.app.state.request_cache[request_id]
    response = await call_next(request)
    if "X-Request-ID" in request.headers:
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
    response = JSONResponse({"error": "Database session not found"}, status_code=500)
    db = SessionLocal()
    try:
        request.state.db = db
        user_email = request.headers.get("X-User-Email")
        user_name = request.headers.get("X-User-Name")
        if user_email:
            logger.log_text(f"db_session_middleware: Received user_email: {user_email}", severity="INFO")
            user = crud.get_or_create_user(db, user_email, user_name)
            request.state.user = user
            logger.log_text(f"db_session_middleware: User object set in request.state: {user.id}, {user.email}", severity="INFO")
        response = await call_next(request)
    finally:
        db.close()
    return response

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
        logger.log_text(f"Fatal error during database initialization: {e}", severity="ERROR")
        # Depending on the desired behavior, you might want to exit or handle this differently.
        # For now, we log it and let the app continue, though it will likely fail on DB operations.
        pass

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.log_text("Application shutdown: Disposing database engine.", severity="INFO")
    if engine:
        engine.dispose()

app.title = "gemini-adk-demo"
app.description = "API for interacting with the Agent gemini-adk-demo"


class Feedback(BaseModel):
    """Represents feedback for a conversation."""

    score: int | float
    text: str | None = ""
    invocation_id: str
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["gemini-adk-demo"] = "gemini-adk-demo"
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


@app.delete("/users/{user_id}/purge")
def purge_user(user_id: int, db: Session = Depends(get_db)):
    """
    Deletes all data associated with a user.
    """
    result = crud.purge_user_data(db, user_id)
    return result

@app.get("/users/by_email/{user_email}", response_model=schemas.User)
def get_user_by_email(user_email: str, request: Request, db: Session = Depends(get_db)):
    """
    Retrieves a user by their email address.
    """
    user_name = request.headers.get("X-User-Name", "default_user")
    user = crud.get_or_create_user(db, user_email, user_name)
    return user


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
