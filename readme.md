# 🔍 Checkr.ai — Instagram Fact-Checking Bot

An open-source Instagram bot that fact-checks claims in real time. Tag the bot in any comment → it fetches context, searches the web, and replies with a sourced verdict.

**Built with:** FastAPI · Groq (Llama 3.3 70B) · Tavily Search · Instagram Business Login API

---

## How it works

1. Someone tags your bot account in an Instagram comment
2. Bot fetches the post caption and/or parent comment for context
3. Tavily searches the web for relevant sources
4. Groq (Llama 3.3 70B) generates a verdict based on the claim + sources
5. Bot replies with verdict, explanation, and source URLs — in ~5 seconds

### Three ways to trigger it

```
# 1. Inline — put the claim in the comment
@yourbotaccount vaccines cause autism

# 2. Reply to a comment — bot fact-checks the parent comment
@yourbotaccount fact check this

# 3. On a post — bot fact-checks the caption
@yourbotaccount is this true?
```

### Verdicts
| Verdict | Emoji | Meaning |
|---------|-------|---------|
| TRUE | ✅ | Supported by sources |
| FALSE | ❌ | Contradicted by sources |
| MISLEADING | ⚠️ | Technically true but missing context |
| UNVERIFIABLE | ❓ | Not enough evidence either way |
| NOT_A_CLAIM | 💬 | Opinion or question, nothing to verify |

---

## Prerequisites

- Python 3.10+
- An Instagram **Business or Creator** account (this becomes your bot account)
- A Meta Developer account ([developers.facebook.com](https://developers.facebook.com))
- ngrok account for local dev ([ngrok.com](https://ngrok.com)) — free tier works

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/smridhiwho/facttag
cd checkr
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Get your API keys

| Key | Where | Free tier |
|-----|-------|-----------|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | 14,400 req/day, no CC |
| `TAVILY_API_KEY` | [tavily.com](https://app.tavily.com) | 1,000 searches/month |

### 3. Configure environment

```bash
cp .env.example .env
```

Fill in at minimum:
```
GROQ_API_KEY=gsk_...
TAVILY_API_KEY=tvly-...
```

### 4. Run locally

```bash
uvicorn main:app --reload
```

### 5. Test without Instagram

```bash
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Great Wall of China is visible from space"}'
```

You should get back a verdict JSON with sources. If this works, your Groq + Tavily setup is correct.

---

## Instagram Setup

### Step 1 — Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**
2. Select **Business** as the app type
3. Give it a name, enter your email, click **Create App**
4. In the left sidebar under **Products**, click **Add Product**
5. Find **Instagram** and click **Set up**
6. Choose **API setup with Instagram Login** (not Facebook Login)

### Step 2 — Connect your Instagram account

1. In the Instagram product page → **API setup with Instagram Login**
2. Under **Generate access tokens** → click **Add account**
3. Log in with your Instagram bot account and approve permissions
4. Click **Generate token** next to your account
5. Copy the token (starts with `IGAAR...` or `IGQ...`) → paste as `ACCESS_TOKEN` in `.env`

### Step 3 — Get your remaining credentials

**App Secret:**
- Meta Dashboard → **App Settings** → **Basic** → click **Show** next to App Secret
- Paste as `APP_SECRET` in `.env`

**IG User ID:**
- Start your server (`uvicorn main:app --reload`)
- Visit `http://localhost:8000/setup`
- Copy the `id` value → paste as `IG_USER_ID` in `.env`

### Step 4 — Set up ngrok

```bash
# Install ngrok, then get your free static domain:
# dashboard.ngrok.com → Domains → your free static domain

# Always start ngrok with your static domain:
ngrok http --domain=your-static-domain.ngrok-free.dev 8000
```

Using a static domain means your webhook URL never changes, even after restarts. Get yours free at [dashboard.ngrok.com](https://dashboard.ngrok.com) → Domains.

### Step 5 — Register the webhook

1. Back in Meta Dashboard → Instagram → **API setup with Instagram Login**
2. Under **Configure webhooks**:
   - **Callback URL**: `https://your-static-domain.ngrok-free.dev/webhook`
   - **Verify token**: any string you choose → also set this as `VERIFY_TOKEN` in `.env`
3. Click **Verify and save** — your terminal should log `Webhook verified ✅`

### Step 6 — Subscribe your account to webhook events

Run this once after setup (replace with your actual values):

```bash
curl -X POST "https://graph.instagram.com/v20.0/YOUR_IG_USER_ID/subscribed_apps" \
  -d "subscribed_fields=mentions,comments" \
  -d "access_token=YOUR_ACCESS_TOKEN"
```

Should return `{"success": true}`.

### Step 7 — Go Live

1. Meta Dashboard → top of page → toggle **Development** → **Live**
2. If prompted, add a Privacy Policy URL in **App Settings → Basic**
   - Free generator: [privacypolicygenerator.info](https://www.privacypolicygenerator.info)

### Step 8 — Add testers (Development mode only)

While in Development mode, only whitelisted accounts can trigger the bot:

1. Meta Dashboard → **App Roles** → **Roles** → **Add People**
2. Search by Instagram username → assign **Instagram Tester** role
3. The tester must accept the invite at: `instagram.com/developer/invitation/`

---

## Full .env reference

```bash
# App
ENVIRONMENT=development          # change to "production" when deploying

# Instagram
VERIFY_TOKEN=make_up_any_string  # must match what you enter in Meta webhook setup
APP_SECRET=                      # App Settings → Basic → App Secret
ACCESS_TOKEN=                    # Generated token from Instagram API setup page
IG_USER_ID=                      # Your bot's Instagram user ID (visit /setup to find it)

# Groq — free at console.groq.com
GROQ_API_KEY=gsk_...

# Tavily — free at tavily.com
TAVILY_API_KEY=tvly-...

# Redis (optional) — leave empty to use in-memory cache
REDIS_URL=
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Check all keys and config status |
| `/setup` | GET | Fetch your IG_USER_ID from the API |
| `/webhook` | GET | Meta webhook verification |
| `/webhook` | POST | Receive Instagram events |
| `/test` | POST | Test fact-check pipeline (dev only) |

---

## Deploy to Railway (recommended for production)

Railway gives you a permanent HTTPS URL so you don't need ngrok:

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Then in Railway dashboard → Variables, add all your `.env` values.

Update your Meta webhook Callback URL to:
```
https://your-app.up.railway.app/webhook
```

And rerun the subscribed_apps curl command with the same ACCESS_TOKEN.

---

## Limits & behaviour

- **Rate limit**: 10 fact-checks per user per day (set `RATE_LIMIT_PER_DAY` in code)
- **Cache**: identical claims are cached for 24 hours — instant response, no API calls
- **Loop prevention**: bot ignores its own comments automatically
- **Context window**: fetches up to 800 chars of post caption + parent comment
- **Token expiry**: Instagram access tokens expire in 60 days — you'll need to regenerate

---

## Troubleshooting

**Webhook not receiving events**
- Make sure app is in **Live** mode (not Development) unless testing with whitelisted accounts
- Check ngrok is running with your static domain: `ngrok http --domain=your-domain.ngrok-free.dev 8000`
- Re-run the `subscribed_apps` curl command — subscriptions sometimes need refreshing

**`No ACCESS_TOKEN — skipping reply`**
- Your `.env` ACCESS_TOKEN is empty or the server wasn't restarted after adding it

**`Invalid OAuth access token`**
- Token has expired (60 day limit) — go to Meta Dashboard → Generate token again

**Bot replies but goes into a loop**
- Pull the latest `main.py` — loop prevention is already built in via `self_ig_scoped_id` check

**Verdict is NOT_A_CLAIM when it shouldn't be**
- The comment probably didn't include enough context — try tagging with a specific claim inline
- Or make sure the post caption contains a verifiable fact (opinions in captions won't trigger a verdict)
