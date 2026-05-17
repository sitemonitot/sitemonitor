"""
Monitoriza menciones del producto en Reddit y responde automáticamente
usando Claude para generar respuestas contextuales y naturales.
"""
import praw
from groq import Groq
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from marketing.publishers import get_reddit_client, reply_reddit_comment
from core import config

logger = logging.getLogger(__name__)

KEYWORDS = ["site monitor", "sitemonitor", "monitor website", "website changes", "page change alert", "url monitor"]
REPLIED_COMMENTS = set()


async def generate_reply(comment_text: str, subreddit: str) -> str:
    client = Groq(api_key=config.GROQ_API_KEY)
    prompt = f"""
Eres el creador de SiteMonitor, una herramienta que monitoriza URLs y envía alertas por email.

Alguien en r/{subreddit} escribió:
"{comment_text}"

Tu tarea:
- Responder de forma NATURAL y ÚTIL, como lo haría un founder real
- Si el comentario pregunta por herramientas similares: menciona SiteMonitor brevemente
- Si el comentario menciona un problema que SiteMonitor resuelve: ofrece una solución
- Si el comentario es negativo: responde con empatía, sin ponerte a la defensiva
- Máximo 150 palabras
- No empieces con "¡Gran pregunta!" ni frases genéricas
- No suenes como un bot de marketing

Escribe SOLO la respuesta, sin explicaciones adicionales.
"""
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


async def check_reddit_mentions(db: AsyncSession):
    reddit = get_reddit_client()
    if not reddit:
        logger.warning("Reddit no configurado, saltando monitorización de menciones")
        return

    try:
        for keyword in KEYWORDS:
            for submission in reddit.subreddit("all").search(keyword, sort="new", time_filter="day", limit=10):
                # Revisar comentarios del post
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list()[:20]:
                    if comment.id in REPLIED_COMMENTS:
                        continue
                    if comment.author and comment.author.name == config.REDDIT_USERNAME:
                        continue

                    text_lower = comment.body.lower()
                    if any(kw in text_lower for kw in KEYWORDS):
                        reply = await generate_reply(comment.body, submission.subreddit.display_name)
                        success = await reply_reddit_comment(comment.id, reply)
                        if success:
                            REPLIED_COMMENTS.add(comment.id)
                            logger.info(f"Respondido comentario {comment.id} en r/{submission.subreddit.display_name}")

    except Exception as e:
        logger.error(f"Error monitorizando menciones Reddit: {e}")
