# 🤖 AI Content Creation & Posting System

> **Fully Automated** • **Hindi First** • **Zero Cost** • **No Manual Work**

[![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-blue)](https://github.com/manish91082-coder/ai-content-system/actions)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 🎯 What This Does

This system runs **completely automatically** to:
1. 🔍 **Research** — Finds trending Hindi topics daily
2. ✍️ **Create** — Generates text, images, voice, video content
3. 📤 **Post** — Uploads to YouTube, Instagram, Facebook automatically
4. 💰 **Monetize** — Tracks income from all platforms
5. 📊 **Report** — Sends daily Telegram summary

**User's daily work = 5 minutes (check morning report)**

## 🏗️ Architecture

```
GitHub Actions (Automation Engine)
    ↓
research_engine.py → content_generator.py → publisher.py
    ↓                       ↓                     ↓
 Gemini API           Pollinations.ai          YouTube API
 (Trending topics)   (Images + Voice)         Instagram API
                     Azure Speech              Facebook API
    ↓
Supabase Database (Track everything)
    ↓
Telegram Bot (Daily report to you)
```

## 📁 Project Structure

```
ai-content-system/
├── .github/workflows/          ← Automation (runs on GitHub)
│   ├── daily_content.yml       ← Main daily job
│   ├── research_only.yml       ← Research testing
│   └── publish_test.yml        ← Publishing testing
├── src/
│   ├── research_engine.py      ← Find trending topics
│   ├── content_generator.py    ← Generate all content
│   ├── image_generator.py      ← AI image creation
│   ├── voice_generator.py      ← Hindi voice/audio
│   ├── video_creator.py        ← Assemble video
│   ├── publisher.py            ← Post to all platforms
│   ├── database.py             ← Supabase operations
│   └── telegram_bot.py         ← Send reports
├── config/
│   ├── content_rules.json      ← Rules per platform
│   └── schedule_config.json    ← Posting schedule
├── tests/                      ← All test files
├── requirements.txt            ← Python dependencies
└── README.md                   ← This file
```

## ⚡ Tech Stack (100% Free, No Downloads)

| Component | Tool | Cost |
|-----------|------|------|
| Automation | GitHub Actions | FREE |
| Text AI | Gemini 2.0 Flash | FREE 1500/day |
| Text Backup | Groq Llama 3.1 | FREE 14400/day |
| Images | Pollinations.ai | FREE, no key |
| Voice | Azure Speech | FREE 500K/month |
| Video | FFmpeg (in Actions) | FREE |
| Database | Supabase | FREE 500MB |
| Notifications | Telegram Bot | FREE |
| Storage | Google Drive API | FREE 15GB |

## 🔐 Required Secrets (Add in GitHub → Settings → Secrets)

```
GEMINI_API_KEY          → Google AI Studio
GROQ_API_KEY            → console.groq.com
AZURE_SPEECH_KEY        → Azure Portal
AZURE_SPEECH_REGION     → e.g. centralindia
SUPABASE_URL            → Your Supabase project
SUPABASE_KEY            → Supabase anon key
TELEGRAM_BOT_TOKEN      → @BotFather
TELEGRAM_CHAT_ID        → Your chat ID
YOUTUBE_CLIENT_ID       → Google Cloud Console
YOUTUBE_CLIENT_SECRET   → Google Cloud Console
YOUTUBE_REFRESH_TOKEN   → OAuth flow
GDRIVE_CREDENTIALS      → Google Drive API JSON
```

## 🚀 Status

- [x] Phase 1: Research & Documentation ✅
- [x] Phase 2: Code Architecture ✅
- [ ] Phase 3: API Keys Setup (needs user action)
- [ ] Phase 4: First automated post
- [ ] Phase 5: Full monetization active
