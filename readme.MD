# 🔍 Checkr.ai — Instagram Fact-Checking Bot

Tag `@CheckrAI` in any Instagram comment → the bot reads the claim, searches the web, and replies with a sourced verdict.

**Stack:** FastAPI · GPT-4o-mini · Tavily · Meta Graph API

---

## Files

```
checkr/
├── main.py          ← entire app (one file)
├── .env.example     ← copy to .env and fill in keys
├── requirements.txt
├── railway.toml     ← deploy to Railway in one command
└── .gitignore
```

---

## Local Setup

```bash
# 1. Install deps
pip install -r requirements.txt

# 2. Set up env
cp .env.example .env
# Fill in OPENAI_API_KEY and TAVILY_API_KEY at minimum

# 3. Run
uvicorn main:app --reload

# 4. Test the fact-check pipeline (no Instagram needed)
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"claim": "The Great Wall of China is visible from space"}'
```

---

## API Keys

| Key | Where to get | Free tier |
|-----|-------------|-----------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/api-keys) | Pay per use (~$0.001/check) |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | 1,000 searches/month |
| `ACCESS_TOKEN` | Meta Developer Dashboard | Free |
| `APP_SECRET` | Meta Developer Dashboard | Free |
| `PAGE_ID` | Meta Developer Dashboard | Free |

---

## Instagram / Meta Setup

### 1. Create a Meta Developer App
- [developers.facebook.com](https://developers.facebook.com) → Create App → Business type
- Add the **Instagram** product

### 2. Connect your Instagram Professional Account
- Instagram → API Setup → connect your account
- Copy: **App Secret**, **Page Access Token**, **Instagram Business Account ID** → paste into `.env`

### 3. Register the Webhook
- Webhooks → Add Subscription → Instagram
- Callback URL: `https://your-deployed-url.com/webhook`
- Verify Token: matches `VERIFY_TOKEN` in your `.env`
- Subscribe to fields: `mentions`, `comments`

### 4. Test locally with ngrok
```bash
ngrok http 8000
# Use the https:// URL as your webhook callback URL
```

---

## Deploy to Railway

```bash
npm install -g @railway/cli
railway login
railway init
railway up
```

Add all `.env` values in the Railway dashboard → Variables.

Your webhook URL: `https://your-app.up.railway.app/webhook`

---

## Beta (Dev Mode — No App Review)

Works immediately for up to **25 whitelisted testers**:
- Meta Dashboard → Roles → Add testers (Instagram accounts)
- Those accounts can tag `@CheckrAI` and the bot will respond
- Random strangers tagging you → not received until App Review is approved

**Submit App Review in Week 2.** Use case: *"Public interest fact-checking bot."* Takes 1–4 weeks.

---

## Verdicts

| Label | Emoji | Meaning |
|-------|-------|---------|
| `TRUE` | ✅ | Accurate, well-sourced |
| `FALSE` | ❌ | Contradicted by sources |
| `MISLEADING` | ⚠️ | True but missing context |
| `UNVERIFIABLE` | ❓ | Insufficient evidence |
| `NOT_A_CLAIM` | 💬 | Opinion / question — can't be checked |

---

## Example Reply

```
@username
🔍 Fact Check: ❌ FALSE

The original 1998 study linking vaccines to autism was retracted.
Large-scale reviews find no connection.

📎 Sources:
https://pubmed.ncbi.nlm.nih.gov/...
https://www.who.int/...

— Checkr.ai
```
