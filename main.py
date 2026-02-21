"""
Checkr.ai — Instagram Fact-Checking Bot
Monolithic FastAPI app. One file. No microservices.

Stack:
  - FastAPI (webhook server)
  - Groq / Llama 3.3 70B — free, no credit card needed (console.groq.com)
  - Tavily (web search grounding)
  - Instagram API with Business Login — no Facebook Page needed
  - In-memory cache (upgradeable to Redis via REDIS_URL)
"""
from dotenv import load_dotenv
import hashlib
import hmac
import json
import logging
import os

load_dotenv()
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from openai import OpenAI          # Groq uses the OpenAI-compatible SDK
from pydantic import BaseModel

# ─────────────────────────────────────────────
# CONFIG  (all from environment variables)
# ─────────────────────────────────────────────

VERIFY_TOKEN       = os.getenv("VERIFY_TOKEN", "checkr_verify_token_change_me")
APP_SECRET         = os.getenv("APP_SECRET", "")
ACCESS_TOKEN       = os.getenv("ACCESS_TOKEN", "")  # Instagram User Access Token (from OAuth)
IG_USER_ID         = os.getenv("IG_USER_ID", "")   # Your Instagram Business Account user ID
GROQ_API_KEY       = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY     = os.getenv("TAVILY_API_KEY", "")
REDIS_URL          = os.getenv("REDIS_URL", "")     # Optional — falls back to in-memory
ENVIRONMENT        = os.getenv("ENVIRONMENT", "development")
MAX_CLAIM_LENGTH   = 500
CACHE_TTL_SECONDS  = 86400   # 24 hours
RATE_LIMIT_PER_DAY = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("checkr")

# ─────────────────────────────────────────────
# CACHE  (in-memory dict, Redis if configured)
# ─────────────────────────────────────────────

_mem_cache: dict = {}
_redis = None


async def _init_redis():
    global _redis
    if not REDIS_URL:
        log.info("No REDIS_URL — using in-memory cache")
        return
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        await _redis.ping()
        log.info("✅ Redis connected")
    except Exception as e:
        log.warning(f"Redis unavailable ({e}) — falling back to in-memory")
        _redis = None


def _cache_key(text: str) -> str:
    return "checkr:claim:" + hashlib.sha256(text.lower().strip().encode()).hexdigest()


def _rate_key(user_id: str) -> str:
    return f"checkr:rate:{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"


async def cache_get(claim: str) -> Optional[dict]:
    key = _cache_key(claim)
    try:
        if _redis:
            val = await _redis.get(key)
            return json.loads(val) if val else None
        entry = _mem_cache.get(key)
        if entry and entry["exp"] > datetime.utcnow().isoformat():
            return entry["data"]
    except Exception as e:
        log.warning(f"Cache read error: {e}")
    return None


async def cache_set(claim: str, data: dict):
    key = _cache_key(claim)
    try:
        if _redis:
            await _redis.setex(key, CACHE_TTL_SECONDS, json.dumps(data))
        else:
            exp = (datetime.utcnow() + timedelta(seconds=CACHE_TTL_SECONDS)).isoformat()
            _mem_cache[key] = {"data": data, "exp": exp}
    except Exception as e:
        log.warning(f"Cache write error: {e}")


async def rate_ok(user_id: str) -> bool:
    key = _rate_key(user_id)
    try:
        if _redis:
            count = await _redis.incr(key)
            if count == 1:
                await _redis.expire(key, 86400)
            return count <= RATE_LIMIT_PER_DAY
        entry = _mem_cache.get(key, {"count": 0})
        entry["count"] += 1
        _mem_cache[key] = entry
        return entry["count"] <= RATE_LIMIT_PER_DAY
    except Exception:
        return True  # fail open


# ─────────────────────────────────────────────
# SEARCH  (Tavily)
# ─────────────────────────────────────────────

async def search(claim: str) -> list[dict]:
    """Fetch top web sources for the claim via Tavily."""
    if not TAVILY_API_KEY:
        log.warning("No TAVILY_API_KEY — skipping search")
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": claim,
                    "search_depth": "advanced",
                    "max_results": 5,
                    "include_answer": False,
                },
            )
            results = resp.json().get("results", [])
            log.info(f"Tavily returned {len(results)} results")
            return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")[:400]} for r in results]
    except Exception as e:
        log.warning(f"Tavily error: {e}")
        return []


# ─────────────────────────────────────────────
# FACT-CHECK  (Groq / Llama 3.3 70B)
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are Checkr.ai, a rigorous and impartial fact-checking assistant.

Return ONLY valid JSON — no markdown, no text outside the JSON.

Output format:
{
  "verdict": "TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIABLE" | "NOT_A_CLAIM",
  "explanation": "1-2 sentences max.",
  "sources": ["url1", "url2"],
  "confidence": "high" | "medium" | "low"
}

Rules:
- Only use URLs from the provided search results — never invent URLs.
- NOT_A_CLAIM = opinions, questions, predictions, jokes — anything that cannot be fact-checked.
- Prefer UNVERIFIABLE over guessing when evidence is thin.
- Keep explanation to 1-2 sentences."""


def clean_claim(text: str) -> str:
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#\w+", "", text)
    text = re.sub(r"http\S+|www\.\S+", "", text)
    return " ".join(text.split()).strip()[:MAX_CLAIM_LENGTH]


async def fact_check(raw_text: str) -> dict:
    claim = clean_claim(raw_text)
    if not claim:
        return {"verdict": "NOT_A_CLAIM", "explanation": "No claim found.", "sources": [], "confidence": "high", "claim": ""}

    # Cache check
    cached = await cache_get(claim)
    if cached:
        log.info("Cache hit")
        return cached

    # Search for sources
    sources = await search(claim)
    sources_text = "\n".join(
        f"[{i+1}] {s['title']}\n    URL: {s['url']}\n    Excerpt: {s['content']}"
        for i, s in enumerate(sources)
    ) or "No sources found."

    # Call Groq (Llama 3.3 70B) — free, OpenAI-compatible
    try:
        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f'CLAIM: "{claim}"\n\nSEARCH RESULTS:\n{sources_text}\n\nReturn your JSON verdict.'},
            ],
        )
        raw = response.choices[0].message.content
        data = json.loads(re.sub(r"```json|```", "", raw).strip())
    except Exception as e:
        log.error(f"Groq error: {e}")
        data = {"verdict": "UNVERIFIABLE", "explanation": "Fact-check temporarily unavailable.", "sources": [], "confidence": "low"}

    # Sanitise: only allow URLs from search results
    allowed = {s["url"] for s in sources}
    data["sources"] = [u for u in data.get("sources", []) if u in allowed][:2]
    data["claim"] = claim

    await cache_set(claim, data)
    return data


# ─────────────────────────────────────────────
# INSTAGRAM  (Business Login API — no FB Page)
# Uses graph.instagram.com, not graph.facebook.com
# ─────────────────────────────────────────────

GRAPH = "https://graph.instagram.com/v20.0"

EMOJI = {"TRUE": "✅", "FALSE": "❌", "MISLEADING": "⚠️", "UNVERIFIABLE": "❓", "NOT_A_CLAIM": "💬"}


def build_reply(result: dict, username: Optional[str] = None) -> str:
    verdict = result.get("verdict", "UNVERIFIABLE")
    emoji = EMOJI.get(verdict, "🔍")
    label = verdict.replace("_", " ")
    lines = []
    if username:
        lines.append(f"@{username}")
    lines.append(f"🔍 Fact Check: {emoji} {label}")
    lines.append("")
    lines.append(result.get("explanation", ""))
    if result.get("sources"):
        lines.append("")
        lines.append("📎 Sources:")
        for url in result["sources"]:
            lines.append(url)
    lines.append("")
    lines.append("— Checkr.ai")
    return "\n".join(lines)[:2000]


def build_not_a_claim_reply(username: Optional[str] = None) -> str:
    lines = []
    if username:
        lines.append(f"@{username}")
    lines.append("👋 Checkr.ai can only verify factual claims — not opinions or questions.")
    lines.append("Tag me next to a specific fact you want checked!")
    lines.append("— Checkr.ai")
    return "\n".join(lines)


def build_rate_limit_reply(username: Optional[str] = None) -> str:
    lines = []
    if username:
        lines.append(f"@{username}")
    lines.append("⏳ You've hit today's limit of 10 fact-checks. Try again tomorrow!")
    lines.append("— Checkr.ai")
    return "\n".join(lines)


async def post_reply(media_id: str, comment_id: Optional[str], text: str):
    if not ACCESS_TOKEN:
        log.warning("No ACCESS_TOKEN — skipping reply (dev mode)")
        log.info(f"[DRY RUN REPLY]\n{text}")
        return
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            url = f"{GRAPH}/{comment_id}/replies" if comment_id else f"{GRAPH}/{media_id}/comments"
            resp = await client.post(url, data={"message": text, "access_token": ACCESS_TOKEN})
            resp.raise_for_status()
            log.info(f"Reply posted: {resp.json().get('id')}")
    except Exception as e:
        log.error(f"Failed to post reply: {e}")


# ─────────────────────────────────────────────
# PIPELINE
# ─────────────────────────────────────────────

async def handle_mention(media_id: str, comment_id: Optional[str], text: str, user_id: Optional[str], username: Optional[str]):
    log.info(f"Mention — text: {text[:80]}")

    if user_id and not await rate_ok(user_id):
        await post_reply(media_id, comment_id, build_rate_limit_reply(username))
        return

    result = await fact_check(text)

    reply = build_not_a_claim_reply(username) if result.get("verdict") == "NOT_A_CLAIM" else build_reply(result, username)
    await post_reply(media_id, comment_id, reply)
    log.info(f"✅ Done — verdict: {result.get('verdict')}")


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await _init_redis()
    log.info("🚀 Checkr.ai is live")
    yield

app = FastAPI(title="Checkr.ai", version="1.0.0", lifespan=lifespan)


@app.get("/webhook")
async def verify(request: Request):
    """Meta webhook verification — echoes hub.challenge back."""
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == VERIFY_TOKEN:
        log.info("Webhook verified ✅")
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks):
    """Receive Instagram events. Always returns 200 fast; processing is async."""
    body = await request.body()

    # RAW LOGGER — see exactly what Instagram sends
    log.info(f"WEBHOOK HIT raw={body.decode()[:800]}")

    if APP_SECRET:
        sig = request.headers.get("x-hub-signature-256", "")
        expected = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            log.error(f"Bad signature: {sig}")
            raise HTTPException(status_code=403, detail="Bad signature")

    payload = json.loads(body)
    log.info(f"PAYLOAD object={payload.get('object')} entries={len(payload.get('entry', []))}")

    if payload.get("object") != "instagram":
        log.warning(f"Not instagram object: {payload.get('object')}")
        return Response(status_code=200)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            field  = change.get("field")
            value  = change.get("value", {})
            log.info(f"CHANGE field={field} value={json.dumps(value)[:300]}")
            media_id   = value.get("media_id", "")
            comment_id = value.get("comment_id")
            text       = value.get("text", "")
            from_      = value.get("from", {}) if isinstance(value.get("from"), dict) else {}
            user_id    = from_.get("id")
            username   = from_.get("username")

            # ── Ignore the bot's own comments to prevent infinite loop ──
            if user_id == IG_USER_ID or from_.get("self_ig_scoped_id"):
                log.info(f"Skipping bot's own comment from {username}")
                continue

            # @mention in caption or comment on ANY public post
            if field == "mentions" and media_id:
                bg.add_task(handle_mention, media_id, comment_id, text, user_id, username)

            # Comment containing @thehalfstackgirl
            elif field == "comments":
                media_id   = value.get("media", {}).get("id", "") or media_id
                comment_id = value.get("id", "")
                commenter  = value.get("from", {})
                bg.add_task(handle_mention, media_id, comment_id, text, commenter.get("id"), commenter.get("username"))

    return Response(status_code=200)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "groq_key":        "✅" if GROQ_API_KEY   else "❌ missing — get free key at console.groq.com",
        "tavily_key":      "✅" if TAVILY_API_KEY  else "❌ missing — get free key at tavily.com",
        "instagram_token": "✅" if ACCESS_TOKEN     else "❌ missing — complete Instagram OAuth",
        "ig_user_id":      "✅" if IG_USER_ID       else "❌ missing — run /setup to find yours",
        "cache":           "redis" if _redis else "in-memory",
        "environment":     ENVIRONMENT,
    }


@app.get("/setup")
async def setup():
    """Helper: fetch your IG_USER_ID from the API once you have an ACCESS_TOKEN."""
    if not ACCESS_TOKEN:
        return {"error": "Set ACCESS_TOKEN in .env first, then visit this endpoint."}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{GRAPH}/me",
                params={"fields": "id,username,name", "access_token": ACCESS_TOKEN},
            )
            data = resp.json()
            return {
                "message": f"Add this to your .env: IG_USER_ID={data.get('id')}",
                "id": data.get("id"),
                "username": data.get("username"),
                "name": data.get("name"),
            }
    except Exception as e:
        return {"error": str(e)}


class ClaimRequest(BaseModel):
    claim: str

@app.post("/test")
async def test(req: ClaimRequest):
    """Dev only — test the full fact-check pipeline without Instagram."""
    if ENVIRONMENT == "production":
        raise HTTPException(status_code=403, detail="Disabled in production")
    result = await fact_check(req.claim)
    return {
        "result": result,
        "instagram_reply_preview": build_reply(result, "testuser"),
    }