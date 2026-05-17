import os
import resend
from core import config


def _resend_key() -> str:
    return os.getenv("RESEND_API_KEY", "") or config.RESEND_API_KEY


def _from_email() -> str:
    return os.getenv("FROM_EMAIL", "") or config.FROM_EMAIL


def _base_url() -> str:
    return os.getenv("BASE_URL", "") or config.BASE_URL


def _footer(base_url: str) -> str:
    return f'<hr style="margin-top:32px"><p style="color:#aaa;font-size:12px;">GetURLMonitor · <a href="{base_url}/dashboard" style="color:#aaa;">Dashboard</a> · <a href="{base_url}/profile" style="color:#aaa;">Settings</a></p>'


async def send_change_alert(to_email: str, url: str, label: str | None, old_snippet: str, new_snippet: str, extra_emails: list[str] | None = None):
    label_text = label or url
    base_url = _base_url()
    subject = f"Change detected: {label_text}"
    body = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1e3a5f">Change detected: <a href="{url}" style="color:#1a73e8">{label_text}</a></h2>
      <h3 style="color:#555">Before</h3>
      <div style="background:#fff3f3;padding:12px;border-left:4px solid #e53e3e;border-radius:4px;font-size:14px;white-space:pre-wrap">{old_snippet}</div>
      <h3 style="color:#555;margin-top:16px">After</h3>
      <div style="background:#f0fff4;padding:12px;border-left:4px solid #38a169;border-radius:4px;font-size:14px;white-space:pre-wrap">{new_snippet}</div>
      <p style="margin-top:20px"><a href="{url}" style="background:#1a73e8;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold">View page →</a></p>
      {_footer(base_url)}
    </div>
    """
    key = _resend_key()
    if not key:
        print(f"[EMAIL MOCK] To: {to_email} | Subject: {subject}")
        return
    resend.api_key = key
    all_emails = [to_email] + [e for e in (extra_emails or []) if e != to_email]
    resend.Emails.send({"from": _from_email(), "to": all_emails, "subject": subject, "html": body})


async def send_reset_email(to_email: str, token: str):
    base_url = _base_url()
    reset_url = f"{base_url}/reset-password?token={token}"
    key = _resend_key()
    if not key:
        print(f"[EMAIL MOCK] Reset password for: {to_email} | URL: {reset_url}")
        return
    resend.api_key = key
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": "Reset your GetURLMonitor password",
        "html": f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#1e3a5f">Password reset</h2>
          <p>Click the button below to set a new password. This link expires in 1 hour.</p>
          <p><a href="{reset_url}" style="background:#1a73e8;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;">Reset password →</a></p>
          <p style="color:#aaa;font-size:12px;margin-top:24px">If you didn't request this, you can safely ignore this email.</p>
          {_footer(base_url)}
        </div>
        """,
    })


async def send_verification_email(to_email: str, token: str):
    base_url = _base_url()
    verify_url = f"{base_url}/auth/verify?token={token}"
    key = _resend_key()
    if not key:
        print(f"[EMAIL MOCK] Verify email for: {to_email} | URL: {verify_url}")
        return
    resend.api_key = key
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": "Confirm your GetURLMonitor email",
        "html": f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#1e3a5f">Welcome to GetURLMonitor!</h2>
          <p>Please confirm your email address to activate your account.</p>
          <p><a href="{verify_url}" style="background:#1a73e8;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;">Confirm email →</a></p>
          <p style="color:#aaa;font-size:12px;margin-top:24px">This link expires in 24 hours. If you didn't create this account, ignore this email.</p>
          {_footer(base_url)}
        </div>
        """,
    })


async def send_welcome_email(to_email: str):
    base_url = _base_url()
    key = _resend_key()
    if not key:
        print(f"[EMAIL MOCK] Welcome for: {to_email}")
        return
    resend.api_key = key
    resend.Emails.send({
        "from": _from_email(),
        "to": to_email,
        "subject": "Welcome to GetURLMonitor 👋",
        "html": f"""
        <div style="font-family:sans-serif;max-width:600px;margin:auto">
          <h2 style="color:#1e3a5f">Welcome to GetURLMonitor!</h2>
          <p>You're all set. Add your first URL to start monitoring — we'll email you whenever anything changes.</p>
          <p><a href="{base_url}/dashboard" style="background:#1a73e8;color:white;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:bold;">Go to dashboard →</a></p>
          <p style="color:#555;font-size:14px;margin-top:16px">
            <strong>Free plan:</strong> up to 3 URLs, checks every 6 hours.<br>
            <strong>Pro ($5/mo):</strong> unlimited URLs, checks every hour.
          </p>
          {_footer(base_url)}
        </div>
        """,
    })
