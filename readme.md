# 🔍 Project Atlas (Beta)
**Real-time fact-checking for Instagram comments**

Project Atlas is an AI-powered Instagram bot designed to combat misinformation in public discourse. Tag the bot in any thread, and it will analyze the claim, search for credible sources, and reply with a verified fact-check in seconds.

> [!IMPORTANT]
> **Beta Status:** This project is currently in private beta during the **Meta App Review** process. Public access is currently limited to whitelisted accounts.

---

## 🚀 Core Features

- **Contextual Awareness:** Reads parent comments and post captions to understand the nuance behind a claim.
- **Live Verification:** Searches the web in real-time for current, credible information.
- **Automated Citations:** Provides a clear verdict with links to high-authority sources.
- **Performance Optimized:** Uses intelligent caching for recurring claims to provide near-instant replies.
- **Abuse Prevention:** Implements rate limiting and spam filtering to maintain thread integrity.

### **Tech Stack**
- **Framework:** FastAPI
- **LLM:** Groq (Llama 3.3 70B)
- **Search:** Tavily Search
- **Platform:** Instagram Business API

---

## 🛠 How to Use (Beta)

Tag the bot handle (e.g., `@bot_handle`) in a comment. The system supports three primary interaction patterns:

### 1. Inline Claims
Submit a claim directly within your comment.
> **Example:** `@bot_handle the moon is made of green cheese`

### 2. Reply to a Comment
Reply to a specific comment with just the tag. The bot will automatically verify the content of the parent comment.
> **Example:** `@bot_handle fact check this`

### 3. Verify Post Captions
Comment on a post where the main caption contains a claim.
> **Example:** `@bot_handle is this true?`

---

## ⚖️ Verdict Types



| Emoji | Label | Meaning |
|:---:|:--- |:--- |
| ✅ | **TRUE** | The claim is accurate and supported by credible sources. |
| ❌ | **FALSE** | The claim is contradicted by reliable sources. |
| ⚠️ | **MISLEADING** | The claim is partly true but lacks critical context. |
| ❓ | **UNVERIFIABLE** | Insufficient evidence exists to confirm or deny the claim. |
| 💬 | **NOT_A_CLAIM** | The input is an opinion, question, or subjective statement. |

---

## 📝 Example Interaction

**User:** `@username`
**Project Atlas:**
> 🔍 **Fact Check:** ❌ **FALSE**
>
> The original 1998 study linking vaccines to autism was retracted, and large-scale reviews involving millions of children have found no link.
>
> **Sources:**
> - [Reuters - Fact Check Link](https://www.reuters.com/...)
> - [World Health Organization - Vaccine Safety](https://www.who.int/...)
>
> *— Project Atlas (Beta)*

---

## 🛡 Safety & Responsible Use

- **Anti-Hallucination:** The bot is strictly constrained to cite only links returned from live web searches.
- **Privacy:** Personal data and metadata within comments are ignored and never stored.
- **Human-Centric:** Designed to provide context for better discussion, not to act as a final arbiter of truth.

---

## 🗺 Roadmap

- [ ] **Public Launch:** Full release following Meta App Review.
- [ ] **Visual Verification:** Support for checking claims within images and screenshots.
- [ ] **Multilingual Support:** Fact-checking capabilities for non-English claims.
- [ ] **Public Archive:** A searchable database of previously verified claims.
- [ ] **Creator Tools:** Dashboards for influencers and journalists to monitor their comment sections.

---

## 📬 Contact

For beta participants reporting bugs or users requesting access, please reach out via the **Project Repository Issues** or the official **Instagram page** linked to the bot.
