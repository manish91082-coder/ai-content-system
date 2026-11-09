# 🤖 AI Content Creation & Posting System

> **Automation Prototype** • **Hindi First** • **Free-Tier-First** • **Publishing Disabled by Default**

[![GitHub Actions](https://img.shields.io/badge/Automation-GitHub%20Actions-blue)](https://github.com/manish91082-coder/ai-content-system/actions)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## ⚠️ Verified Status — 2026-11-09

This repository is an automation prototype, not a verified revenue-generating production system.

- Research workflow has completed successfully in an observed GitHub Actions run.
- Daily content pipeline run #17 failed: Gemini authentication, Groq model/request, and daily-report defects were recorded.
- Reliability and publishing-safety fixes are being developed on the isolated branch `revenue-engine/phase-1-safety-fixes`; they are not merged into `master` and the full GitHub Actions regression run is pending.
- No checkout, customer order/fulfilment, affiliate attribution, or bank-settlement ledger is implemented.
- Verified settled revenue: **₹0** as of this audit. Views, generated assets, or pending payouts are not revenue.

## 🎯 What This Prototype Is Intended to Do

The codebase is intended to automate parts of the content workflow to:
1. 🔍 **Research** — Finds trending Hindi topics daily
2. ✍️ **Create** — Generates text, images, voice, video content
3. 📤 **Post** — Uploads to YouTube, Instagram, Facebook automatically
4. 📈 **Measure** — Store post outcomes and basic analytics where configured
5. 📊 **Report** — Sends daily Telegram summary

External account setup, API credentials, OAuth, publishing permissions, editorial review, and monetization setup still require human action.

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
| Text AI | Gemini 3.5 Flash-Lite | Free tier, account quota applies |
| Text Backup | Groq GPT-OSS 120B | Free plan, model-specific quota applies |
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
GEMINI_MODEL            → optional; defaults to gemini-3.5-flash-lite
GROQ_MODEL              → optional; defaults to openai/gpt-oss-120b
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

## 🔐 Publishing safety gate

Live publishing is blocked unless both conditions are true:
- The repository variable `PUBLISH_ENABLED` is explicitly set to `true`.
- The run is not in test mode (`TEST_MODE=false`).

Scheduled runs force test mode. Keep `PUBLISH_ENABLED` unset unless the account owner has explicitly approved live publishing and all content/platform checks have passed. API keys belong only in GitHub Actions Secrets, never in source code or issues.

## 🚀 Delivery status

- [x] Baseline repository audit
- [x] Isolated reliability and publishing-safety remediation branch created
- [x] Regression tests authored
- [ ] Full regression workflow execution and review
- [ ] Provider credentials and live free-tier inference verified
- [ ] Source provenance and editorial quality gate implemented
- [ ] Product offer, checkout, fulfilment, refund, and settlement ledger built
- [ ] First customer payment and settlement independently verified
