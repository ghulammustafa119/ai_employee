# AI Employee - Personal Autonomous Task Processor

A local-first, file-based AI employee that reads tasks, generates plans, executes them, and logs everything automatically. Features watchers for Gmail/WhatsApp, human-in-the-loop approval, LinkedIn auto-posting, and Email MCP server.

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
├── Logs/                ← JSON audit logs
├── Dashboard.md         ← Live system status
└── Company_Handbook.md  ← Rules of engagement
```

### Flow

```
[Gmail/WhatsApp Watcher] → Needs_Action/task.md
  → AI reads task
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
- **MCP:** Email MCP Server (Node.js)

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
```

### 3. Install Playwright Browsers (for WhatsApp)

```bash
uv run playwright install chromium
```

### 4. Get API Keys

- **Groq (required):** https://console.groq.com/keys (free)
- **Gmail (optional):** Google Cloud Console → Gmail API → OAuth credentials
- **LinkedIn (optional):** Set email/password in .env

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
```

## Usage

### Run the AI Employee (Core)

```bash
uv run python -m src.runner
```

### Run Gmail Watcher

```bash
uv run python -m src.watchers.gmail_watcher
```

### Run WhatsApp Watcher

```bash
uv run python -m src.watchers.whatsapp_watcher
```

### Generate LinkedIn Post

```bash
uv run python -m src.linkedin_poster
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

## Project Structure

```
ai_employ/
├── pyproject.toml
├── .env                          # Secrets (gitignored)
├── .gitignore
├── README.md
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
│   ├── Dashboard.md
│   └── Company_Handbook.md
├── src/
│   ├── __init__.py
│   ├── config.py                 # Paths, settings, env loading
│   ├── brain.py                  # AI logic + approval system
│   ├── runner.py                 # Main polling loop
│   ├── dashboard.py              # Dashboard generator
│   ├── linkedin_poster.py        # LinkedIn post generator
│   └── watchers/
│       ├── __init__.py
│       ├── base_watcher.py       # Abstract base class
│       ├── gmail_watcher.py      # Gmail monitoring
│       └── whatsapp_watcher.py   # WhatsApp monitoring
└── mcp_servers/
    └── email_server/
        ├── package.json
        └── index.js              # Email MCP server
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

## Tier Progress

- [x] **Bronze** — Local file-based task processor with plan + execute
- [x] **Silver** — Watchers, approval system, LinkedIn, MCP, Dashboard
- [ ] **Gold** — Multi-domain integration, Odoo, CEO Briefing
- [ ] **Platinum** — Cloud-deployed 24/7 system
