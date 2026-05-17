from groq import Groq
from core import config
import json

client = Groq(api_key=config.GROQ_API_KEY) if config.GROQ_API_KEY else None

MODEL = "llama-3.3-70b-versatile"

PRODUCT_CONTEXT = f"""
SiteMonitor es una herramienta SaaS que monitoriza URLs y envía alertas por email cuando
detecta cambios en el contenido. Casos de uso: seguimiento de precios, alertas de empleo,
cambios en webs de competidores, disponibilidad de stock.
- Plan gratuito: 3 URLs, checks cada 24h
- Plan Pro: $5/mes, URLs ilimitadas, checks cada hora
- Web: {config.BASE_URL}
"""

REDDIT_SUBREDDITS = [
    ("SideProject", "Show HN style - proyecto propio, honesto, sin spam"),
    ("entrepreneur", "Emprendimiento, qué problema resuelve"),
    ("webdev", "Aspecto técnico, cómo funciona"),
    ("passive_income", "Cómo genera ingresos pasivos"),
    ("microsaas", "Micro-SaaS, stack, modelo de negocio"),
]


def _chat(prompt: str, max_tokens: int = 800) -> str:
    if not client:
        raise RuntimeError("GROQ_API_KEY no configurada")
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _parse_json(text: str) -> dict:
    # Extraer bloque de código si existe
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if part.startswith("json"):
                text = part[4:]
                break
            elif part.strip().startswith("{"):
                text = part
                break
    text = text.strip()
    # Primer intento directo
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Buscar el primer { y último } para extraer solo el JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No se pudo extraer JSON del texto: {text[:200]}")


async def generate_reddit_post(subreddit: str, context_hint: str) -> dict:
    prompt = f"""
Eres el creador de SiteMonitor. Escribe un post auténtico para el subreddit r/{subreddit}.

Contexto del producto:
{PRODUCT_CONTEXT}

Tono del subreddit: {context_hint}

Reglas:
- Sé honesto y transparente, no hagas spam
- Aporta valor real al lector
- Menciona el producto de forma natural, no agresiva
- Incluye algo útil aunque no usen el producto
- Máximo 400 palabras
- Título atractivo pero no clickbait

Responde EXACTAMENTE en este formato (sin nada más):
TITLE: el título aquí
BODY:
el cuerpo del post en markdown aquí
"""
    text = _chat(prompt)
    lines = text.strip().split("\n")
    title = ""
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {"title": title, "body": "\n".join(body_lines)}


async def generate_devto_post() -> dict:
    prompt = f"""
Eres el creador de SiteMonitor. Escribe un artículo técnico para Dev.to.

Contexto:
{PRODUCT_CONTEXT}

El artículo debe:
- Tener valor técnico real
- Mencionar SiteMonitor de forma natural al final
- 500-800 palabras
- Exactamente 4 tags en inglés, simples (ej: webdev, python, productivity, opensource)

Responde EXACTAMENTE en este formato (sin nada más):
TITLE: el título aquí
TAGS: tag1,tag2,tag3,tag4
BODY:
el cuerpo del artículo en markdown aquí
"""
    text = _chat(prompt, max_tokens=1500)
    lines = text.strip().split("\n")
    title = ""
    tags = []
    body_lines = []
    in_body = False
    for line in lines:
        if line.startswith("TITLE:"):
            title = line[6:].strip()
        elif line.startswith("TAGS:"):
            tags = [t.strip() for t in line[5:].split(",")][:4]
        elif line.startswith("BODY:"):
            in_body = True
        elif in_body:
            body_lines.append(line)
    return {"title": title, "body_markdown": "\n".join(body_lines), "tags": tags}


async def generate_bluesky_post() -> str:
    prompt = f"""
Eres el creador de SiteMonitor. Escribe un post para Bluesky (máx 280 caracteres).

Producto: {PRODUCT_CONTEXT}

El post debe ser natural, útil, no spam. Puede ser un tip, estadística o mención del producto.

Responde SOLO con el texto del post, sin comillas ni explicaciones.
"""
    return _chat(prompt, max_tokens=100)[:280]
