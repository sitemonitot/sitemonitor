from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID = os.getenv("STRIPE_PRO_PRICE_ID", "")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@sitemonitor.io")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SiteMonitorBot/1.0")

DEVTO_API_KEY = os.getenv("DEVTO_API_KEY", "")

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE", "")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD", "")

FREE_URL_LIMIT = 3
FREE_CHECK_INTERVAL_HOURS = 6
PRO_CHECK_INTERVAL_HOURS = 1
