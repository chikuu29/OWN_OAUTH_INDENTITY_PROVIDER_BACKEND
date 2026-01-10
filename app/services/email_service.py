import os
import logging
import smtplib
import ssl
import asyncio
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
logger = logging.getLogger(__name__)
load_dotenv()

def _send_smtp_email(
    smtp_server: str,
    smtp_port: int,
    username: str,
    password: str,
    use_tls: bool,
    from_email: str,
    to_emails: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> Dict[str, Any]:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    # plain text
    part1 = MIMEText(body or "", "plain", "utf-8")
    msg.attach(part1)

    if html_body:
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part2)

    try:
        if use_tls:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls(context=ssl.create_default_context())
        else:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ssl.create_default_context())

        server.login(username, password)
        rejected = server.sendmail(from_email, to_emails, msg.as_string())
        server.quit()

        return {"success": True, "rejected": rejected}

    except Exception as e:
        logger.exception("Failed to send SMTP email")
        return {"success": False, "error": str(e)}


async def send_tenant_registration_email(tenant_email: str, tenant_name: str, link_url: str = None) -> Dict[str, Any]:
    """Send a simple welcome email to a newly registered tenant.

    Uses environment variables:
      SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_USE_TLS, FROM_EMAIL, FROM_NAME
    """
    # Load configuration from env
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    from_email = os.getenv("FROM_EMAIL", smtp_username)
    from_name = os.getenv("FROM_NAME", "Support")

    if not smtp_username or not smtp_password:
        msg = "SMTP credentials are not configured"
        logger.error(msg)
        return {"success": False, "error": msg}

    subject = f"Welcome to the platform, {tenant_name}!"
    if link_url:
        body = (
            f"Hi {tenant_name},\n\n"
            "Please complete your tenant setup by visiting the following link (valid for 24 hours):\n"
            f"{link_url}\n\n"
            "If you did not request this, you can ignore this email.\n\n"
            "— The Team"
        )
        html_body = f"<p>Hi {tenant_name},</p><p>Please complete your tenant setup by visiting the following link (valid for 24 hours):</p><p><a href=\"{link_url}\">Complete setup</a></p><p>— The Team</p>"
    else:
        body = (
            f"Hi {tenant_name},\n\n"
            "Thanks for registering your tenant. Your account has been created successfully.\n\n"
            "— The Team"
        )
        html_body = f"<p>Hi {tenant_name},</p><p>Thanks for registering your tenant. Your account has been created successfully.</p><p>— The Team</p>"

    # run blocking SMTP call in thread
    result = await asyncio.to_thread(
        _send_smtp_email,
        smtp_server,
        smtp_port,
        smtp_username,
        smtp_password,
        smtp_use_tls,
        f"{from_name} <{from_email}>",
        [tenant_email],
        subject,
        body,
        html_body,
    )

    return result
async def send_subscription_confirmation_email(
    tenant_email: str, 
    tenant_name: str, 
    plan_name: str,
    start_date: str,
    end_date: str,
    username: Optional[str] = None,
    password: Optional[str] = None
) -> Dict[str, Any]:
    """Send a subscription confirmation email with plan details and credentials."""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    from_email = os.getenv("FROM_EMAIL", smtp_username)
    from_name = os.getenv("FROM_NAME", "Support")

    if not smtp_username or not smtp_password:
        msg = "SMTP credentials are not configured"
        logger.error(msg)
        return {"success": False, "error": msg}

    subject = f"Subscription Activated: {plan_name}"
    
    body = (
        f"Hi {tenant_name},\n\n"
        f"Your subscription for the {plan_name} plan has been successfully activated!\n\n"
        f"Details:\n"
        f"- Plan: {plan_name}\n"
        f"- Start Date: {start_date}\n"
        f"- End Date: {end_date}\n\n"
    )
    
    html_body = (
        f"<h3>Hi {tenant_name},</h3>"
        f"<p>Your subscription for the <b>{plan_name}</b> plan has been successfully activated!</p>"
        f"<h4>Details:</h4>"
        f"<ul>"
        f"<li><b>Plan:</b> {plan_name}</li>"
        f"<li><b>Start Date:</b> {start_date}</li>"
        f"<li><b>End Date:</b> {end_date}</li>"
        f"</ul>"
    )

    if username and password:
        creds_text = (
            f"Here are your administrator credentials to get started:\n"
            f"- Username: {username}\n"
            f"- Default Password: {password}\n"
            f"Please change your password after logging in.\n\n"
        )
        body += creds_text
        html_body += (
            f"<h4>Admin Credentials:</h4>"
            f"<ul>"
            f"<li><b>Username:</b> {username}</li>"
            f"<li><b>Default Password:</b> {password}</li>"
            f"</ul>"
            f"<p><i>Please change your password after logging in.</i></p>"
        )

    body += "Happy building!\n— The Team"
    html_body += "<p>Happy building!<br>— The Team</p>"

    result = await asyncio.to_thread(
        _send_smtp_email,
        smtp_server,
        smtp_port,
        smtp_username,
        smtp_password,
        smtp_use_tls,
        f"{from_name} <{from_email}>",
        [tenant_email],
        subject,
        body,
        html_body,
    )

    return result
