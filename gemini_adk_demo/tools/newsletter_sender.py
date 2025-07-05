import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import asyncio
import hashlib
import re
import uuid
from google.adk.tools import FunctionTool as Tool, ToolContext
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.genai.types import Content, Part

from .. import crud, models
from ..database import get_db

logger = logging.getLogger(__name__)

# Load environment variables for email
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = os.environ.get("SMTP_PORT")
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
NEWSLETTER_SENDER_EMAIL = os.environ.get("NEWSLETTER_SENDER_EMAIL")
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
SUBSCRIPTION_SECRET_KEY = os.environ.get("SUBSCRIPTION_SECRET_KEY")


async def send_email_async(subject: str, html_body: str, to_email: str):
    if not all(
        [SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, NEWSLETTER_SENDER_EMAIL]
    ):
        logger.error(
            f"Email server configuration is incomplete. Skipping email to {to_email}."
        )
        return False

    def _send_sync():
        message = MIMEMultipart("alternative")
        message["From"] = f"The Opportunity Architect <{NEWSLETTER_SENDER_EMAIL}>"
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(html_body, "html"))

        try:
            port = int(SMTP_PORT)
            if port == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, port) as server:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(
                        NEWSLETTER_SENDER_EMAIL, to_email, message.as_string()
                    )
            else:
                with smtplib.SMTP(SMTP_HOST, port) as server:
                    if port == 587:
                        server.starttls()
                    server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(
                        NEWSLETTER_SENDER_EMAIL, to_email, message.as_string()
                    )
            return True
        except Exception as e:
            logger.error(
                f"Failed to send newsletter email to {to_email}: {e}", exc_info=True
            )
            return False

    try:
        success = await asyncio.to_thread(_send_sync)
        return success
    except Exception as e:
        logger.error(f"Error in send_email_async for {to_email}: {e}", exc_info=True)
        return False


def generate_newsletter_html_content(
    user_email: str, user_name: str | None, content: str, log_id: int
) -> str:
    insights_and_nudges_html = ""
    motivational_quote_text = ""

    # Safeguard: Convert markdown to HTML first, as the LLM might mix them.
    content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)
    content = re.sub(r"\_(.*?)\_", r"<em>\1</em>", content)
    content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)

    # This logic handles cases where the quote is in an `<em>` tag,
    # optionally wrapped in an `<li>` tag, at the end of the content.
    # Find the last `<em>` tag, which contains the quote.
    last_em_start = content.rfind("<em>")

    if last_em_start != -1:
        # Check if the quote is wrapped in an `<li>` tag.
        # We search for the `<li>` tag just before the `<em>` tag.
        last_li_start = content.rfind("<li>", 0, last_em_start)

        # Determine the starting point of the quote section.
        quote_section_start = last_em_start
        if last_li_start != -1:
            # Check if the `<li>` tag is closely followed by the `<em>` tag.
            substring_between = content[last_li_start + 4 : last_em_start].strip()
            if not substring_between:  # No other content between <li> and <em>
                quote_section_start = last_li_start

        # Separate the insights from the quote section.
        insights_and_nudges_html = content[:quote_section_start].strip()

        # Extract the quote text from between the `<em>` and `</em>` tags.
        quote_section = content[last_em_start:]
        last_em_end = quote_section.find("</em>")
        if last_em_end != -1:
            motivational_quote_text = quote_section[4:last_em_end].strip()
        else:
            # Fallback if `</em>` is not found after `<em>`.
            motivational_quote_text = quote_section[4:].strip()
    else:
        # Fallback if no `<em>` tag is found.
        insights_and_nudges_html = content
        motivational_quote_text = "Stay positive, work hard, and make it happen."

    unsubscribe_token = ""
    if SUBSCRIPTION_SECRET_KEY:
        unsubscribe_token = hashlib.sha256(
            f"{user_email}{SUBSCRIPTION_SECRET_KEY}".encode()
        ).hexdigest()

    unsubscribe_url = (
        f"{API_BASE_URL}/newsletter/unsubscribe/{user_email}/{unsubscribe_token}"
        if unsubscribe_token
        else "#"
    )

    today_iso_date = datetime.utcnow().date().isoformat()

    mood_options = [
        {"emoji": "🤩", "value": "Amazing", "label": "Amazing"},
        {"emoji": "😊", "value": "Good", "label": "Good"},
        {"emoji": "🙂", "value": "Okay", "label": "Okay"},
        {"emoji": "😟", "value": "Down", "label": "Down"},
        {"emoji": "😢", "value": "Terrible", "label": "Terrible"},
    ]

    mood_logging_html = '<div style="text-align: center; margin-top: 15px;">'
    for mood in mood_options:
        token = hashlib.sha256(
            f"{user_email}{SUBSCRIPTION_SECRET_KEY}".encode()
        ).hexdigest()
        mood_log_url = f"{API_BASE_URL}/metrics/log_mood_via_redirect?email={user_email}&date={today_iso_date}&mood_value={mood['value']}&mood_emoji={mood['emoji']}&token={token}"
        mood_logging_html += f"""
            <a href="{mood_log_url}" target="_blank"
               style="text-decoration: none; margin: 0 8px; font-size: 30px; padding: 6px 10px; border-radius: 8px; background-color: #eaf2fa; display: inline-block; border: 1px solid #dce8f5; transition: transform 0.1s ease;"
               onmouseover="this.style.transform='scale(1.1)';" onmouseout="this.style.transform='scale(1)';"
               title="Log feeling {mood['label']}">
                {mood['emoji']}
            </a>
        """
    mood_logging_html += "</div>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Your Daily Opportunity Brief</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f7f6;
                color: #333333;
            }}
            .email-wrapper {{
                max-width: 600px;
                margin: 25px auto;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            }}
            .header {{
                background-color: #5D9CEC;
                color: #ffffff;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 500;
            }}
            .content {{
                padding: 30px;
            }}
            .greeting p {{
                font-size: 17px;
                line-height: 1.6;
                color: #555555;
                margin-bottom: 20px;
            }}
            .section-title {{
                font-size: 22px;
                color: #5D9CEC; 
                margin-top: 25px;
                margin-bottom: 15px;
                padding-bottom: 10px;
                border-bottom: 2px solid #e0e0e0;
            }}
            .content ul {{
                padding-left: 25px;
                margin-top: 10px;
                list-style-type: '→ ';
            }}
            .content ul li {{
                margin-bottom: 12px;
                font-size: 16px;
                line-height: 1.7;
                color: #444444;
            }}
            .content ul li strong {{
                color: #333333;
            }}
            .mood-log-section {{
                text-align: center;
                margin: 20px 0;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 10px;
            }}
            .mood-log-section .section-title {{
                 margin-top: 0;
                 border-bottom: none;
                 font-size: 20px;
                 color: #333;
            }}
            .mood-log-section p.subtitle {{
                font-size: 15px;
                color: #666;
                margin-top: 0;
                margin-bottom: 18px;
            }}
            .mood-emoji-link {{
                text-decoration: none;
                margin: 0 7px;
                font-size: 32px;
                padding: 8px 12px;
                border-radius: 10px;
                background-color: #e9eff7;
                display: inline-block;
                border: 1px solid #d8e2ef;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }}
            .mood-emoji-link:hover {{
                transform: scale(1.15);
                box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            }}
            .section-divider {{
                border: 0;
                height: 1px;
                background-color: #e8e8e8;
                margin: 35px 0;
            }}
            .quote-section {{
                margin: 30px 0 25px;
                padding: 20px 25px;
                background-color: #f0f5fb;
                border-radius: 10px;
                border-left: 6px solid #5D9CEC;
            }}
            .quote-section p {{
                font-style: italic;
                font-size: 17px;
                line-height: 1.65;
                margin: 0;
                color: #3a506b;
            }}
            .footer {{
                text-align: center;
                padding: 25px 30px;
                font-size: 13px;
                color: #777777;
                background-color: #f4f7f6;
                border-top: 1px solid #e0e0e0;
            }}
            .footer p {{ margin: 6px 0; }}
            .footer a {{ color: #5D9CEC; text-decoration: none; font-weight: 500; }}
            .footer a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="email-wrapper">
            <div class="header">
                <h1>Your Daily Opportunity Brief</h1>
            </div>
            <div class="content">
                <div class="greeting">
                    <p>Hi {user_name or user_email.split('@')[0]},</p>
                    <p>Here's your personalized update for {datetime.utcnow().strftime('%A, %B %d, %Y')}:</p>
                </div>

                <div class="mood-log-section">
                    <h2 class="section-title" style="margin-bottom: 5px;">How are you feeling today?</h2>
                    <p class="subtitle">Tap an emoji to quickly log your mood:</p>
                    {mood_logging_html}
                </div>

                <hr class="section-divider">

                <h2 class="section-title">Your Personalized Opportunity Brief</h2>
                <ul>{insights_and_nudges_html}</ul>

                <hr class="section-divider">

                <div class="quote-section">
                    <p>{motivational_quote_text}</p>
                </div>

            </div>
            <div class="footer">
                <p>This newsletter was automatically generated by Life Tracker.</p>
                <p>To manage your preferences, please visit your settings in the Life Tracker app.</p>
                <p><a href="{unsubscribe_url}">Unsubscribe from this newsletter</a></p>
            </div>
        </div>
        <!-- Tracking Pixel -->
        <img src="{API_BASE_URL}/newsletter/track/open/{log_id}" width="1" height="1" alt="" style="display:none;"/>
    </body>
    </html>
    """
    return html_content


def send_daily_briefing(
    final_insight_report: str, tool_context: ToolContext = None
) -> dict:
    if not final_insight_report:
        return {"status": "error", "message": "No insight report to send."}

    db = next(get_db())
    try:
        user_id = tool_context.state.get("user_id")
        user_email = tool_context.state.get("user_email")
        user_name = tool_context.state.get("user_name")
        user = crud.get_or_create_user(db, user_email, user_name, user_id)

        preference = crud.get_newsletter_preference(db, user.email)
        if not (preference and preference.subscribed):
            message = (
                f"User {user.email} is not subscribed to the newsletter. Skipping."
            )
            logger.info(message)
            return {"status": "skipped", "message": message}

        content_hash = hashlib.sha256(final_insight_report.encode()).hexdigest()
        log_entry = models.NewsletterLog(
            user_id=user.id,
            newsletter_category="daily_briefing",
            content_text=final_insight_report,
            content_hash=content_hash,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)

        html_body = generate_newsletter_html_content(
            user.email, user.username, final_insight_report, log_entry.id
        )
        subject = f"Your Daily Briefing - {datetime.utcnow().strftime('%B %d, %Y')}"

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_email_async(subject, html_body, user.email))
            logger.info(f"Email for {user.email} has been scheduled to be sent.")
            return {
                "status": "success",
                "message": f"Briefing queued for sending to {user.email}.",
            }
        except RuntimeError:
            logger.error(
                "No running asyncio event loop found. Cannot schedule email sending."
            )
            return {
                "status": "error",
                "message": "Failed to send briefing due to a missing event loop.",
            }
    finally:
        db.close()


async def trigger_insight_engine(user: models.User) -> str:
    """Triggers the insight engine for a user and returns the generated report."""
    from ..agent import root_agent

    prompt = "Based on my recent activity, generate a newsletter report with insights and nudges for my daily briefing."
    try:
        # Replicate the service configuration from fast_api.py for internal invocation
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        memory_service = InMemoryMemoryService()
        credential_service = InMemoryCredentialService()

        runner = Runner(
            app_name="gemini-adk-demo",
            agent=root_agent,
            artifact_service=artifact_service,
            session_service=session_service,
            memory_service=memory_service,
            credential_service=credential_service,
        )

        # Each newsletter generation is a new, ephemeral session
        session_id = f"newsletter-{user.id}-{uuid.uuid4()}"
        await session_service.create_session(
            app_name="gemini-adk-demo",
            user_id=str(user.id),
            session_id=session_id,
            state={"user_id": user.id, "user_email": user.email, "user_name": user.username},
        )

        final_insight_report = None
        # Use the synchronous runner to execute the agent, which correctly builds the InvocationContext
        for event in runner.run(
            user_id=str(user.id),
            session_id=session_id,
            new_message=Content(
                parts=[Part(text=prompt)],
                role="user"
            )
        ):
            if event.is_final_response() and event.content:
                final_insight_report = "".join(
                    part.text for part in event.content.parts if part.text
                )
                # The after_agent_callback in the workflow will handle the rest
                break

        return final_insight_report
    except Exception as e:
        logger.error(
            f"Error triggering insight engine for {user.email}: {e}", exc_info=True
        )
        return None


async def process_and_send_newsletters(db):
    """
    Processes and sends daily newsletters to all subscribed users.
    """
    users = db.query(models.User).all()
    logger.info(f"Found {len(users)} users to check for newsletter permissions.")

    for user in users:
        preference = crud.get_newsletter_preference(db, user.email)
        if preference and preference.subscribed:
            logger.info(f"Processing newsletter for user: {user.email}")
            try:
                # 1. Trigger the insight engine to get the personalized report
                final_insight_report = await trigger_insight_engine(user)

                if (
                    final_insight_report
                    and "No text response received" not in final_insight_report
                ):
                    logger.info(
                        f"Successfully triggered insight engine for {user.email}"
                    )
                else:
                    logger.warning(
                        f"Insight engine did not return a valid report for {user.email}. Skipping newsletter."
                    )

            except Exception as e:
                logger.error(
                    f"Failed to process newsletter for {user.email}: {e}", exc_info=True
                )
                db.rollback()  # Rollback any partial DB changes for this user


send_newsletter_tool = Tool(
    func=send_daily_briefing,
)
