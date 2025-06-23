from google.adk.tools import FunctionTool, ToolContext
from ..shared_libraries.crud import update_background_info_and_persist_impl, get_or_create_user
from ..shared_libraries.database import get_db

def update_background_info_impl(background_update_json: str, tool_context: ToolContext) -> str:
    """Updates the user's background information in the database.

    Args:
        background_update_json: A JSON string with the background information to update.
        tool_context: The context of the tool.

    Returns:
        A string with the result of the operation.
    """
    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = get_or_create_user(db, user_email, user_name, user_id)
        
        result = update_background_info_and_persist_impl(
            db=db,
            background_update_json=background_update_json,
            user=user
        )
        if not result:
            return "Error: Could not update background information."
        return f"Success: Background information updated for user {result.user_id}."
    except Exception as e:
        return f"Error updating background info: {e}"
    finally:
        db.close()

update_background_info_tool = FunctionTool(
    func=update_background_info_impl,
)
