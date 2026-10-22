# 🔑 API KEYS SETUP GUIDE
## Sirf ye 5 kaam karo — baaki sab AI karega!

---

## ⏱️ Total time: ~30-45 minutes

---

## STEP 1: Gemini API Key (5 minutes)
**FREE: 1500 requests/day**

1. Browser mein open karo: **https://aistudio.google.com**
2. Google account se login karo (manish91082@gmail.com)
3. Left menu → "Get API Key"
4. "Create API Key" button click karo
5. Key copy karo (starts with "AIza...")

---

## STEP 2: Groq API Key (2 minutes)  
**FREE: 14,400 requests/day**

1. Open: **https://console.groq.com**
2. "Sign in with Google" → manish91082@gmail.com
3. Dashboard → "API Keys" → "Create API Key"
4. Name: "ai-content-system"
5. Key copy karo (starts with "gsk_...")

---

## STEP 3: Telegram Bot (5 minutes)
**FREE: Unlimited**

1. Telegram app mein open karo
2. Search: **@BotFather**
3. `/newbot` type karo
4. Bot name: `AI Content System`
5. Username: `ai_content_hindi_bot` (ya koi bhi available)
6. Token copy karo (format: `123456789:ABC...`)

7. Apna Chat ID pane ke liye:
   - Search: **@userinfobot**
   - `/start` bhejo
   - Number note karo (e.g., `987654321`)

---

## STEP 4: Supabase (5 minutes)
**FREE: 500MB database**

1. Open: **https://supabase.com**
2. "Start your project" → GitHub se login
3. "New project" click karo
4. Name: `ai-content-system`
5. Database password set karo (save kar lo!)
6. Region: **Southeast Asia (Singapore)** — India ke closest
7. Project create hone ka wait karo (2 min)

8. Project ready hone ke baad:
   - Settings → API
   - **Project URL** copy karo (format: `https://xxx.supabase.co`)
   - **anon/public key** copy karo

9. SQL Editor mein jao → New query
10. File `config/supabase_schema.sql` ka content paste karo
11. "Run" button click karo
12. "Schema created successfully!" message aana chahiye

---

## STEP 5: Azure Speech (5 minutes)
**FREE: 500,000 characters/month**

1. Open: **https://portal.azure.com**
2. Microsoft account banao ya login karo
3. Search: "Speech Services"
4. "+ Create" click karo
5. Settings:
   - Name: `hindi-voice-ai`
   - Region: **Central India**
   - Pricing tier: **F0 (Free)**
6. "Review + create" → "Create"
7. Resource ready hone ke baad: "Keys and Endpoint"
8. **KEY 1** copy karo
9. Region note karo: `centralindia`

---

## STEP 6: Add Secrets to GitHub (10 minutes)

1. Open: **https://github.com/manish91082-coder/ai-content-system**
2. Settings → Secrets and variables → Actions
3. "New repository secret" click karo
4. Ek-ek karke yeh saare add karo:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Step 1 ki key |
| `GROQ_API_KEY` | Step 2 ki key |
| `TELEGRAM_BOT_TOKEN` | Step 3 ka token |
| `TELEGRAM_CHAT_ID` | Step 3 ka chat ID |
| `SUPABASE_URL` | Step 4 ka URL |
| `SUPABASE_KEY` | Step 4 ka anon key |
| `AZURE_SPEECH_KEY` | Step 5 ki key |
| `AZURE_SPEECH_REGION` | `centralindia` |

---

## ✅ Test Karo!

Sab secrets add hone ke baad:
1. GitHub → Actions tab
2. "🔍 Test Research Only" workflow
3. "Run workflow" → "Run workflow"
4. 5 minute mein Telegram pe message aana chahiye!

---

## 📱 YouTube API (Later — Week 1)

YouTube pe actual upload ke liye Google Cloud Console setup chahiye.
Yeh baad mein karenge — pehle basic system test karte hain.

---

## ❓ Koi problem aaye toh:
Is file mein likho ya AI ko batao — sab fix ho jayega!
