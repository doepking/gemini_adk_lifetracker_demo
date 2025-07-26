from google.adk.tools import FunctionTool as Tool, ToolContext
from typing import Optional
from ..crud import add_log_entry_tool as add_log_entry_crud_tool, get_or_create_user
from ..database import get_db


def add_new_log_entry_for_user(
    text_input: str, category_suggestion: Optional[str], tool_context: ToolContext
) -> dict:
    """Appends a new log entry with a timestamp to the database.

    This tool should be used for any user input that represents a thought, action, or observation.

    Args:
        text_input: The text of the log entry.
        category_suggestion: A suggestion for the category of the log entry (e.g., "Note", "Action", "Decision").
        tool_context: The context of the tool, containing user information.

    Returns:
        A dictionary with the status of the operation.
        Example (success): {"status": "success", "message": "Log entry added."}
        Example (error): {"status": "error", "message": "User not found."}
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        result = add_log_entry_crud_tool(
            db=db,
            text_input=text_input,
            user=user,
            category_suggestion=category_suggestion,
        )
        tool_context.actions.skip_summarization = True
        return result
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}
    finally:
        db.close()


add_log_entry_tool = Tool(
    func=add_new_log_entry_for_user,
)
