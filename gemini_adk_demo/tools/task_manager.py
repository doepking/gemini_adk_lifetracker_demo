from google.adk.tools import FunctionTool, ToolContext
from typing import Optional
from ..crud import (
    create_tasks_tool as create_tasks_crud_tool,
    update_tasks_tool as update_tasks_crud_tool,
    list_tasks_tool as list_tasks_crud_tool,
    get_or_create_user,
)
from ..database import get_db


def create_new_task_for_user(
    task_description: str,
    deadline: Optional[str] = None,
    tool_context: ToolContext = None,
) -> dict:
    """Creates a new task in the database and returns the task details.

    This tool should be used when a user wants to create a new task. It can infer the task description and deadline from the user's input.

    Args:
        task_description: The full, detailed description of the task.
        deadline: The deadline for the task in ISO 8601 format (e.g., "2025-12-31T23:59:59Z").
        tool_context: The context of the tool, containing user information.

    Returns:
        A dictionary containing the details of the created task or an error message.
        Example (success): {"status": "success", "id": 123, "description": "Buy milk", ...}
        Example (error): {"status": "error", "message": "Could not create task."}
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        return create_tasks_crud_tool(
            db=db, user=user, task_description=task_description, deadline=deadline
        )
    finally:
        db.close()


def update_existing_task_for_user(
    task_id: int,
    task_description: Optional[str] = None,
    task_status: Optional[str] = None,
    deadline: Optional[str] = None,
    tool_context: ToolContext = None,
) -> dict:
    """Updates an existing task with a new description, status, or deadline.

    This tool should be used to modify an existing task. The user can specify the task by its ID and provide the updated information.

    Args:
        task_id: The unique identifier of the task to update.
        task_description: The new, full description for the task.
        task_status: The new status for the task (e.g., "open", "in_progress", "completed").
        deadline: The new deadline for the task in ISO 8601 format.
        tool_context: The context of the tool, containing user information.

    Returns:
        A dictionary containing the details of the updated task or an error message.
        Example (success): {"status": "success", "id": 123, "description": "Buy milk", "status": "completed", ...}
        Example (error): {"status": "error", "message": "Task not found."}
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        return update_tasks_crud_tool(
            db=db,
            user=user,
            task_id=task_id,
            task_description=task_description,
            task_status=task_status,
            deadline=deadline,
        )
    finally:
        db.close()


def list_all_tasks_for_user(
    task_status: Optional[str] = None, tool_context: ToolContext = None
) -> dict:
    """Lists all tasks for the user, optionally filtering by status.

    This tool retrieves a list of the user's tasks. It can be used to show all tasks or filter them by their status.

    Args:
        task_status: An optional status to filter the tasks by (e.g., "open", "in_progress", "completed").
        tool_context: The context of the tool, containing user information.

    Returns:
        A dictionary containing the list of tasks.
        Example: {"status": "success", "tasks": [{"id": 123, "description": "Buy milk", "status": "open", ...}]}
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        return list_tasks_crud_tool(db=db, user=user, task_status=task_status)
    finally:
        db.close()


create_tasks_tool = FunctionTool(
    func=create_new_task_for_user,
)

update_tasks_tool = FunctionTool(
    func=update_existing_task_for_user,
)

list_tasks_tool = FunctionTool(
    func=list_all_tasks_for_user,
)
