import resend
from core import config

resend.api_key = config.RESEND_API_KEY


async def send_change_alert(to_email: str, url: str, label: str | None, old_snippet: str, new_snippet: str):
    label_text = label or url
    subject = f"[SiteMonitor] Cambio detectado: {label_text}"
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
    <small>SiteMonitor · <a href="{config.BASE_URL}/dashboard">Tu dashboard</a></small>
    """
    if not config.RESEND_API_KEY:
        print(f"[EMAIL SIMULADO] Para: {to_email} | Asunto: {subject}")
        return
    resend.Emails.send({
        "from": config.FROM_EMAIL,
        "to": to_email,
        "subject": subject,
        "html": body,
    })


async def send_welcome_email(to_email: str):
    if not config.RESEND_API_KEY:
        print(f"[EMAIL SIMULADO] Bienvenida para: {to_email}")
        return
    resend.Emails.send({
        "from": config.FROM_EMAIL,
        "to": to_email,
        "subject": "Bienvenido a SiteMonitor 👋",
        "html": f"""
        <h2>¡Gracias por registrarte!</h2>
        <p>Ya puedes añadir las URLs que quieres monitorizar desde tu dashboard.</p>
        <p><a href="{config.BASE_URL}/dashboard">Ir al dashboard →</a></p>
        <p>Plan gratuito: hasta 3 URLs, checks cada 24h.<br>
        Plan Pro ($5/mes): URLs ilimitadas, checks cada hora.</p>
        """,
    })
