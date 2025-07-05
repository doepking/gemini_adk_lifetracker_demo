from pydantic import BaseModel, field_validator
from typing import Optional, List
import datetime

class TaskBase(BaseModel):
    description: str
    status: Optional[str] = "open"
    deadline: Optional[datetime.datetime] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    id: int
    description: Optional[str] = None
    status: Optional[str] = None
    deadline: Optional[datetime.datetime] = None

    @field_validator("deadline", mode="before")
    @classmethod
    def make_deadline_timezone_aware(cls, v):
        if isinstance(v, str):
            try:
                dt_obj = datetime.datetime.fromisoformat(v.replace("Z", "+00:00"))
                # If the datetime object is naive, assume UTC
                if dt_obj.tzinfo is None:
                    return dt_obj.replace(tzinfo=datetime.timezone.utc)
                return dt_obj
            except (ValueError, TypeError):
                return None
        elif isinstance(v, datetime.datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=datetime.timezone.utc)
        return v

class Task(TaskBase):
    id: int
    user_id: int
    created_at: datetime.datetime
    completed_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True

class TextInputBase(BaseModel):
    content: str
    category: Optional[str] = "Note"

class TextInputCreate(TextInputBase):
    pass

class TextInputUpdate(TextInputBase):
    id: int

class TextInput(TextInputBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class BackgroundInfoBase(BaseModel):
    content: dict

class BackgroundInfoCreate(BackgroundInfoBase):
    pass

class BackgroundInfo(BackgroundInfoBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class BackgroundInfoResponse(BaseModel):
    status: str
    updated_info: Optional[dict] = None
    message: Optional[str] = None

class UserBase(BaseModel):
    email: str
    username: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    tasks: List[Task] = []
    text_inputs: List[TextInput] = []
    background_info: List[BackgroundInfo] = []

    class Config:
        orm_mode = True

class StatusResponse(BaseModel):
    status: str
    message: str

# --- NewsletterPreference Schemas ---

class NewsletterPreferenceBase(BaseModel):
    user_email: str

class NewsletterPreferenceCreate(NewsletterPreferenceBase):
    pass

class NewsletterPreference(NewsletterPreferenceBase):
    id: int
    subscribed: bool
    subscribed_at: Optional[datetime.datetime] = None
    unsubscribed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

# --- DailyMetric Schemas ---

class DailyMetricBase(BaseModel):
    user_email: str
    metric_date: datetime.date
    morning_mood_subjective: Optional[str] = None

class DailyMetricCreate(DailyMetricBase):
    pass

class DailyMetric(DailyMetricBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        orm_mode = True

# --- Schemas for API request bodies ---
class SubscribeRequest(BaseModel):
    email: str

class UnsubscribeRequest(BaseModel):
    email: str

class LogMetricRequest(BaseModel):
    email: str
    date: datetime.date
    morning_mood_subjective: Optional[str] = None
