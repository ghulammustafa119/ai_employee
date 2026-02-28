# AI Employee - Personal Autonomous Task Processor

A local-first, file-based AI employee that reads tasks, generates plans, executes them, and logs everything automatically. Features watchers for Gmail/WhatsApp, human-in-the-loop approval, social media posting (LinkedIn, Facebook, Instagram, Twitter), Odoo accounting, CEO Briefing, and autonomous task loops.

## Architecture

```
vault/
├── Inbox/               ← Raw incoming items from watchers
├── Needs_Action/        ← Tasks to be processed
├── Plans/               ← AI-generated plans
├── Pending_Approval/    ← Sensitive tasks awaiting human approval
├── Approved/            ← Human-approved actions
├── Rejected/            ← Human-rejected actions
├── Done/                ← Completed tasks + output deliverables
├── Logs/                ← JSON + audit logs
├── Briefings/           ← Weekly CEO briefings
├── Accounting/          ← Financial data
├── In_Progress/         ← Ralph Wiggum loop state
├── Dashboard.md         ← Live system status
├── Business_Goals.md    ← Revenue targets & metrics
└── Company_Handbook.md  ← Rules of engagement
```

### Flow

```
[Gmail/WhatsApp Watcher] → Needs_Action/task.md
  → AI reads task → Detects domain (personal/business)
    → Is it sensitive?
      YES → Pending_Approval/ (wait for human)
            → Move to Approved/ → AI executes → Done/
            → Move to Rejected/ → Logged
      NO  → Plans/PLAN_task.md → Done/OUTPUT_task.md → Done/
    → Dashboard.md updated
    → Logs/date.json updated
```

## Tech Stack

- **Language:** Python 3.13+, Node.js v24+
- **Package Manager:** UV (Python), npm (Node.js)
- **LLM:** Groq (Llama 3.3 70B) - Free tier
- **Storage:** Local Markdown files (vault)
- **Watchers:** Gmail API, Playwright (WhatsApp)
- **MCP Servers:** Email (Gmail), Odoo Accounting (mock)
- **Social Media:** Facebook, Instagram, Twitter (mock), LinkedIn (Playwright)

## Setup

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. Install Dependencies

```bash
uv sync
cd mcp_servers/email_server && npm install
cd mcp_servers/odoo_server && npm install
```

### 3. Install Playwright Browsers (for WhatsApp/LinkedIn)

```bash
uv run playwright install chromium
```

### 4. Get API Keys

- **Groq (required):** https://console.groq.com/keys (free)
- **Gmail (optional):** Google Cloud Console → Gmail API → OAuth credentials
- **LinkedIn (optional):** Set email/password in .env
- **Facebook/Instagram (optional):** Meta Graph API access token
- **Twitter (optional):** Twitter API v2 keys

### 5. Configure .env

```
GROQ_API_KEY=your_groq_api_key_here
VAULT_PATH=vault
CHECK_INTERVAL=10
DRY_RUN=false

# Gmail Watcher
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
GMAIL_CHECK_INTERVAL=120

# WhatsApp Watcher
WHATSAPP_SESSION_PATH=.whatsapp_session
WHATSAPP_CHECK_INTERVAL=30
WHATSAPP_KEYWORDS=urgent,asap,invoice,payment,help

# LinkedIn
LINKEDIN_EMAIL=
LINKEDIN_PASSWORD=

# Facebook / Instagram (Meta Graph API)
META_ACCESS_TOKEN=
META_PAGE_ID=
META_INSTAGRAM_ACCOUNT_ID=

# Twitter / X
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=

# Odoo Community
ODOO_URL=http://localhost:8069
ODOO_DB=odoo
ODOO_USERNAME=admin
ODOO_PASSWORD=admin

# CEO Briefing
BRIEFING_DAY=Monday
```

## Usage

### Run the AI Employee (Full Runner)

```bash
uv run python -m src.runner
```

### Run All Services

```bash
./scripts/start_all.sh
```

### Run Gmail Watcher

```bash
uv run python -m src.watchers.gmail_watcher
```

### Run WhatsApp Watcher

```bash
uv run python -m src.watchers.whatsapp_watcher
```

### Generate Social Media Posts

```bash
uv run python -m src.linkedin_poster
uv run python test_social_approval.py
```

### Generate CEO Briefing

```bash
uv run python -m src.ceo_briefing
```

### Start Ralph Wiggum Loop

```bash
./scripts/ralph_loop.sh "Process all files in Needs_Action" --max-iterations 10
```

### Approval Workflow

1. Sensitive tasks automatically go to `vault/Pending_Approval/`
2. Review the file
3. Move to `vault/Approved/` to approve → AI executes it
4. Move to `vault/Rejected/` to reject → Logged and archived

## Features

### Bronze Tier
- **Plan + Execute** — AI generates a plan AND produces the actual deliverable
- **Duplicate Protection** — Same task won't be processed twice
- **Error Handling** — Failed tasks stay in Needs_Action for retry
- **Dry Run Mode** — Set `DRY_RUN=true` to test without LLM calls
- **Audit Logging** — Every action logged with timestamp in JSON

### Silver Tier
- **Gmail Watcher** — Monitors unread important emails, creates tasks
- **WhatsApp Watcher** — Monitors messages with keywords via Playwright
- **Human-in-the-Loop** — Sensitive actions require approval before execution
- **LinkedIn Auto-Poster** — AI generates business posts, approval required
- **Email MCP Server** — Send/draft/search emails via MCP protocol
- **Live Dashboard** — Auto-updated Dashboard.md with system status
- **Company Handbook** — Configurable rules for AI behavior

### Gold Tier
- **Facebook Integration** — AI-generated posts with approval workflow (mock)
- **Instagram Integration** — AI-generated captions with approval workflow (mock)
- **Twitter/X Integration** — AI-generated tweets with approval workflow (mock)
- **Odoo Accounting** — Invoice, payment, contact management via MCP (mock)
- **CEO Briefing** — Weekly autonomous business audit with AI-generated report
- **Cross-Domain Routing** — Auto-detects personal vs business tasks
- **Error Recovery** — Retry with exponential backoff, graceful degradation
- **Structured Audit Logging** — Enhanced logging with timing and monthly summaries
- **Ralph Wiggum Loop** — Autonomous multi-step task completion
- **Architecture Docs** — Full system documentation (ARCHITECTURE.md)

## Project Structure

```
ai_employee/
├── pyproject.toml
├── .env                          # Secrets (gitignored)
├── README.md
├── ARCHITECTURE.md               # System architecture docs
├── documents.txt                 # Hackathon spec
├── vault/
│   ├── Needs_Action/
│   ├── Plans/
│   ├── Pending_Approval/
│   ├── Approved/
│   ├── Rejected/
│   ├── Done/
│   ├── Logs/
│   ├── Inbox/
│   ├── Briefings/
│   ├── Accounting/
│   ├── Dashboard.md
│   ├── Business_Goals.md
│   └── Company_Handbook.md
├── src/
│   ├── __init__.py
│   ├── config.py                 # Paths, settings, env loading
│   ├── brain.py                  # AI logic + approval + domain routing
│   ├── runner.py                 # Main polling loop (orchestrator)
│   ├── dashboard.py              # Dashboard generator
│   ├── linkedin_poster.py        # LinkedIn post generator
│   ├── odoo_client.py            # Odoo accounting client (mock)
│   ├── ceo_briefing.py           # Weekly CEO briefing generator
│   ├── ralph_wiggum.py           # Autonomous task loop
│   ├── retry_handler.py          # Error recovery & retry logic
│   ├── audit_logger.py           # Structured audit logging
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py       # Abstract base class
│   │   ├── gmail_watcher.py      # Gmail monitoring
│   │   └── whatsapp_watcher.py   # WhatsApp monitoring
│   └── social_media/
│       ├── __init__.py
│       ├── facebook_poster.py    # Facebook (mock)
│       ├── instagram_poster.py   # Instagram (mock)
│       └── twitter_poster.py     # Twitter/X (mock)
├── mcp_servers/
│   ├── email_server/
│   │   ├── package.json
│   │   └── index.js              # Email MCP server
│   └── odoo_server/
│       ├── package.json
│       └── index.js              # Odoo accounting MCP server (mock)
└── scripts/
    ├── start_all.sh              # Start all services
    ├── stop_all.sh               # Stop all services
    ├── setup_cron.sh             # Configure cron jobs
    └── ralph_loop.sh             # Start Ralph Wiggum loop
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Groq API key (required) |
| `VAULT_PATH` | `vault` | Path to vault directory |
| `CHECK_INTERVAL` | `10` | Seconds between folder checks |
| `DRY_RUN` | `false` | Skip LLM calls and file moves |
| `GMAIL_CREDENTIALS_PATH` | `credentials.json` | Gmail OAuth credentials |
| `GMAIL_CHECK_INTERVAL` | `120` | Gmail check interval (seconds) |
| `WHATSAPP_SESSION_PATH` | `.whatsapp_session` | WhatsApp browser session |
| `WHATSAPP_CHECK_INTERVAL` | `30` | WhatsApp check interval (seconds) |
| `WHATSAPP_KEYWORDS` | `urgent,asap,...` | Keywords to trigger WhatsApp alerts |
| `LINKEDIN_EMAIL` | — | LinkedIn login email |
| `LINKEDIN_PASSWORD` | — | LinkedIn login password |
| `META_ACCESS_TOKEN` | — | Meta Graph API token |
| `META_PAGE_ID` | — | Facebook Page ID |
| `META_INSTAGRAM_ACCOUNT_ID` | — | Instagram account ID |
| `TWITTER_API_KEY` | — | Twitter API key |
| `TWITTER_API_SECRET` | — | Twitter API secret |
| `TWITTER_ACCESS_TOKEN` | — | Twitter access token |
| `TWITTER_ACCESS_SECRET` | — | Twitter access secret |
| `ODOO_URL` | `http://localhost:8069` | Odoo server URL |
| `ODOO_DB` | `odoo` | Odoo database name |
| `ODOO_USERNAME` | `admin` | Odoo username |
| `ODOO_PASSWORD` | `admin` | Odoo password |
| `BRIEFING_DAY` | `Monday` | Day for CEO briefing |

## Tier Progress

- [x] **Bronze** — Local file-based task processor with plan + execute
- [x] **Silver** — Watchers, approval system, LinkedIn, MCP, Dashboard
- [x] **Gold** — Social media, Odoo accounting, CEO Briefing, Ralph Wiggum, error recovery
- [ ] **Platinum** — Cloud-deployed 24/7 system
