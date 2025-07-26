from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import os
import hashlib
from datetime import date as date_type, datetime

from gemini_adk_demo import crud, schemas
from gemini_adk_demo.database import get_db
from ..exceptions import APIException

router = APIRouter(
    prefix="/metrics",
    tags=["metrics"],
)

STREAMLIT_APP_URL = os.environ.get("STREAMLIT_APP_URL")


@router.get("/user/{user_email}", response_model=List[schemas.DailyMetric])
def get_user_daily_metrics(
    user_email: str, limit: int = 30, db: Session = Depends(get_db)
):
    """
    Retrieves recent daily metrics for a given user.
    """
    metrics = crud.get_daily_metrics_for_user(
        db=db, user_email=user_email, skip=0, limit=limit
    )
    if not metrics:
        return []
    return metrics


@router.get("/log_mood_via_redirect", response_class=RedirectResponse)
def log_mood_via_redirect(
    email: str,
    date: str,
    mood_value: str,
    mood_emoji: str,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Logs a user's mood from a link clicked in an email and then redirects to the Streamlit app.
    """
    secret_key = os.environ.get("SUBSCRIPTION_SECRET_KEY")
    if not secret_key:
        raise APIException(
            status_code=500, detail="Subscription secret key is not configured."
        )

    expected_token = hashlib.sha256(f"{email}{secret_key}".encode()).hexdigest()
    if token != expected_token:
        raise APIException(status_code=400, detail="Invalid token.")
    try:
        metric_date_obj: date_type = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise APIException(status_code=400, detail="Invalid date format.")

    try:
        preference = crud.get_newsletter_preference(db, user_email=email)
        if not preference:
            preference_create = schemas.NewsletterPreferenceCreate(user_email=email)
            crud.create_newsletter_preference(db=db, preference=preference_create)

        metric_create_data = schemas.DailyMetricCreate(
            user_email=email,
            metric_date=metric_date_obj,
            morning_mood_subjective=f"{mood_emoji} {mood_value}",
        )
        crud.create_or_update_daily_metric(db=db, metric=metric_create_data)

    except Exception as e:
        db.rollback()
        raise APIException(status_code=500, detail="Could not log mood.")

    return RedirectResponse(url=f"{STREAMLIT_APP_URL}", status_code=303)
