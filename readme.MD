# 🔍 FactTag — Instagram Fact-Checking Bot

Anyone on Instagram tags `@YourBotPage` in a comment or caption → FactTag reads the claim, searches the web, and replies with a sourced verdict in under 30 seconds.

---

## How It Works

```
User tags @FactTag in comment
        ↓
Instagram fires webhook → your server
        ↓
Extract & clean the claim text
        ↓
Tavily web search + Google Fact Check API
        ↓
Claude (claude-sonnet-4-6) reasons over sources
        ↓
Structured verdict: TRUE / FALSE / MISLEADING / UNVERIFIABLE
        ↓
Bot posts reply comment with verdict + source links
```

---

## Quick Start (Local Dev)

### 1. Clone & install

```bash
git clone <your-repo>
cd facttag
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys (see API Keys section below)
```

### 3. Run the server

```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Test the fact-check pipeline (no Instagram needed)

```bash
curl -X POST http://localhost:8000/test/factcheck \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Great Wall of China is visible from space"}'
```

```bash
# Preview the Instagram reply format
curl -X POST http://localhost:8000/test/format \
  -H "Content-Type: application/json" \
  -d '{"claim": "Vaccines cause autism"}'
```

### 5. Check health

```bash
curl http://localhost:8000/health
```

---

## API Keys You Need

| Service | What for | Free tier | Link |
|---------|----------|-----------|------|
| **Anthropic** | Claude — the fact-checking brain | $5 free credit | [console.anthropic.com](https://console.anthropic.com) |
| **Tavily** | Web search grounding | 1,000 searches/mo | [tavily.com](https://tavily.com) |
| **Meta/Instagram** | Read @mentions, post replies | Free | [developers.facebook.com](https://developers.facebook.com) |
| **Google Fact Check** | *(optional)* Indexed fact-checks | Free | [developers.google.com/fact-check](https://developers.google.com/fact-check/tools/api) |
| **Upstash Redis** | *(optional)* Claim caching | Free tier | [upstash.com](https://upstash.com) |

---

## Instagram / Meta Setup (Step by Step)

### Step 1 — Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com) and log in
2. Click **My Apps → Create App**
3. Choose **Business** type
4. Name it (e.g. "FactTag")

### Step 2 — Add Instagram product

1. In your app dashboard, click **Add Product**
2. Choose **Instagram** → **Set Up**
3. Under **Instagram → API setup with Instagram Login**, connect your Instagram Professional Account

### Step 3 — Get your credentials

From the Instagram settings page:
- **App Secret** → Settings → Basic → App Secret
- **Page Access Token** → Generate from Instagram → API setup
- **Instagram Account ID** → shown in API setup as "Instagram Business Account ID"

Add these to your `.env` file.

### Step 4 — Set up Webhooks

1. In your app, go to **Webhooks** → **Add Subscription** → select **Instagram**
2. Set **Callback URL** to: `https://your-deployed-url.com/webhook`
3. Set **Verify Token** to match `INSTAGRAM_VERIFY_TOKEN` in your `.env`
4. Subscribe to these fields: `mentions`, `comments`
5. Click **Verify and Save**

> ⚠️ The webhook URL must be **publicly accessible HTTPS**. Use Railway/Render for deployment, or `ngrok` for local testing.

### Step 5 — Local webhook testing with ngrok

```bash
# Install ngrok: https://ngrok.com
ngrok http 8000
# Copy the https:// URL → use as your webhook callback URL in Meta dashboard
```

---

## Deploying to Railway (Recommended)

Railway gives you free always-on hosting with HTTPS out of the box.

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Then in Railway dashboard → **Variables**, add all your `.env` values.

Your webhook URL will be: `https://your-app-name.up.railway.app/webhook`

---

## Deploying to Render (Alternative)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables in the Render dashboard

---

## Beta Testing (Dev Mode — No App Review Needed)

In Development Mode, the bot only receives webhook events from **whitelisted testers**.

### Add testers:
1. Meta Developer Dashboard → Your App → **Roles → Test Users** or **People**
2. Add Instagram accounts you want to test with (max 25)
3. Those accounts can now tag your bot and it will respond

### What works in Dev Mode:
- ✅ Someone comments `@YourBotPage can you check this: vaccines cause autism` on **your bot's own post** → bot replies with verdict
- ✅ A whitelisted tester tags `@YourBotPage` in their caption → bot receives it
- ❌ Random strangers tagging your bot → not received until App Review approved

---

## Meta App Review (Unlock Public Access)

Submit as early as Week 2. While it processes, keep building.

**What to prepare:**
1. **Screencast video** (2–3 min) showing the bot receiving a mention and posting a reply
2. **Use case description**: "Public interest fact-checking bot. Users tag @FactTag in Instagram comments to receive AI-powered fact-checks with source citations. Helps combat misinformation in real time."
3. **Privacy Policy** — host a simple page (use [privacypolicygenerator.info](https://privacypolicygenerator.info))
4. **Terms of Service** — similarly simple hosted page

**Permissions to request:**
- `instagram_basic`
- `instagram_manage_comments`
- `pages_manage_metadata`
- `pages_read_engagement` ← this is the key one for reading mentions on others' posts

---

## Project Structure

```
facttag/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings from environment variables
│   ├── models/
│   │   └── schemas.py       # Verdict enum, data models
│   ├── routes/
│   │   ├── webhook.py       # POST /webhook — receives Instagram events
│   │   └── health.py        # GET /health + test endpoints
│   └── services/
│       ├── orchestrator.py  # Main pipeline coordinator
│       ├── llm.py           # Claude fact-checking logic
│       ├── search.py        # Tavily + Google Fact Check
│       ├── instagram.py     # Graph API — read mentions, post replies
│       └── cache.py         # Redis / in-memory claim cache
├── .env.example             # Template — copy to .env
├── requirements.txt
├── railway.toml             # Railway deployment config
└── Procfile                 # Render/Heroku deployment config
```

---

## Verdict Types

| Verdict | Emoji | Meaning |
|---------|-------|---------|
| `TRUE` | ✅ | Claim is accurate and well-supported |
| `FALSE` | ❌ | Claim is contradicted by credible sources |
| `MISLEADING` | ⚠️ | True but missing context or exaggerated |
| `UNVERIFIABLE` | ❓ | Insufficient evidence either way |
| `NOT_A_CLAIM` | 💬 | Opinion, question, or non-factual statement |

---

## Example Bot Reply

```
@username
🔍 Fact Check: ❌ FALSE

The original 1998 study linking vaccines to autism was retracted in 2010.
Reviews of millions of children find no connection.

📎 Sources:
https://pubmed.ncbi.nlm.nih.gov/...
https://www.who.int/...

— Powered by @FactTag
```

---

## Security

- All webhook payloads verified via **X-Hub-Signature-256** HMAC (Meta's standard)
- API keys stored in environment variables, never in code
- Input sanitised — max 500 chars processed, @mentions/URLs stripped before LLM
- LLM only cites URLs from search results — hallucinated URLs architecturally prevented
- Rate limiting: 10 checks per user per day (configurable)

---

## Cost Estimates

| Component | Cost per fact-check |
|-----------|---------------------|
| Claude Sonnet API | ~$0.003 |
| Tavily search | ~$0.001 |
| Total | **~$0.004 per check** |

At 1,000 checks/day → ~$4/day. Well within a small project budget.

---

## Roadmap

- **v1** (now): Text claim fact-checking via @mention
- **v2**: Image/screenshot claim detection (Claude vision)
- **v3**: Public fact-check archive website
- **v4**: Multi-language support