import datetime

import sqlalchemy.orm
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    JSON,
    Date,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    text_inputs = relationship("TextInput", back_populates="user")
    background_infos = relationship("BackgroundInfo", back_populates="user")
    newsletter_logs = relationship("NewsletterLog", back_populates="user")
    tasks = relationship("Task", back_populates="user")

class TextInput(Base):
    __tablename__ = "text_inputs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    category = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="text_inputs")

class BackgroundInfo(Base):
    __tablename__ = "background_info"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="background_infos")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    description = Column(Text)
    status = Column(String, default="open", nullable=False)

    @sqlalchemy.orm.validates("status")
    def validate_status(self, key, status):
        allowed_statuses = ["open", "in_progress", "completed"]
        if status not in allowed_statuses:
            raise ValueError(
                f"Invalid status: {status}. Allowed values are: {', '.join(allowed_statuses)}"
            )
        return status

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deadline = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tasks")

class NewsletterLog(Base):
    __tablename__ = "newsletter_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    newsletter_category = Column(
        String(100), nullable=False, index=True
    )  # e.g., "personalized_daily_brief"

    content_text = Column(Text, nullable=False)  # The actual text content sent
    content_hash = Column(
        String(64), nullable=False, index=True
    )  # SHA256 hash of content_text for quick checks

    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    opened_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Updated by tracking pixel

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="newsletter_logs")

    # Unique constraint to prevent sending the exact same newsletter (category + content_hash) to the same user twice
    # However, the primary goal is to log what was sent and use previous content for context.
    # A strict unique constraint on (user_email, newsletter_category, content_hash) might be too restrictive
    # if we intend to resend *similar* but slightly different content.
    # The check for "don't contact the same user twice with the same newsletter category"
    # should likely be handled in the sending logic by checking recent logs for that category,
    # rather than a strict DB constraint on the *exact same content hash*.
    # For now, we'll rely on application logic to manage resends.

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "newsletter_category",
            "content_hash",
            name="_user_category_content_uc",
        ),
    )

class NewsletterPreference(Base):
    __tablename__ = "newsletter_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(255), unique=True, nullable=False, index=True)
    subscribed = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    subscribed_at = Column(DateTime(timezone=True), server_default=func.now())
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("user_email"),)

class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(
        String(255), ForeignKey("users.email"), nullable=False, index=True
    )
    metric_date = Column(Date, nullable=False)
    morning_mood_subjective = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship(
        "User",
        back_populates="daily_metrics",
        primaryjoin="User.email == DailyMetric.user_email",
    )

User.daily_metrics = relationship(
    "DailyMetric",
    order_by=DailyMetric.metric_date.desc(),
    back_populates="user",
    primaryjoin="User.email == DailyMetric.user_email",
)
