from google.adk.tools import FunctionTool, ToolContext
from ..crud import (
    update_background_info_tool as update_background_info_crud_tool,
    get_or_create_user,
)
from ..database import get_db


def update_user_background_information(
    background_update_json: str, tool_context: ToolContext
) -> dict:
    """Updates the user's background information in the database.

    This tool should be used when the user provides personal information like name, age, goals, values, or challenges.

    Args:
        background_update_json: A JSON string with the background information to update.
        tool_context: The context of the tool, containing user information.

    Returns:
        A dictionary containing the updated background information or an error message.
        Example (success): {"status": "success", "content": {"location": "San Francisco"}, ...}
        Example (error): {"status": "error", "message": "Invalid JSON format."}
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)

        return update_background_info_crud_tool(
            db=db, background_update_json=background_update_json, user=user
        )
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}
    finally:
        db.close()


update_background_info_tool = FunctionTool(
    func=update_user_background_information,
)
