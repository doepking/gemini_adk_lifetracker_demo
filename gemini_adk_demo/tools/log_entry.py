from google.adk.tools import FunctionTool as Tool, ToolContext
from typing import Optional
from ..shared_libraries.crud import add_log_entry_and_persist_impl, get_or_create_user
from ..shared_libraries.database import get_db

def add_log_entry_impl(text_input: str, category_suggestion: Optional[str], tool_context: ToolContext) -> str:
    """Appends a new log entry with a timestamp to the database.

    Args:
        text_input: The text of the log entry.
        category_suggestion: A suggestion for the category of the log entry.
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
        result = add_log_entry_and_persist_impl(
            db=db,
            text_input=text_input,
            user=user,
            category_suggestion=category_suggestion or "Note"
        )
        if not result:
            return "Error: Could not create log entry."
        
        content_preview = result.content[:100] + '...' if len(result.content) > 100 else result.content
        return f"Log entry {result.id} added successfully Content: '{content_preview}', Category: '{result.category}'"
    except Exception as e:
        return f"Error logging entry: {e}"
    finally:
        db.close()
 
add_log_entry_tool = Tool(
    func=add_log_entry_impl,
)
