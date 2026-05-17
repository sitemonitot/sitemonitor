import os
import resend
from core import config


def _resend_key() -> str:
    return os.getenv("RESEND_API_KEY", "") or config.RESEND_API_KEY


def _from_email() -> str:
    return os.getenv("FROM_EMAIL", "") or config.FROM_EMAIL


async def send_change_alert(to_email: str, url: str, label: str | None, old_snippet: str, new_snippet: str, extra_emails: list[str] | None = None):
    label_text = label or url
    subject = f"[SiteMonitor] Cambio detectado: {label_text}"
    base_url = os.getenv("BASE_URL", "") or config.BASE_URL
    body = f"""
    <h2>Se detectó un cambio en: <a href="{url}">{label_text}</a></h2>
    <h3>Antes:</h3>
    <blockquote style="background:#f5f5f5;padding:12px;border-left:4px solid #ccc;">
        {old_snippet}
    </blockquote>
    <h3>Ahora:</h3>
    <blockquote style="background:#e8f5e9;padding:12px;border-left:4px solid #4caf50;">
        {new_snippet}
    </blockquote>
    <p><a href="{url}">Ver página →</a></p>
    <hr>
    <small>SiteMonitor · <a href="{base_url}/dashboard">Tu dashboard</a></small>
    """
    key = _resend_key()
    if not key:
        print(f"[EMAIL SIMULADO] Para: {to_email} | Asunto: {subject}")
        return
    resend.api_key = key
    all_emails = [to_email] + [e for e in (extra_emails or []) if e != to_email]
    resend.Emails.send({
        "from": _from_email(),
        "to": all_emails,
        "subject": subject,
        "html": body,
    })


async def send_reset_email(to_email: str, token: str):
    key = _resend_key()
    base_url = os.getenv("BASE_URL", "") or config.BASE_URL
    reset_url = f"{base_url}/reset-password?token={token}"
    if not key:
        print(f"[EMAIL SIMULADO] Reset password para: {to_email} | URL: {reset_url}")
        return
    resend.api_key = key
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": "Reset your GetURLMonitor password",
        "html": f"""
        <h2>Password reset request</h2>
        <p>Click the link below to set a new password. This link expires in 1 hour.</p>
        <p><a href="{reset_url}" style="background:#1a73e8;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Reset password</a></p>
        <p style="color:#888;font-size:12px;">If you didn't request this, ignore this email. Your password won't change.</p>
        """,
    })


async def send_welcome_email(to_email: str):
    key = _resend_key()
    base_url = os.getenv("BASE_URL", "") or config.BASE_URL
    if not key:
        print(f"[EMAIL SIMULADO] Bienvenida para: {to_email}")
        return
    resend.api_key = key
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": "Bienvenido a SiteMonitor 👋",
        "html": f"""
        <h2>¡Gracias por registrarte!</h2>
        <p>Ya puedes añadir las URLs que quieres monitorizar desde tu dashboard.</p>
        <p><a href="{base_url}/dashboard">Ir al dashboard →</a></p>
        <p>Plan gratuito: hasta 3 URLs, checks cada 24h.<br>
        Plan Pro ($5/mes): URLs ilimitadas, checks cada hora.</p>
        """,
    })
