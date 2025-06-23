import json
import datetime as dt
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import case

from .models import User, TextInput, BackgroundInfo, Task, NewsletterLog

def get_or_create_user(db, user_email: str, user_name: str, user_id: int = None) -> User:
    """Gets a user from the database or creates one if it doesn't exist."""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email, username=user_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def load_input_log(db, user_id):
    return db.query(TextInput).filter(TextInput.user_id == user_id).all()

def load_tasks(db, user_id):
    """Loads tasks for a user, with open/in_progress tasks first, then by creation date."""
    status_order = case(
        (Task.status.in_(['open', 'in_progress']), 0),
        else_=1
    )
    return db.query(Task).filter(Task.user_id == user_id).order_by(status_order, Task.created_at.desc()).all()

def load_background_info(db, user_id):
    background_info = db.query(BackgroundInfo).filter(BackgroundInfo.user_id == user_id).order_by(BackgroundInfo.created_at.desc()).first()
    if not background_info:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            background_info = BackgroundInfo(user_id=user_id, content={})
            db.add(background_info)
            db.commit()
            db.refresh(background_info)
    return background_info

def task_to_dict(task: Task) -> dict:
    """Converts a Task SQLAlchemy object to a dictionary."""
    if not task:
        return None
    return {
        "id": task.id,
        "user_id": task.user_id,
        "description": task.description,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }

def log_entry_to_dict(log_entry: TextInput) -> dict:
    """Converts a TextInput SQLAlchemy object to a dictionary."""
    if not log_entry:
        return None
    return {
        "id": log_entry.id,
        "user_id": log_entry.user_id,
        "content": log_entry.content,
        "category": log_entry.category,
        "created_at": log_entry.created_at.isoformat() if log_entry.created_at else None,
    }

def background_info_to_dict(background_info: BackgroundInfo) -> dict:
    """Converts a BackgroundInfo SQLAlchemy object to a dictionary."""
    if not background_info:
        return None
    return {
        "id": background_info.id,
        "user_id": background_info.user_id,
        "content": background_info.content,
        "created_at": background_info.created_at.isoformat() if background_info.created_at else None,
    }

def create_task(db, user: User, task_description: str, deadline: str = None):
    """Creates a new task in the database."""
    if not task_description:
        return {"status": "error", "message": "Task description is required to add a task."}
    
    task_deadline = None
    if deadline:
        try:
            task_deadline = dt.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            try:
                d = dt.datetime.strptime(deadline, "%Y-%m-%d").date()
                now_time = dt.datetime.now(dt.timezone.utc).time()
                task_deadline = dt.datetime.combine(d, now_time, tzinfo=dt.timezone.utc)
            except (ValueError, TypeError):
                return {"status": "error", "message": "Invalid deadline format. Please use ISO format or YYYY-MM-DD."}

    new_task = Task(
        user_id=user.id,
        description=task_description,
        status="open",
        deadline=task_deadline,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

def update_task(db, user: User, task_id: int, task_description: str = None, task_status: str = None, deadline: str = None):
    """Updates an existing task in the database."""
    if task_id is None:
        return {"status": "error", "message": "Task ID is required to update a task."}
    
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        return {"status": "error", "message": f"Task with ID {task_id} not found."}

    if task_status:
        task.status = task_status
        if task_status == "completed":
            task.completed_at = dt.datetime.now(dt.timezone.utc)
        else:
            task.completed_at = None

    if deadline:
        try:
            task.deadline = dt.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            try:
                d = dt.datetime.strptime(deadline, "%Y-%m-%d").date()
                now_time = dt.datetime.now(dt.timezone.utc).time()
                task.deadline = dt.datetime.combine(d, now_time, tzinfo=dt.timezone.utc)
            except (ValueError, TypeError):
                return {"status": "error", "message": "Invalid deadline format. Please use ISO format or YYYY-MM-DD."}
    
    if task_description:
        task.description = task_description

    db.commit()
    db.refresh(task)
    return task

def list_tasks(db, user: User, task_status: str = None):
    """Lists tasks from the database."""
    query = db.query(Task).filter(Task.user_id == user.id)
    if task_status and task_status in ["open", "in_progress", "completed"]:
        query = query.filter(Task.status == task_status)

    status_order = case(
        (Task.status == 'in_progress', 0),
        (Task.status == 'open', 1),
        (Task.status == 'completed', 2),
        else_=3
    )
    tasks = query.order_by(status_order, Task.created_at.desc()).all()
    return tasks

def deep_update(source, overrides):
    """
    Recursively update a dictionary.
    """
    for key, value in overrides.items():
        if isinstance(value, dict) and value:
            existing_dict = source.get(key, {})
            if not isinstance(existing_dict, dict):
                existing_dict = {}
            source[key] = deep_update(existing_dict, value)
        elif isinstance(value, list) and value:
            if key not in source or not isinstance(source.get(key), list):
                source[key] = []
            source[key].extend(item for item in value if item not in source[key])
        else:
            source[key] = value
    return source

def add_log_entry_and_persist_impl(db, text_input: str, user: User, category_suggestion: str = None):
    """
    Core logic to process and log text input to the database.
    """
    if user is None:
        return None

    log_entry = TextInput(
        user_id=user.id,
        content=text_input,
        category=category_suggestion if category_suggestion else "Note",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

def update_input_log(db, user: User, log_list: list):
    """Updates a list of text inputs in the database."""
    updated_logs = []
    for log_data in log_list:
        log_id = log_data.id
        if not log_id:
            continue
        
        log = db.query(TextInput).filter(TextInput.id == log_id, TextInput.user_id == user.id).first()
        if log:
            log.content = log_data.content
            log.category = log_data.category
            updated_logs.append(log)
    
    db.commit()
    for log in updated_logs:
        db.refresh(log)
    return {"status": "success", "message": "Logs updated successfully."}

def update_background_info_and_persist_impl(db, background_update_json: str, user: User, replace: bool = False):
    """
    Core logic to update background information in the database.
    If 'replace' is True, the entire content is overwritten.
    Otherwise, a deep update is performed.
    """
    if user is None:
        return None

    try:
        update_data = json.loads(background_update_json)
        
        background_info = db.query(BackgroundInfo).filter(BackgroundInfo.user_id == user.id).order_by(BackgroundInfo.created_at.desc()).first()
        if not background_info:
            background_info = BackgroundInfo(user_id=user.id, content={})
            db.add(background_info)

        if replace:
            updated_content = update_data
        else:
            current_content = (background_info.content or {}).copy()
            updated_content = deep_update(current_content, update_data)
        
        background_info.content = updated_content
        flag_modified(background_info, "content")
        db.commit()
        db.refresh(background_info)
        
        return background_info

    except json.JSONDecodeError:
        return None
    except Exception as e:
        db.rollback()
        return None

def purge_user_data(db, user_id: int):
    """
    Deletes all data associated with a user.
    """
    try:
        # Delete all tasks, text inputs, and background info for the user.
        db.query(NewsletterLog).filter(NewsletterLog.user_id == user_id).delete()
        db.query(Task).filter(Task.user_id == user_id).delete()
        db.query(TextInput).filter(TextInput.user_id == user_id).delete()
        db.query(BackgroundInfo).filter(BackgroundInfo.user_id == user_id).delete()
        
        # After deleting associated data, delete the user.
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            db.delete(user)
        
        db.commit()
        return {"status": "success", "message": f"All data for user {user_id} has been purged."}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"An error occurred while purging data for user {user_id}."}
