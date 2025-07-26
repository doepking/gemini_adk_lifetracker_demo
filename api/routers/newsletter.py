import os
import hashlib
from google.cloud import logging as google_cloud_logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from gemini_adk_demo import crud, schemas
from gemini_adk_demo.database import get_db
from gemini_adk_demo.tools import newsletter_sender
from ..exceptions import APIException
from ..dependencies import verify_internal_api_key

router = APIRouter(
    prefix="/newsletter",
    tags=["newsletter"]
)
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

# --- Newsletter Endpoints ---


@router.post(
    "/subscribe/{user_email}/{token}",
    response_model=schemas.NewsletterPreference,
    status_code=status.HTTP_201_CREATED
)
def subscribe_newsletter(
    user_email: str, token: str, db: Session = Depends(get_db)
):
    """
    Subscribes a user to the newsletter.
    If the user already exists, it updates their status to subscribed.
    """
    secret_key = os.environ.get("SUBSCRIPTION_SECRET_KEY")
    if not secret_key:
        raise APIException(
            status_code=500, detail="Subscription secret key is not configured."
        )

    expected_token = hashlib.sha256(f"{user_email}{secret_key}".encode()).hexdigest()
    if token != expected_token:
        raise APIException(status_code=400, detail="Invalid subscribe token.")

    db_preference = crud.get_newsletter_preference(db, user_email=user_email)
    if db_preference and db_preference.subscribed:
        return db_preference

    preference_create = schemas.NewsletterPreferenceCreate(
        user_email=user_email
    )
    created_preference = crud.create_newsletter_preference(
        db=db, preference=preference_create
    )
    return created_preference


@router.get(
    "/preferences/{user_email}", response_model=schemas.NewsletterPreference,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_internal_api_key)],
)
def get_newsletter_preference(user_email: str, db: Session = Depends(get_db)):
    """
    Retrieves the newsletter subscription preference for a given user email.
    """
    db_preference = crud.get_newsletter_preference(db, user_email=user_email)
    if db_preference is None:
        raise APIException(
            status_code=404, detail=f"Preference not found for user {user_email}"
        )
    return db_preference


@router.api_route("/unsubscribe/{user_email}/{token}", methods=["GET", "POST"])
def unsubscribe_from_link(user_email: str, token: str, db: Session = Depends(get_db)):
    """
    Unsubscribes a user from the newsletter via a link with a token.
    This endpoint handles both GET requests from email links and POST requests from the frontend.
    """
    secret_key = os.environ.get("SUBSCRIPTION_SECRET_KEY")
    if not secret_key:
        raise APIException(
            status_code=500, detail="Subscription secret key is not configured."
        )

    expected_token = hashlib.sha256(f"{user_email}{secret_key}".encode()).hexdigest()
    if token != expected_token:
        raise APIException(status_code=400, detail="Invalid unsubscribe token.")

    db_preference = crud.update_newsletter_preference(
        db=db, user_email=user_email, subscribed=False
    )
    if db_preference is None:
        raise APIException(
            status_code=404,
            detail=f"User with email {user_email} not found or not subscribed.",
        )

    return JSONResponse(
        status_code=200, content={"message": "You have been successfully unsubscribed."}
    )


# 1x1 transparent GIF pixel, base64 encoded
# GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;
TRANSPARENT_GIF_BYTES = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f90401000000002c00000000010001000002024401003b"
)


@router.get("/track/open/{log_id}", tags=["internal"], status_code=status.HTTP_200_OK)
async def track_newsletter_open(log_id: int, db: Session = Depends(get_db)):
    """
    Tracks a newsletter open via a 1x1 pixel.
    Updates the 'opened_at' field for the corresponding SentNewsletterLog entry.
    Returns a 1x1 transparent GIF.
    """
    try:
        updated_log = crud.update_sent_newsletter_log_opened_at(db=db, log_id=log_id)
        if updated_log:
            logger.log_text(
                f"Newsletter open tracked for log_id: {log_id}", severity="INFO"
            )
        else:
            logger.log_text(
                f"Newsletter open tracking: No update for log_id: {log_id} (possibly already tracked or not found).",
                severity="INFO",
            )
    except Exception as e:
        logger.log_text(
            f"Error tracking newsletter open for log_id {log_id}: {e}", severity="ERROR"
        )
        # Still return the pixel to not break email clients, but log the error.

    return Response(content=TRANSPARENT_GIF_BYTES, media_type="image/gif")


@router.post(
    "/send-daily",
    tags=["internal"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_internal_api_key)],
)
async def trigger_daily_newsletter_sending(db: Session = Depends(get_db)):
    """
    Endpoint to be triggered by Cloud Scheduler to send daily newsletters.
    This endpoint is protected by an internal API key.
    """
    try:
        await newsletter_sender.process_and_send_newsletters(db=db)
    except Exception as e:
        logger.log_text(
            f"Error during scheduled newsletter sending: {e}", severity="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send newsletters: {str(e)}",
        )
