# SiteMonitor

SaaS de monitorización web con marketing automatizado y chatbot.

## Estructura

```
sitemonitor/
├── core/           # Núcleo: API, auth, checker, Stripe, email
├── marketing/      # Posts automáticos + bot de menciones Reddit
├── chatbot/        # Asistente con Claude API
├── frontend/       # Landing page + Dashboard
├── main.py         # Punto de entrada FastAPI
└── requirements.txt
```

## Setup local

```bash
cd sitemonitor
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edita .env con tus credenciales

uvicorn main:app --reload
# → http://localhost:8000
```

## Variables de entorno necesarias

| Variable | Dónde obtenerla |
|----------|----------------|
| `SECRET_KEY` | Genera con: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `STRIPE_SECRET_KEY` | dashboard.stripe.com |
| `STRIPE_WEBHOOK_SECRET` | `stripe listen --forward-to localhost:8000/billing/webhook` |
| `STRIPE_PRO_PRICE_ID` | Crea un producto en Stripe ($5/mes recurrente) |
| `RESEND_API_KEY` | resend.com (gratis hasta 3k emails/mes) |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `REDDIT_CLIENT_ID/SECRET` | reddit.com/prefs/apps → crear app "script" |
| `DEVTO_API_KEY` | dev.to/settings/extensions |
| `BLUESKY_HANDLE/PASSWORD` | Tu cuenta de bsky.social |

## Despliegue en producción

```bash
# En tu VPS (Hetzner CX11 = ~$4/mes)
git clone <tu-repo> /opt/sitemonitor
cd /opt/sitemonitor
cp .env.example .env
# Rellena .env
bash deploy.sh tudominio.com
```

## Cómo funciona el marketing automatizado

1. El scheduler comprueba cada 30 min si hay posts pendientes
2. Si no hay post reciente en una plataforma, Claude genera uno nuevo
3. Se programa para publicar en horario de máximo tráfico
4. El bot monitoriza menciones en Reddit cada 2h y responde con Claude

## Plataformas de marketing

| Plataforma | Frecuencia | Tipo de contenido |
|-----------|-----------|------------------|
| Reddit | Cada 3 días | Post en subreddits relevantes |
| Dev.to | Semanal | Artículo técnico |
| Bluesky | Diario | Post corto |

## Monetización

- **Stripe Checkout**: flujo completo de pago
- **Stripe Webhooks**: activa/desactiva Pro automáticamente
- **Portal del cliente**: los usuarios gestionan su suscripción solos
