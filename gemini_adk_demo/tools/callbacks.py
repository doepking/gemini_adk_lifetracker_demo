from google.adk.agents.callback_context import CallbackContext
from datetime import datetime
import json
import os
import logging
import time
from typing import Optional
from google.cloud import logging as google_cloud_logging
from ..database import get_db
from ..crud import (
    get_or_create_user,
    load_background_info,
    load_tasks,
    load_input_log,
    background_info_to_dict,
    count_recent_newsletters,
)
from .newsletter_sender import send_daily_briefing
from google.adk.models import LlmRequest

OUTPUT_DIR = "_output"

# Adjust these values to limit the rate at which the agent
# queries the LLM API.
RATE_LIMIT_SECS = 60
RPM_QUOTA = 10


def rate_limit_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """Callback function that implements a query rate limit.

    Args:
      callback_context: A CallbackContext object representing the active
              callback context.
      llm_request: A LlmRequest object representing the active LLM request.
    """
    now = time.time()
    if "timer_start" not in callback_context.state:
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
        logging.debug(
            "rate_limit_callback [timestamp: %i, req_count: 1, " "elapsed_secs: 0]",
            now,
        )
        return

    request_count = callback_context.state["request_count"] + 1
    elapsed_secs = now - callback_context.state["timer_start"]
    logging.debug(
        "rate_limit_callback [timestamp: %i, request_count: %i," " elapsed_secs: %i]",
        now,
        request_count,
        elapsed_secs,
    )

    if request_count > RPM_QUOTA:
        delay = RATE_LIMIT_SECS - elapsed_secs + 1
        if delay > 0:
            logging.debug("Sleeping for %i seconds", delay)
            time.sleep(delay)
        callback_context.state["timer_start"] = now
        callback_context.state["request_count"] = 1
    else:
        callback_context.state["request_count"] = request_count

    return


def save_report_as_markdown_impl(report_content: str) -> str:
    """Saves the generated report content to a markdown file."""
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Final_Verdict_{timestamp}.md"

        filepath = os.path.join(OUTPUT_DIR, filename)

        with open(filepath, "w") as f:
            f.write(report_content)

        return f"Report saved successfully to {filepath}"
    except Exception as e:
        return f"Error saving report: {e}"


def load_user_data(callback_context: CallbackContext):
    """
    Loads user data from the database into the session state before the agent runs.
    """
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger("adk-callbacks")
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    current_weekday_str = now.strftime("%A")

    user_id = callback_context.state.get("user_id")
    user_email = callback_context.state.get("user_email")
    user_name = callback_context.state.get("user_name")

    logger.log_text(
        f"load_user_data: Received from callback_context.state - user_id: {user_id}, user_email: {user_email}, user_name: {user_name}",
        severity="INFO",
    )

    db = next(get_db())
    user = None

    if user_id:
        user = get_or_create_user(db, user_id=user_id)
    elif user_email:
        user = get_or_create_user(db, user_email=user_email, user_name=user_name)

    if not user:
        logger.log_text(
            "load_user_data: No user could be identified, falling back to default.",
            severity="WARNING",
        )
        user = get_or_create_user(db, "default_user@example.com", "Default User")

    logger.log_text(
        f"load_user_data: Final user object: {user.id}, {user.email}", severity="INFO"
    )

    background_info = load_background_info(db, user.id)
    background_info_dict = background_info_to_dict(background_info)
    current_bg_info_str = (
        json.dumps(background_info_dict["content"])
        if background_info_dict and "content" in background_info_dict
        else "{}"
    )

    tasks = load_tasks(db, user.id)
    tasks.sort(key=lambda x: x.created_at, reverse=True)
    tasks_preview = [
        f"ID: {task.id}, Desc: {task.description}, Status: {task.status}, Deadline: {task.deadline}, Created: {task.created_at.strftime('%Y-%m-%d %H:%M')}"
        for task in tasks[:20]
    ]
    tasks_str = (
        "\n- ".join(tasks_preview) if tasks_preview else "No open or in-progress tasks."
    )

    logs = load_input_log(db, user.id)
    logs.sort(key=lambda x: x.created_at, reverse=True)
    recent_logs_preview = []
    for log in logs[:50]:
        timestamp = (
            log.created_at.strftime("%Y-%m-%d %H:%M:%S (%A)")
            if log.created_at
            else "No timestamp"
        )
        content_preview = (
            log.content[:500] + "..." if len(log.content) > 500 else log.content
        )
        recent_logs_preview.append(f"[{timestamp}] {content_preview}")
    recent_logs_str = (
        "\n- ".join(recent_logs_preview) if recent_logs_preview else "No recent logs."
    )

    context = {
        "current_time_str": current_time_str,
        "current_weekday_str": current_weekday_str,
        "current_bg_info_str": current_bg_info_str,
        "tasks_str": tasks_str,
        "recent_logs_str": recent_logs_str,
        "user_id": user.id,
        "user_email": user.email,
        "user_name": user.username,
    }

    callback_context.state.update(context)


def save_final_verdict(callback_context: CallbackContext):
    """Saves the final verdict to a markdown file."""
    final_verdict = callback_context.state.get("final_insight_report")
    if final_verdict:
        save_report_as_markdown_impl(final_verdict)


def after_tool_callback(tool, args, tool_context, tool_response):
    """Passes the tool response directly to the next step."""
    logging_client = google_cloud_logging.Client()
    logger = logging_client.logger("adk-callbacks")
    logger.log_text(
        f"after_tool_callback received response: '{tool_response}' from tool: {tool.name}",
        severity="INFO",
    )

    # The tool_response is now a simple string (e.g., "Success: Task created.")
    # or a JSON string for list_tasks. We will just pass it along.
    # The agent's prompt will guide it on how to use this string.
    return tool_response


def load_user_data_after_tool_callback(tool, args, tool_context, tool_response):
    """Loads user data after a tool call."""
    load_user_data(tool_context)
    return tool_response


def return_final_insight_report(
    callback_context: CallbackContext,
) -> Optional[str]:
    """Returns the final insight report as the agent's response."""
    final_report = callback_context.state.get("final_insight_report")
    if final_report:
        return final_report
    return None


def send_newsletter_callback(callback_context: CallbackContext):
    """
    Callback to send the newsletter after the insights engine has run.
    """
    logging.info("--- send_newsletter_callback TRIGGERED ---")
    db = next(get_db())
    user_id = callback_context.state.get("user_id")
    user_email = callback_context.state.get("user_email")
    user_name = callback_context.state.get("user_name")
    final_insight_report = callback_context.state.get("final_insight_report")

    logging.info(
        f"Callback data: user_id={user_id}, user_email={user_email}, user_name={user_name}"
    )
    logging.info(f"Callback final_insight_report: {final_insight_report}")

    if final_insight_report:
        # Rate-limiting check
        if count_recent_newsletters(db, user_id) >= 3:
            logging.info(
                f"Newsletter limit of 3 reached today for {user_email}. Skipping."
            )
            return

        logging.info("All necessary data is present. Calling send_daily_briefing.")
        send_daily_briefing(
            final_insight_report=final_insight_report,
            tool_context=callback_context,
        )
    else:
        logging.error(
            "Could not send newsletter due to missing data in callback_context.state. One of the required fields is None."
        )
