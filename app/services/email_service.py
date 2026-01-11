import os
import logging
import smtplib
import ssl
import asyncio
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from app.core.logger import create_logger

logger = create_logger('email')
load_dotenv()

# Setup Jinja2 environment
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "emails")
jinja_env = Environment(loader=FileSystemLoader(template_dir))

def render_template(template_name: str, **context) -> str:
    """Helper to render a Jinja2 template."""
    template = jinja_env.get_template(template_name)
    # Add common context like current year
    context.setdefault("year", datetime.now().year)
    return template.render(**context)

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
    attachments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    msg = MIMEMultipart("alternative") if not attachments else MIMEMultipart("mixed")
    
    # Create the alternative part for text/html
    if attachments:
        alt_part = MIMEMultipart("alternative")
        msg.attach(alt_part)
        msg_to_attach_text = alt_part
    else:
        msg_to_attach_text = msg

    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)

    # plain text
    part1 = MIMEText(body or "", "plain", "utf-8")
    msg_to_attach_text.attach(part1)

    if html_body:
        part2 = MIMEText(html_body, "html", "utf-8")
        msg_to_attach_text.attach(part2)

    # Attachments
    if attachments:
        for attachment in attachments:
            file_content = attachment.get("content")
            file_name = attachment.get("filename")
            content_type = attachment.get("content_type", "application/octet-stream")
            
            if file_content and file_name:
                part = MIMEBase(*content_type.split("/"))
                part.set_payload(file_content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={file_name}",
                )
                msg.attach(part)

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
    
    template_data = {
        "tenant_name": tenant_name,
        "activation_url": link_url
    }
    
    try:
        html_body = render_template("registration.html", **template_data)
        # For plain text, we can use a simpler approach or a dedicated .txt template
        # For now, let's keep it simple or strip HTML if we wanted to be fancy
        body = (
            f"Hi {tenant_name},\n\n"
            f"Please complete your tenant setup by visiting the following link:\n{link_url}\n\n"
            "— The Team"
        )
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        # Fallback to simple strings
        body = f"Hi {tenant_name}, please activate: {link_url}"
        html_body = body

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
    password: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    payment_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Send a subscription confirmation email with plan details, credentials, and optional invoice."""
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
    
    template_data = {
        "tenant_name": tenant_name,
        "plan_name": plan_name,
        "start_date": start_date,
        "end_date": end_date,
        "username": username,
        "password": password,
        "payment_info": payment_info,
        "has_attachments": bool(attachments)
    }

    try:
        html_body = render_template("subscription_confirmation.html", **template_data)
        # Simplified plain text body
        body = f"Hi {tenant_name},\n\nYour subscription for {plan_name} is active.\n"
        if username:
            body += f"Login: {username}\n"
        if attachments:
            body += "Invoice attached.\n"
    except Exception as e:
        logger.error(f"Template rendering failed: {e}")
        body = f"Subscription {plan_name} activated for {tenant_name}."
        html_body = body

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
        attachments,
    )

    return result
