from pydantic import BaseModel
from typing import Optional, List
import datetime

class TaskBase(BaseModel):
    description: str
    status: Optional[str] = "open"
    deadline: Optional[datetime.datetime] = None

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

class TextInput(TextInputBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class BackgroundInfoBase(BaseModel):
    content: dict

class BackgroundInfo(BackgroundInfoBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    class Config:
        orm_mode = True

class UserBase(BaseModel):
    email: str
    username: Optional[str] = None

class User(UserBase):
    id: int
    tasks: List[Task] = []
    text_inputs: List[TextInput] = []
    background_info: List[BackgroundInfo] = []

    class Config:
        orm_mode = True
