import os
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader

from gemini_adk_demo import crud, models
from gemini_adk_demo.database import get_db

api_key_header = APIKeyHeader(name="X-Internal-API-Key", auto_error=False)


def get_current_user(
    request: Request, db: Depends = Depends(get_db)
) -> models.User:
    """
    Gets the current user from the database based on the email and name
    provided in the headers.
    """
    user_email = request.headers.get("X-User-Email")
    user_name = request.headers.get("X-User-Name")
    user = crud.get_or_create_user(db, user_email=user_email, user_name=user_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def verify_internal_api_key(api_key: str = Depends(api_key_header)):
    """
    Verifies the internal API key provided in the request header.
    """
    if not api_key or api_key != os.getenv("INTERNAL_API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )
    return True
