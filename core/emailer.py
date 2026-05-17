import os
import resend
from core import config


def _resend_key() -> str:
    return os.getenv("RESEND_API_KEY", "") or config.RESEND_API_KEY


def _from_email() -> str:
    return os.getenv("FROM_EMAIL", "") or config.FROM_EMAIL


async def send_change_alert(to_email: str, url: str, label: str | None, old_snippet: str, new_snippet: str):
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
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": subject,
        "html": body,
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
