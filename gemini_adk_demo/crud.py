import json
import datetime as dt
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import case, func

from .models import (
    User,
    TextInput,
    BackgroundInfo,
    Task,
    NewsletterLog,
    NewsletterPreference,
    DailyMetric,
)


def get_or_create_user(
    db, user_email: str = None, user_name: str = None, user_id: int = None
) -> User:
    """Gets a user from the database or creates one if it doesn't exist."""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    if not user_email:
        return None  # Can't create user without email

    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        user = User(email=user_email, username=user_name or "Undefined")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def load_input_log(db, user_id):
    return db.query(TextInput).filter(TextInput.user_id == user_id).all()


def load_tasks(db, user_id):
    """Loads tasks for a user, with open/in_progress tasks first, then by creation date."""
    status_order = case((Task.status.in_(["open", "in_progress"]), 0), else_=1)
    return (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .order_by(status_order, Task.created_at.desc())
        .all()
    )

def load_background_info(db, user_id):
    background_info = (
        db.query(BackgroundInfo)
        .filter(BackgroundInfo.user_id == user_id)
        .order_by(BackgroundInfo.created_at.desc())
        .first()
    )
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
        "created_at": (
            log_entry.created_at.isoformat() if log_entry.created_at else None
        ),
    }

def background_info_to_dict(background_info: BackgroundInfo) -> dict:
    """Converts a BackgroundInfo SQLAlchemy object to a dictionary."""
    if not background_info:
        return None
    return {
        "id": background_info.id,
        "user_id": background_info.user_id,
        "content": background_info.content,
        "created_at": (
            background_info.created_at.isoformat()
            if background_info.created_at
            else None
        ),
    }

def create_tasks_tool(
    db, user: User, task_description: str, deadline: str = None
) -> dict:
    """
    Creates a new task in the database and returns a dictionary with the result.
    Args:
        db: The database session.
        user: The user to create the task for.
        task_description: The description of the task.
        deadline: The deadline for the task in ISO 8601 format.
    Returns:
        A dictionary with the result of the operation.
    """
    if not task_description:
        return {
            "status": "error",
            "message": "Task description is required to add a task.",
        }

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
                return {
                    "status": "error",
                    "message": "Invalid deadline format. Please use ISO format or YYYY-MM-DD.",
                }

    new_task = Task(
        user_id=user.id,
        description=task_description,
        status="open",
        deadline=task_deadline,
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"status": "success", "task": task_to_dict(new_task)}

def update_tasks_tool(
    db,
    user: User,
    task_id: int,
    task_description: str = None,
    task_status: str = None,
    deadline: str = None,
) -> dict:
    """
    Updates an existing task in the database and returns a dictionary with the result.

    Args:
        db: The database session.
        user: The user to update the task for.
        task_id: The ID of the task to update.
        task_description: The new description of the task.
        task_status: The new status of the task.
        deadline: The new deadline for the task.

    Returns:
        A dictionary with the result of the operation.
    """
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

    if deadline is not None:
        if isinstance(deadline, dt.datetime):
            task.deadline = deadline
        elif isinstance(deadline, str):
            try:
                task.deadline = dt.datetime.fromisoformat(
                    deadline.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                try:
                    d = dt.datetime.strptime(deadline, "%Y-%m-%d").date()
                    now_time = dt.datetime.now(dt.timezone.utc).time()
                    task.deadline = dt.datetime.combine(
                        d, now_time, tzinfo=dt.timezone.utc
                    )
                except (ValueError, TypeError):
                    return {
                        "status": "error",
                        "message": "Invalid deadline format. Please use ISO format or YYYY-MM-DD.",
                    }
        else:
            return {
                "status": "error",
                "message": "Invalid deadline type. Must be a datetime object or a string.",
            }

    if task_description:
        task.description = task_description

    db.commit()
    db.refresh(task)
    return {
        "status": "success",
        "message": f"Task {task_id} updated successfully.",
        "task": task_to_dict(task),
    }

def update_tasks_tool_bulk(db, user: User, tasks: list) -> dict:
    """
    Updates a list of tasks in the database, including deletions,
    and returns a dictionary with the result.

    Args:
        db: The database session.
        user: The user to update tasks for.
        tasks: A list of task dictionaries with the updates.

    Returns:
        A dictionary with the result of the operation.
    """
    updated_count = 0
    deleted_count = 0

    task_ids_from_frontend = {task.get("id") for task in tasks if task.get("id")}

    # Delete tasks that are in the DB but not in the frontend list
    tasks_to_delete = (
        db.query(Task)
        .filter(Task.user_id == user.id, ~Task.id.in_(task_ids_from_frontend))
        .all()
    )

    for task in tasks_to_delete:
        db.delete(task)
        deleted_count += 1

    # Update existing tasks
    for task_data in tasks:
        task_id = task_data.get("id")
        if not task_id:
            continue

        task = (
            db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
        )
        if not task:
            continue

        is_updated = False
        if "description" in task_data and task.description != task_data["description"]:
            task.description = task_data["description"]
            is_updated = True

        if "status" in task_data and task.status != task_data["status"]:
            task.status = task_data["status"]
            if task_data["status"] == "completed":
                task.completed_at = dt.datetime.now(dt.timezone.utc)
            else:
                task.completed_at = None
            is_updated = True

        if "deadline" in task_data:
            deadline_data = task_data["deadline"]
            new_deadline = None
            if isinstance(deadline_data, dt.datetime):
                new_deadline = deadline_data
            elif isinstance(deadline_data, str) and deadline_data:
                try:
                    # Pydantic might have already converted it, but handle string just in case
                    new_deadline = dt.datetime.fromisoformat(
                        deadline_data.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    new_deadline = None

            # Ensure comparison is between two timezone-aware datetime objects
            task_deadline_utc = (
                task.deadline.astimezone(dt.timezone.utc) if task.deadline else None
            )
            new_deadline_utc = (
                new_deadline.astimezone(dt.timezone.utc) if new_deadline else None
            )

            if task_deadline_utc != new_deadline_utc:
                task.deadline = new_deadline
                is_updated = True

        if is_updated:
            updated_count += 1

    db.commit()

    if deleted_count > 0 and updated_count > 0:
        message = f"{deleted_count} task(s) deleted and {updated_count} task(s) updated successfully."
    elif deleted_count > 0:
        message = f"{deleted_count} task(s) deleted successfully."
    elif updated_count > 0:
        message = f"{updated_count} task(s) updated successfully."
    else:
        message = "No changes detected."

    return {"status": "success", "message": message}

def list_tasks_tool(db, user: User, task_status: str = None) -> dict:
    """
    Lists tasks from the database and returns a dictionary.

    Args:
        db: The database session.
        user: The user to list tasks for.
        task_status: The status of the tasks to list.

    Returns:
        A dictionary with the list of tasks.
    """
    query = db.query(Task).filter(Task.user_id == user.id)
    if task_status and task_status in ["open", "in_progress", "completed"]:
        query = query.filter(Task.status == task_status)

    status_order = case(
        (Task.status == "in_progress", 0),
        (Task.status == "open", 1),
        (Task.status == "completed", 2),
        else_=3,
    )
    tasks = query.order_by(status_order, Task.created_at.desc()).all()
    return {"status": "success", "tasks": [task_to_dict(task) for task in tasks]}

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

def add_log_entry_tool(
    db, text_input: str, user: User, category_suggestion: str = None
) -> dict:
    """
    Appends a new log entry with a timestamp to the database.

    Args:
        db: The database session.
        text_input: The text of the log entry.
        user: The user to add the log entry for.
        category_suggestion: A suggestion for the category of the log entry.

    Returns:
        A dictionary with the status and the created log entry.
    """
    if user is None:
        return {"status": "error", "message": "User not found."}

    log_entry = TextInput(
        user_id=user.id,
        content=text_input,
        category=category_suggestion if category_suggestion else "Note",
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return {
        "status": "success",
        "message": "Log entry added.",
        "log_entry": log_entry_to_dict(log_entry),
    }

def update_input_log(db, user: User, log_list: list):
    """Updates a list of text inputs in the database."""
    updated_logs = []
    deleted_logs_count = 0
    log_ids_from_frontend = {log.id for log in log_list if log.id}

    # Delete logs that are not in the frontend list
    logs_to_delete = (
        db.query(TextInput)
        .filter(TextInput.user_id == user.id, ~TextInput.id.in_(log_ids_from_frontend))
        .all()
    )
    deleted_logs_count = len(logs_to_delete)
    for log in logs_to_delete:
        db.delete(log)

    for log_data in log_list:
        log_id = log_data.id
        if not log_id:
            continue

        log = (
            db.query(TextInput)
            .filter(TextInput.id == log_id, TextInput.user_id == user.id)
            .first()
        )
        if log:
            if log.content != log_data.content or log.category != log_data.category:
                log.content = log_data.content
                log.category = log_data.category
                updated_logs.append(log)

    db.commit()
    refreshed_logs = []
    for log in updated_logs:
        db.refresh(log)
        refreshed_logs.append(log_entry_to_dict(log))

    if deleted_logs_count > 0 and len(refreshed_logs) > 0:
        message = f"{deleted_logs_count} log(s) deleted and {len(refreshed_logs)} log(s) updated successfully."
    elif deleted_logs_count > 0:
        message = f"{deleted_logs_count} log(s) deleted successfully."
    else:
        message = f"{len(refreshed_logs)} log(s) updated successfully."

    return {"status": "success", "message": message, "updated_logs": refreshed_logs}

def update_background_info_tool(
    db, background_update_json: str, user: User, replace: bool = False
) -> dict:
    """
    Updates the user's background information in the database.

    Args:
        db: The database session.
        background_update_json: A JSON string with the background information to update.
        user: The user to update the background info for.
        replace: Whether to replace the entire content or perform a deep update.

    Returns:
        A dictionary with the result of the operation.
    """
    if user is None:
        return {"status": "error", "message": "User not found."}

    try:
        update_data = json.loads(background_update_json)

        background_info = (
            db.query(BackgroundInfo)
            .filter(BackgroundInfo.user_id == user.id)
            .order_by(BackgroundInfo.created_at.desc())
            .first()
        )
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

        return {
            "status": "success",
            "message": "Background information updated successfully.",
            "updated_info": background_info_to_dict(background_info),
        }

    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON format."}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}

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
        return {
            "status": "success",
            "message": f"All data for user {user_id} has been purged.",
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"An error occurred while purging data for user {user_id}.",
        }

# --- NewsletterPreference CRUD ---

def get_newsletter_preference(db, user_email: str):
    """
    Retrieves a newsletter preference by user email.
    Performs a case-insensitive search for the email.
    """
    return (
        db.query(NewsletterPreference)
        .filter(func.lower(NewsletterPreference.user_email) == func.lower(user_email))
        .first()
    )

def create_newsletter_preference(db, preference):
    """
    Creates a new newsletter preference or updates an existing one to be subscribed.
    If a preference for the email exists, it marks it as subscribed and updates timestamps.
    """
    db_preference = get_newsletter_preference(db, user_email=preference.user_email)
    if db_preference:
        db_preference.subscribed = True
        db_preference.subscribed_at = dt.datetime.utcnow()
        db_preference.unsubscribed_at = None
    else:
        db_preference = NewsletterPreference(
            user_email=preference.user_email,
            subscribed=True,
            subscribed_at=dt.datetime.utcnow(),
        )
        db.add(db_preference)
    db.commit()
    db.refresh(db_preference)
    return db_preference

def update_newsletter_preference(db, user_email: str, subscribed: bool):
    """
    Updates the subscription status of an existing newsletter preference.
    Sets subscribed_at or unsubscribed_at accordingly.
    """
    db_preference = get_newsletter_preference(db, user_email=user_email)
    if db_preference:
        db_preference.subscribed = subscribed
        if subscribed:
            db_preference.subscribed_at = dt.datetime.utcnow()
            db_preference.unsubscribed_at = None
        else:
            db_preference.unsubscribed_at = dt.datetime.utcnow()
        db.commit()
        db.refresh(db_preference)
    return db_preference

# --- DailyMetric CRUD ---

def get_daily_metric(db, user_email: str, metric_date):
    """
    Retrieves a daily metric entry for a specific user and date.
    Email search is case-insensitive.
    """
    return (
        db.query(DailyMetric)
        .filter(
            func.lower(DailyMetric.user_email) == func.lower(user_email),
            DailyMetric.metric_date == metric_date,
        )
        .first()
    )

def get_daily_metrics_for_user(db, user_email: str, skip: int = 0, limit: int = 100):
    """
    Retrieves all daily metric entries for a specific user, with pagination.
    Email search is case-insensitive.
    """
    return (
        db.query(DailyMetric)
        .filter(func.lower(DailyMetric.user_email) == func.lower(user_email))
        .order_by(DailyMetric.metric_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def create_or_update_daily_metric(db, metric):
    """
    Creates a new daily metric entry or updates an existing one for the given user and date.
    """
    db_metric = get_daily_metric(
        db, user_email=metric.user_email, metric_date=metric.metric_date
    )

    if db_metric:
        update_data = metric.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(db_metric, key):
                setattr(db_metric, key, value)
    else:
        db_metric = DailyMetric(**metric.model_dump())
        db.add(db_metric)

    db.commit()
    db.refresh(db_metric)
    return db_metric

def update_sent_newsletter_log_opened_at(db, log_id: int):
    """
    Updates the 'opened_at' timestamp for a sent newsletter log.
    """
    log_entry = db.query(NewsletterLog).filter(NewsletterLog.id == log_id).first()
    if log_entry and not log_entry.opened_at:
        log_entry.opened_at = dt.datetime.utcnow()
        db.commit()
        db.refresh(log_entry)
        return log_entry
    return None

def count_recent_newsletters(db, user_id: int) -> int:
    """
    Counts the number of newsletters a user has received in the last 24 hours.
    """
    twenty_four_hours_ago = dt.datetime.utcnow() - dt.timedelta(hours=24)
    return (
        db.query(NewsletterLog)
        .filter(
            NewsletterLog.user_id == user_id,
            NewsletterLog.sent_at >= twenty_four_hours_ago,
        )
        .count()
    )
