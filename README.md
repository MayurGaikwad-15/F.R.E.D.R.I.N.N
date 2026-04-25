<div align="center">

```
███████╗██████╗ ███████╗██████╗ ██████╗ ██╗███╗   ██╗███╗   ██╗
██╔════╝██╔══██╗██╔════╝██╔══██╗██╔══██╗██║████╗  ██║████╗  ██║
█████╗  ██████╔╝█████╗  ██║  ██║██████╔╝██║██╔██╗ ██║██╔██╗ ██║
██╔══╝  ██╔══██╗██╔══╝  ██║  ██║██╔══██╗██║██║╚██╗██║██║╚██╗██║
██║     ██║  ██║███████╗██████╔╝██║  ██║██║██║ ╚████║██║ ╚████║
╚═╝     ╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝  ╚═══╝
```

**Federated Reasoning Engine for Digital Resource Intelligence & Neural Networks**

*An autonomous AI agent that thinks, plans, and acts — not just a chatbot.*

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-v2-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203-F55036?style=flat-square&logo=meta&logoColor=white)](https://console.groq.com/)
[![Gmail API](https://img.shields.io/badge/Gmail-API-EA4335?style=flat-square&logo=gmail&logoColor=white)](https://developers.google.com/gmail/api)
[![Google Calendar](https://img.shields.io/badge/Calendar-API-4285F4?style=flat-square&logo=google-calendar&logoColor=white)](https://developers.google.com/calendar)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-API-0A66C2?style=flat-square&logo=linkedin&logoColor=white)](https://developer.linkedin.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Academic-green?style=flat-square)](#license)

</div>

---

## What is F.R.E.D.R.I.N.N.?

F.R.E.D.R.I.N.N. is an **autonomous AI agent** — not just a chatbot. While regular chatbots answer questions, F.R.E.D.R.I.N.N. actually **takes actions** on your behalf: it reads and sends emails, creates calendar events, posts to LinkedIn, orders food, fetches files, browses the web, and monitors your inbox in real-time — all through natural language commands in a Discord channel.

### The Problem It Solves

Modern professionals juggle 5+ apps daily — Gmail, Calendar, LinkedIn, note-taking, food delivery. Each has its own interface, notifications, and context-switching tax. F.R.E.D.R.I.N.N. collapses all of these into one conversational interface.

Instead of opening Gmail → searching → reading → switching to Calendar → creating an event, you simply type:

> *"Check my emails and if there's a meeting invite, add it to my calendar."*

### How F.R.E.D.R.I.N.N. Differs from ChatGPT / Gemini

| Capability                       | ChatGPT / Gemini | F.R.E.D.R.I.N.N.             |
| -------------------------------- | ---------------- | ---------------------------- |
| Send real emails                 | ✗                | ✅ Gmail API                  |
| Create calendar events           | ✗                | ✅ Google Calendar API        |
| Post to LinkedIn                 | ✗                | ✅ LinkedIn API               |
| Monitor inbox automatically      | ✗                | ✅ Every 60 seconds           |
| Free to run                      | $20+/month       | ✅ Groq free tier             |
| Runs locally on your machine     | ✗ Cloud only     | ✅ 100% local                 |
| Safety gate on dangerous actions | ✗                | ✅ Human-in-the-Loop approval |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        YOU  (Discord)                        │
│                  Desktop / Mobile / Browser                  │
└──────────────────────────────┬───────────────────────────────┘
                               │ WebSocket
┌──────────────────────────────▼───────────────────────────────┐
│                   DISCORD BOT  discord_main.py               │
│                                                              │
│   ┌─────────────────┐   ┌─────────────────┐                 │
│   │  File Intent    │   │  Food Intent    │                 │
│   │  Detector       │   │  Detector       │                 │
│   └────────┬────────┘   └────────┬────────┘                 │
│            │                     │                           │
│            ▼                     ▼                           │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   Tool Router                       │   │
│   │   8 groups · keyword-matched · ~80% token savings   │   │
│   └──────────────────────────┬──────────────────────────┘   │
│                               │                              │
│   ┌───────────────────────────▼──────────────────────────┐  │
│   │              Groq LLM  ·  ReAct Loop                 │  │
│   │          LLaMA 3.1 8B (fast)  /  3.3 70B (deep)     │  │
│   └───────────────────────────┬──────────────────────────┘  │
│                               │                              │
│   ┌───────────────────────────▼──────────────────────────┐  │
│   │           Human-in-the-Loop Safety Gate              │  │
│   │         5 dangerous tools  ·  ✅ / ❌ buttons         │  │
│   └───────────────────────────┬──────────────────────────┘  │
│                               │                              │
│   ┌───────────────────────────▼──────────────────────────┐  │
│   │                Executor  (39+ tools)                 │  │
│   └──────┬──────────┬──────────┬──────────┬─────────────┘  │
└──────────┼──────────┼──────────┼──────────┼─────────────────┘
           │          │          │          │
    ┌──────▼──┐ ┌─────▼───┐ ┌───▼────┐ ┌──▼──────┐ ┌────────┐
    │ Gmail   │ │Calendar │ │LinkedIn│ │Playwright│ │ SQLite │
    │13 tools │ │ 7 tools │ │ 1 tool │ │ 3 tools │ │ memory │
    └─────────┘ └─────────┘ └────────┘ └─────────┘ └────────┘
```

**Every message follows this pipeline:**

1. **File intent detector** — does the user want a file? → delivers it directly, bypasses LLM
2. **Food intent detector** — does the user want food? → pure regex, zero LLM cost
3. Everything else → **Tool Router** selects relevant tools → **Groq LLM** reasons → **Executor** runs tools → results feed back into LLM → repeat until done (max 10 iterations)

---

## Modules

### 📬 Module 1 — Gmail Inbox Engine (23 tools)

`skills/mail_ops.py` · `skills/inbox_engine.py` · `summarizer.py`

| Capability         | How to trigger                         | What happens                                               |
| ------------------ | -------------------------------------- | ---------------------------------------------------------- |
| Read emails        | `"Check my inbox"`                     | Lists unread emails with subject, sender, preview          |
| Send email         | `"Email Sarah about the meeting"`      | Drafts → HITL approval → sends                             |
| Smart drafting     | `"Reply to the budget email agreeing"` | Analyzes your sent-email style, drafts in your tone        |
| Inbox triage       | `"Clean up my inbox"`                  | Deletes spam, archives promos, flags VIP emails            |
| Morning brief      | `"Morning briefing"`                   | Categorized summary with action items                      |
| Follow-up tracking | `"Any unanswered emails?"`             | Finds sent emails with no reply after 3 days, drafts bumps |
| Real-time alerts   | Automatic (every 60s)                  | Polls Gmail, summarizes new arrivals, pushes to Discord    |
| VIP contacts       | `"Add Sarah as VIP"`                   | VIP emails get starred + IMPORTANT label automatically     |

### 📅 Module 2 — Google Calendar (7 tools)

`skills/calendar_ops.py`

| Capability         | How to trigger                                                                  |
| ------------------ | ------------------------------------------------------------------------------- |
| Create events      | `"Schedule a meeting with Alex Tuesday 3 PM"` — auto-generates Google Meet link |
| List events        | `"What's on my calendar today?"`                                                |
| Conflict detection | `"Do I have any scheduling conflicts?"` — finds overlaps, suggests reschedules  |
| Day prep           | `"Prep me for today's meetings"` — pulls relevant emails from attendees         |
| Focus blocks       | `"Block 2 hours of deep work tomorrow morning"` — marks as busy                 |
| Find free slots    | `"When am I free next week for a 30-min call?"`                                 |
| Delete events      | `"Cancel the 4 PM meeting"` — requires HITL approval                            |

### 🧠 Module 3 — Research & Intelligence (6 tools)

`skills/research_ops.py`

- **Daily intelligence briefs** — tracks your topics, scrapes the web, delivers bullet-point news
- **Deep-dive research** — multi-angle reports: Executive Summary, Key Players, Future Outlook
- **Bookmark queue** — save URLs for batch reading later
- **Content summarization** — condense any article or long text

### 📝 Module 4 — Summarization Engine (5 summarizers)

`summarizer.py` · dual-model strategy: LLaMA 3.1 8B (speed) + LLaMA 3.3 70B (depth)

| Summarizer                | Trigger                              |
| ------------------------- | ------------------------------------ |
| `summarize_text`          | paste any long text                  |
| `summarize_url`           | `"Summarize this article: [URL]"`    |
| `summarize_file`          | upload a PDF/TXT in Discord          |
| `summarize_bullet_points` | fast bullet breakdown of any content |
| `summarize_email`         | summarize a Gmail message by ID      |

### 🔗 Module 5 — LinkedIn Integration (1 tool)

`skills/linkedin_ops.py` · `auth_linkedin.py`

OAuth 2.0 with automatic token management. Type `/linkedinpost [content]` → preview embed → ✅ Approve / ❌ Deny buttons → publishes only on approval.

### 🍛 Module 6 — Food Delivery Simulation (zero LLM calls)

`skills/food_ops.py` · pure regex, <1ms response, zero API cost

```
You:  "Order two chicken biryanis and a coke"
       ↓
      Regex parser → [{qty: 2, item: "Chicken Biryani"}, {qty: 1, item: "Coke"}]
       ↓
      Confirmation embed: itemized bill (subtotal + 5% GST + ₹30 delivery)
       ↓
      ✅ Confirm → Order ID + ETD + receipt embed
      ❌ Cancel  → Cancellation message
```

25 menu items across 4 categories. `MockDeliveryAPI` class is a drop-in replacement for Swiggy/Zomato when those APIs become available.

### 📁 Module 7 — Smart File Transfer (Discord + Google Drive)

`file_sender.py` · `demo_file_ops.py` · `authorize_drive.py`

**Natural language file retrieval:**

```
"Get me the config file"      →  sends config.txt
"Grab the meeting schedule"   →  sends meeting_schedule.json
"I want the system log file"  →  sends system_log.txt
```

**Smart routing by file size:**
- **< 25 MB** → uploaded directly to Discord (instant download)
- **≥ 25 MB** → uploaded to Google Drive → View link + Direct Download link

**3-layer filename matching:**
1. Exact match: `"config.txt"` → `config.txt` ✅
2. Name without extension: `"grab the config"` → `config.txt` ✅
3. Fuzzy word match: `"meeting schedule"` → `meeting_schedule.json` ✅

### 🌐 Module 8 — Web Automation (3 tools)

`skills/browser_ops.py` · headless Chromium via Playwright

- Navigate any web page and extract full DOM
- Click elements by CSS selector
- Type text into input fields

---

## The ReAct Loop

ReAct = **Rea**soning + **Act**ing. The agent doesn't just answer — it thinks, acts, observes, and repeats.

```
User: "Find emails from Alex and add any meetings to my calendar"

┌──────────────────────────────────────────────────────────┐
│  THINK: I need Alex's emails first, then check for      │
│  meeting details before touching the calendar.          │
│                                                          │
│  ACT:  search_emails(query="from:alex")                 │
└──────────────────────────┬───────────────────────────────┘
                           │  result injected
┌──────────────────────────▼───────────────────────────────┐
│  OBSERVE: 3 emails found. Email #2 mentions             │
│  "meeting Thursday 2 PM".                               │
│                                                          │
│  ACT:  create_calendar_event(                           │
│           title="Meeting with Alex",                    │
│           datetime="Thursday 2:00 PM")                  │
└──────────────────────────┬───────────────────────────────┘
                           │  result injected
┌──────────────────────────▼───────────────────────────────┐
│  OBSERVE: Event created. No further actions needed.     │
│                                                          │
│  ANSWER: "Found 3 emails from Alex. I've added the      │
│  Thursday 2 PM meeting to your calendar with a          │
│  Google Meet link."                                     │
└──────────────────────────────────────────────────────────┘
```

Maximum 10 tool loops per message. After that the agent gracefully concludes.

---

## Dynamic Tool Routing

**The problem:** Sending all 39 tool schemas to the LLM costs ~8,000 tokens per request. On Groq's free tier (6,000 TPM), that allows barely 1 request/minute.

**The solution:** `tool_router.py` analyzes each message and injects only the relevant tool subset.

```
User:  "Check my emails"
        ↓
       keywords detected: ["email", "inbox"]
        ↓
       groups matched: core + email_basic + inbox_engine
        ↓
       16 tools injected instead of 39
       (~3,000 tokens instead of ~8,000)
        ↓
       Result: 5× token savings = 4+ requests/minute on free tier
```

**The 8 tool groups:**

| Group          | Trigger keywords                   |
| -------------- | ---------------------------------- |
| `core`         | *(always included)*                |
| `email_basic`  | email, mail, send, inbox           |
| `inbox_engine` | triage, spam, morning, follow up   |
| `calendar`     | calendar, schedule, meeting, event |
| `research`     | research, news, bookmark           |
| `summarizer`   | summarize, summary, tldr           |
| `browser`      | browse, website, click             |
| `linkedin`     | linkedin, post, publish            |

---

## Human-in-the-Loop Safety

Five tools are classified as **dangerous** and require explicit approval before execution:

| Tool                    | Risk                              |
| ----------------------- | --------------------------------- |
| `send_email`            | Could send to the wrong recipient |
| `delete_email`          | Permanent data loss               |
| `write_local_file`      | Could overwrite important files   |
| `delete_calendar_event` | Could remove critical meetings    |
| `post_to_linkedin`      | Public — cannot be retracted      |

**Approval flow:**

```
LLM selects dangerous tool
    ↓
Bot interrupts execution
Shows approval embed (full details: recipient, subject, body)
    ↓
✅ Approve  →  tool executes, result shown
❌ Deny     →  blocked (emails are auto-saved to Drafts instead)
```

All other tools (search, list, summarize, read) execute **instantly** without interruption.

---

## Tech Stack

| Layer            | Technology                           | Reason                                        |
| ---------------- | ------------------------------------ | --------------------------------------------- |
| LLM Engine       | Groq API — LLaMA 3.1 8B + 3.3 70B    | Free tier, 200+ tokens/sec, open-weight       |
| Chat Interface   | discord.py v2                        | Rich embeds, buttons, views, mobile + desktop |
| Email            | Gmail API (google-api-python-client) | Full inbox control via OAuth 2.0              |
| Calendar         | Google Calendar API                  | Shared OAuth with Gmail, Google Meet links    |
| Social           | LinkedIn v2 API + OAuth 2.0          | Direct UGC post publishing                    |
| File Transfer    | Google Drive API                     | Fallback for files ≥ 25 MB                    |
| Food Parsing     | Custom regex engine                  | Zero LLM dependency, <1 ms                    |
| Web Browsing     | Playwright (headless Chromium)       | Full DOM interaction                          |
| Memory           | SQLite3 (WAL mode)                   | Persistent chat history, concurrent reads     |
| Summarization    | Groq dual-model                      | 5 specialized summarizers                     |
| Containerization | Docker + Docker Compose              | Isolated sandbox, one-command deploy          |
| Language         | Python 3.12 (async/await throughout) | Modern async patterns, rich ecosystem         |

---

## Project Structure

```
F.R.E.D.R.I.N.N./
│
├── discord_main.py        # Entry point — Discord bot, message routing,
│                          # ReAct loop, HITL views, email polling
│
├── executor.py            # Tool dispatcher — routes 39+ tool names
│                          # to their implementing functions
│
├── tool_router.py         # Intent analysis — 8 tool groups, keyword
│                          # matching, ~80% token savings per request
│
├── memory.py              # Persistence — SQLite (WAL mode), chat
│                          # history CRUD, background compaction
│
├── summarizer.py          # 5 summarizers: text, URL, file, bullets,
│                          # email. Dual-model (8B fast + 70B deep)
│
├── file_sender.py         # Smart routing: Discord (<25MB) or
│                          # Google Drive (≥25MB) with shareable links
│
├── demo_file_ops.py       # /demo_list, /demo_read, /demo_write
│
├── SOUL.md                # System prompt — personality, routing
│                          # rules, display formats, constraints
│
├── auth_gmail.py          # OAuth 2.0 — Gmail + Calendar
├── auth_linkedin.py       # OAuth 2.0 — LinkedIn
├── authorize_drive.py     # OAuth 2.0 — Google Drive
│
├── skills/
│   ├── system_ops.py      # Core tools + all 39 tool schemas
│   ├── mail_ops.py        # Gmail: search, send, draft
│   ├── inbox_engine.py    # Advanced: triage, brief, smart draft,
│   │                      # follow-ups, VIP, labels, archive, delete
│   ├── calendar_ops.py    # Calendar: CRUD, conflicts, focus time,
│   │                      # free slots, meeting prep, Meet links
│   ├── research_ops.py    # Research: intel briefs, deep dive, bookmarks
│   ├── browser_ops.py     # Playwright: navigate, click, type, DOM
│   ├── linkedin_ops.py    # LinkedIn: UGC post publishing
│   └── food_ops.py        # 25-item menu, NL parser, mock API,
│                          # order flow, billing with GST
│
├── demo_files/            # Sandboxed dummy files for safe demos
│   ├── system_log.txt
│   ├── user_notes.txt
│   ├── config.txt
│   ├── meeting_schedule.json
│   ├── team_contacts.csv
│   └── project_report_summary.txt
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                   # API keys — never committed
```

---

## Setup & Installation

### Prerequisites

- Python 3.12+
- A Discord account with a bot created ([Discord Developer Portal](https://discord.com/developers/applications))
- A Google Cloud project with Gmail API + Calendar API enabled
- A Groq API key — free at [console.groq.com](https://console.groq.com)

### Step 1 — Clone & install

```bash
git clone https://github.com/your-username/F.R.E.D.R.I.N.N..git
cd F.R.E.D.R.I.N.N.

pip install -r requirements.txt
pip install discord.py

# Install headless browser for web automation
playwright install chromium
```

### Step 2 — Configure environment

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
DISCORD_BOT_TOKEN=MTxxxxxxxxxxxxxxxxxxxxxxxxxx
DISCORD_USER_ID=123456789012345678

# LinkedIn (optional)
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_ACCESS_TOKEN=your_access_token

# Google Drive — place credentials.json in project root, then run authorize_drive.py
```

### Step 3 — Authenticate APIs

```bash
# Gmail + Calendar (opens browser for Google OAuth, generates token.json)
python auth_gmail.py

# LinkedIn (optional)
python auth_linkedin.py

# Google Drive (optional — for file transfers > 25 MB)
python authorize_drive.py
```

### Step 4 — Configure your Discord bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**
2. **Bot** tab → Reset Token → copy to `.env`
3. Enable **Privileged Gateway Intents**: Message Content Intent + Server Members Intent
4. **OAuth2 → URL Generator** — Scopes: `bot` — Permissions: Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions
5. Open the generated URL to invite the bot to your server
6. Enable Developer Mode → right-click your username → Copy ID → paste as `DISCORD_USER_ID`

---

## Running

### Local (development)

```bash
# Kill any stale instances first
taskkill /F /IM python3.12.exe   # Windows
# pkill -f discord_main.py       # Linux / macOS

python discord_main.py
```

Expected output:

```
INFO - Discord Bot F.R.E.D.R.I.N.N.#XXXX has connected to Discord!
INFO - Running proactive routine heartbeat...
```

### Docker (recommended for demos and deployment)

```bash
# Build and start in background
docker compose up --build -d

# Stream logs
docker compose logs -f

# Stop
docker compose down
```

Docker confines all file operations to `/app/demo_files/` inside the container, with a volume mount to `./demo_files/` on your host. Drop any file there and it's instantly accessible from Discord — no restart needed.

---

## Commands Reference

### Slash Commands

| Command                         | Description                                         |
| ------------------------------- | --------------------------------------------------- |
| `/menu`                         | Display the full food menu (25 items, 4 categories) |
| `/order [items]`                | Place a food order: `/order 2 biryanis and a coke`  |
| `/linkedinpost [content]`       | Draft a LinkedIn post with HITL approval            |
| `/getfile [filename]`           | Fetch a file: `/getfile config.txt`                 |
| `/demo_list`                    | List all files in the sandbox                       |
| `/demo_read [filename]`         | Read a file's contents into chat                    |
| `/demo_write [filename] [text]` | Append timestamped text to a file                   |

### Natural Language

| You say                                         | F.R.E.D.R.I.N.N. does                              |
| ----------------------------------------------- | -------------------------------------------------- |
| `"Check my inbox"`                              | Lists recent unread emails                         |
| `"Send an email to sarah@example.com about..."` | Drafts → HITL → sends                              |
| `"What's on my calendar today?"`                | Lists today's events                               |
| `"Schedule a meeting with Alex Tuesday 3 PM"`   | Creates event + Google Meet link                   |
| `"Summarize this article: [URL]"`               | Extracts and condenses the page                    |
| `"Clean up my inbox"`                           | Triages: deletes spam, archives promos, flags VIPs |
| `"Morning briefing"`                            | Full digest: emails + calendar + intelligence      |
| `"Get me the config file"`                      | Finds and sends `config.txt`                       |
| `"Order paneer tikka and two cokes"`            | Parses order → confirmation → receipt              |
| `"Research the latest in AI agents"`            | Deep-dive report with structured sections          |
| *(upload any file)*                             | Auto-detects upload → summarizes the document      |

---

## Troubleshooting

| Symptom                            | Cause                           | Fix                                                   |
| ---------------------------------- | ------------------------------- | ----------------------------------------------------- |
| Triple / duplicate responses       | Multiple bot processes running  | `taskkill /F /IM python3.12.exe` then restart         |
| `429 Too Many Requests`            | Groq rate limit (6,000 TPM)     | Wait 60 seconds, or upgrade to Groq Dev tier          |
| `PyNaCl not installed` warning     | Voice support unavailable       | Cosmetic warning — safe to ignore (voice unused)      |
| `database is locked`               | SQLite concurrent access        | Already mitigated with WAL mode                       |
| Food handler catches file requests | `"I want"` triggers food intent | Fixed: file intent detector runs before food detector |
| Drive link doesn't open            | Wrong link format               | Fixed: uses `?usp=sharing` + direct download link     |
| Bot not responding                 | Wrong `DISCORD_USER_ID`         | Verify the ID in `.env` matches your Discord account  |

---

## Roadmap

- [ ] Multi-user support — per-user auth, isolated memory stores
- [ ] WhatsApp interface — WhatsApp Business API integration
- [ ] Real food delivery — replace `MockDeliveryAPI` with Swiggy / Zomato
- [ ] Voice commands — Whisper STT + TTS for hands-free operation
- [ ] Streaming responses — token-by-token output for faster perceived latency
- [ ] Analytics dashboard — web UI for email patterns, calendar stats
- [ ] Plugin marketplace — community skill modules (Notion, Jira, Spotify, GitHub)
- [ ] Mobile companion app — push notifications + offline mode

---



**Guide:** Mr. Saviour Fargose

**Department:** Artificial Intelligence & Machine Learning
Universal College of Engineering, Vasai

---

## License

Developed as part of the T.E. Mini-Project 2A (Semester V)
University of Mumbai · Academic Year 2025–2026

---

<div align="center">

*Built with Python, Groq, Discord.py — and a lot of late-night debugging.*

</div>
