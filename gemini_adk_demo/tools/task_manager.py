from google.adk.tools import FunctionTool, ToolContext
from typing import Optional
import json
from ..shared_libraries.crud import create_task, update_task, list_tasks, task_to_dict, get_or_create_user
from ..shared_libraries.database import get_db

def create_tasks_impl(task_description: str, deadline: Optional[str], tool_context: ToolContext) -> str:
    """Creates a new task in the database.

    Args:
        task_description: The description of the task.
        deadline: The deadline for the task in ISO 8601 format.
        tool_context: The context of the tool.

    Returns:
        A JSON string with the result of the operation.
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        result = create_task(
            db=db,
            user=user,
            task_description=task_description,
            deadline=deadline
        )
        if isinstance(result, dict):
            return f"Error: {result.get('message', 'Could not create task.')}"
        if not result:
            return "Error: Could not create task."
        
        task_desc_preview = result.description[:75] + "..." if len(result.description) > 75 else result.description
        success_message = f"Task created successfully! ID: {result.id}, Description: '{task_desc_preview}'"
        if result.deadline:
            success_message += f", Deadline: {result.deadline.strftime('%Y-%m-%d %H:%M')}"
        return success_message
    finally:
        db.close()

def update_tasks_impl(task_id: int, task_description: Optional[str] = None, task_status: Optional[str] = None, deadline: Optional[str] = None, tool_context: ToolContext = None) -> str:
    """Updates an existing task in the database.

    Args:
        task_id: The ID of the task to update.
        task_description: The new description of the task.
        task_status: The new status of the task.
        deadline: The new deadline for the task.
        tool_context: The context of the tool.

    Returns:
        A JSON string with the result of the operation.
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        result = update_task(
            db=db,
            user=user,
            task_id=task_id,
            task_description=task_description,
            task_status=task_status,
            deadline=deadline
        )
        if not result or isinstance(result, dict):
            return f"Error: Could not update task."
            
        task_desc_preview = result.description[:75] + "..." if len(result.description) > 75 else result.description
        return f"Task {result.id} ('{task_desc_preview}') updated successfully. Status is now '{result.status}'."
    finally:
        db.close()

def list_tasks_impl(task_status: Optional[str], tool_context: ToolContext) -> str:
    """Lists tasks from the database.

    Args:
        task_status: The status of the tasks to list.
        tool_context: The context of the tool.

    Returns:
        A JSON string with the result of the operation.
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        result = list_tasks(
            db=db,
            user=user,
            task_status=task_status
        )
        return json.dumps([task_to_dict(t) for t in result])
    finally:
        db.close()

create_tasks_tool = FunctionTool(
    func=create_tasks_impl,
)

update_tasks_tool = FunctionTool(
    func=update_tasks_impl,
)

list_tasks_tool = FunctionTool(
    func=list_tasks_impl,
)
