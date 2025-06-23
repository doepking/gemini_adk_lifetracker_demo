import datetime

import sqlalchemy.orm
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Numeric, Boolean, ForeignKey, Float, JSON, Date, UniqueConstraint
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
    status = Column(String, default='open', nullable=False)
    @sqlalchemy.orm.validates('status')
    def validate_status(self, key, status):
        allowed_statuses = ['open', 'in_progress', 'completed']
        if status not in allowed_statuses:
            raise ValueError(f"Invalid status: {status}. Allowed values are: {', '.join(allowed_statuses)}")
        return status
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    deadline = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="tasks")

class NewsletterLog(Base):
    __tablename__ = 'newsletter_logs'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="newsletter_logs")
