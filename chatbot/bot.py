from groq import Groq
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from core.database import get_db
from core.models import ChatSession, ChatMessage
from core import config

router = APIRouter(prefix="/chat", tags=["chatbot"])

SYSTEM_PROMPT = f"""
Eres el asistente de soporte de SiteMonitor. Respondes preguntas sobre el producto
de forma amable, clara y concisa. Nunca inventas información.

Información del producto:
- SiteMonitor monitoriza URLs y envía alertas por email cuando el contenido cambia
- Plan gratuito: hasta 3 URLs, checks cada 24 horas
- Plan Pro: $5/mes, URLs ilimitadas, checks cada hora
- Casos de uso: precios, empleo, stock, webs de competidores, noticias
- URL: {config.BASE_URL}

Si no sabes algo, di "No tengo esa información, puedes contactar con soporte".
Responde siempre en el idioma del usuario.
Sé breve: máximo 3-4 frases por respuesta.
"""


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@router.post("/")
async def chat(data: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not config.GROQ_API_KEY:
        return {
            "reply": "El chatbot no está activo. Añade GROQ_API_KEY en .env (gratis en console.groq.com).",
            "session_id": data.session_id or "local",
        }

    client = Groq(api_key=config.GROQ_API_KEY)
    session_id = data.session_id or str(uuid.uuid4())

    result = await db.execute(select(ChatSession).where(ChatSession.session_id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(session_id=session_id)
        db.add(session)
        await db.commit()
        await db.refresh(session)

    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    history = list(reversed(msgs_result.scalars().all()))

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": data.message})

    user_msg = ChatMessage(session_id=session.id, role="user", content=data.message)
    db.add(user_msg)

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=400,
        messages=messages,
    )
    reply = resp.choices[0].message.content.strip()

    assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=reply)
    db.add(assistant_msg)
    await db.commit()

    return {"reply": reply, "session_id": session_id}
