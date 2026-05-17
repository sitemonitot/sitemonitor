import stripe
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.database import get_db
from core.models import User
from core.auth import get_current_user
from core import config

router = APIRouter(prefix="/billing", tags=["billing"])


def _stripe_key() -> str:
    import os
    return os.getenv("STRIPE_SECRET_KEY", "") or config.STRIPE_SECRET_KEY


def _price_id() -> str:
    import os
    return os.getenv("STRIPE_PRO_PRICE_ID", "") or config.STRIPE_PRO_PRICE_ID


def _webhook_secret() -> str:
    import os
    return os.getenv("STRIPE_WEBHOOK_SECRET", "") or config.STRIPE_WEBHOOK_SECRET


@router.post("/checkout")
async def create_checkout(user: User = Depends(get_current_user)):
    stripe.api_key = _stripe_key()
    if not stripe.api_key:
        raise HTTPException(503, "Stripe no configurado")

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email)
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": _price_id(), "quantity": 1}],
        mode="subscription",
        success_url=f"{config.BASE_URL}/dashboard?upgraded=1",
        cancel_url=f"{config.BASE_URL}/dashboard",
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": session.url}


@router.post("/portal")
async def customer_portal(user: User = Depends(get_current_user)):
    stripe.api_key = _stripe_key()
    if not user.stripe_customer_id:
        raise HTTPException(400, "No hay suscripción activa")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{config.BASE_URL}/dashboard",
    )
    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    stripe.api_key = _stripe_key()
    try:
        event = stripe.Webhook.construct_event(payload, sig, _webhook_secret())
    except Exception:
        raise HTTPException(400, "Webhook inválido")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"]["user_id"])
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_pro = True
            user.stripe_customer_id = session["customer"]
            user.stripe_subscription_id = session["subscription"]
            await db.commit()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        sub = event["data"]["object"]
        result = await db.execute(select(User).where(User.stripe_subscription_id == sub["id"]))
        user = result.scalar_one_or_none()
        if user:
            user.is_pro = False
            await db.commit()

    return {"ok": True}
