from groq import Groq
from core import config
import json

def _get_client():
    import os
    key = os.getenv("GROQ_API_KEY", "") or config.GROQ_API_KEY
    if not key:
        raise RuntimeError("GROQ_API_KEY no configurada")
    return Groq(api_key=key)

MODEL = "llama-3.3-70b-versatile"

PRODUCT_CONTEXT = """
GetURLMonitor is a SaaS tool that monitors URLs and sends email alerts when it detects
content changes. Use cases: price tracking, job alerts, competitor website changes, stock availability.
- Free plan: 3 URLs, checks every 24h
- Pro plan: $5/month, unlimited URLs, checks every hour
- Website: https://www.geturlmonitor.com
"""

REDDIT_SUBREDDITS = [
    ("SideProject", "Show HN style - proyecto propio, honesto, sin spam"),
    ("entrepreneur", "Emprendimiento, qué problema resuelve"),
    ("webdev", "Aspecto técnico, cómo funciona"),
    ("passive_income", "Cómo genera ingresos pasivos"),
    ("microsaas", "Micro-SaaS, stack, modelo de negocio"),
]


def _chat(prompt: str, max_tokens: int = 800) -> str:
    resp = _get_client().chat.completions.create(
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
You are the creator of GetURLMonitor. Write an authentic post for the subreddit r/{subreddit}.

Product context:
{PRODUCT_CONTEXT}

Subreddit tone: {context_hint}

Rules:
- Be honest and transparent, no spam
- Provide real value to the reader
- Mention the product naturally, not aggressively
- Include something useful even if they don't use the product
- Maximum 400 words
- Attractive title but no clickbait
- Write entirely in English

Respond EXACTLY in this format (nothing else):
TITLE: the title here
BODY:
the post body in markdown here
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
You are the creator of GetURLMonitor. Write a technical article for Dev.to.

Context:
{PRODUCT_CONTEXT}

The article must:
- Have real technical value
- Mention GetURLMonitor naturally at the end
- 500-800 words
- Exactly 4 simple tags in English (e.g.: webdev, python, productivity, opensource)
- Write entirely in English

Respond EXACTLY in this format (nothing else):
TITLE: the title here
TAGS: tag1,tag2,tag3,tag4
BODY:
the article body in markdown here
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
You are the creator of GetURLMonitor. Write a post for Bluesky (max 280 characters).

Product: {PRODUCT_CONTEXT}

The post must be natural, useful, not spam. Can be a tip, statistic, or product mention.
Write entirely in English.

Respond ONLY with the post text, no quotes or explanations.
"""
    return _chat(prompt, max_tokens=100)[:280]
