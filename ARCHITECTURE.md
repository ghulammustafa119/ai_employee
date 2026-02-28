# AI Employee Architecture (Gold Tier)

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT                        │
│  Dashboard.md │ Business_Goals.md │ Company_Handbook.md  │
│                                                          │
│  /Needs_Action  →  /Plans  →  /Pending_Approval         │
│       ↓                            ↓         ↓           │
│  /In_Progress        /Approved    /Rejected              │
│       ↓                   ↓                              │
│     /Done             /Done                              │
│                                                          │
│  /Briefings  │  /Accounting  │  /Logs                    │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Watchers │ │  Brain   │ │   MCP    │
    │ (Senses) │ │(Reasoner)│ │ (Hands)  │
    └──────────┘ └──────────┘ └──────────┘
```

## Components

### 1. Brain (`src/brain.py`)
The reasoning engine. Uses Groq LLM (llama-3.3-70b) to:
- **Plan** tasks: Reads from `/Needs_Action`, generates step-by-step plans
- **Execute** tasks: Produces actual deliverables (emails, reports, blog posts)
- **Route** tasks: Detects personal vs business domain, routes sensitive tasks to approval
- **Retry**: Automatic retry with exponential backoff on transient errors

### 2. Watchers (`src/watchers/`)
Lightweight polling scripts that monitor external sources:

| Watcher | Source | Pattern |
|---------|--------|---------|
| `GmailWatcher` | Gmail API | Polls unread important emails |
| `WhatsAppWatcher` | WhatsApp Web (Playwright) | Monitors for keyword-triggered messages |

All watchers extend `BaseWatcher` which provides:
- Polling loop with configurable interval
- Duplicate detection via `processed_ids` set
- Error handling per item

### 3. MCP Servers (`mcp_servers/`)
Model Context Protocol servers for external actions:

| Server | Purpose | Status |
|--------|---------|--------|
| `email_server` | Send/draft/search Gmail | Real (Gmail API) |
| `odoo_server` | Accounting: invoices, payments, contacts | Mock (JSON-RPC) |

### 4. Social Media (`src/social_media/`)
Mock integrations for social platforms:

| Platform | Module | Capabilities |
|----------|--------|-------------|
| Facebook | `facebook_poster.py` | Post, insights, summary |
| Instagram | `instagram_poster.py` | Post, insights, summary |
| Twitter/X | `twitter_poster.py` | Tweet, analytics, summary |
| LinkedIn | `linkedin_poster.py` | Post via Playwright |

All follow the approval pattern: generate → `/Pending_Approval` → user approves → execute.

### 5. Odoo Client (`src/odoo_client.py`)
Python wrapper for Odoo Community accounting:
- Invoice management (create, list, filter by status)
- Payment recording
- Contact management
- Account balances and financial summaries
- Currently mock — swap for real JSON-RPC calls to Odoo 19+

### 6. CEO Briefing (`src/ceo_briefing.py`)
Weekly autonomous business audit:
- Collects: completed tasks, activity logs, financial data, social media metrics
- Generates: Monday Morning CEO Briefing with AI
- Sections: Executive Summary, Revenue, Completed Tasks, Bottlenecks, Proactive Suggestions
- Scheduled: Runs on configurable day (default: Monday)

### 7. Ralph Wiggum Loop (`src/ralph_wiggum.py`)
Autonomous multi-step task completion:
- Runs Claude Code in a loop until task is complete
- Two completion strategies: promise-based or file-movement
- Max iteration guard to prevent infinite loops
- State tracking in `/In_Progress` folder

### 8. Runner (`src/runner.py`)
Main orchestration loop:
1. Process new tasks from `/Needs_Action`
2. Process approved tasks (general + social media)
3. Process rejected tasks
4. Update dashboard
5. Check CEO briefing schedule

Wrapped with `graceful_degrade()` for fault tolerance.

### 9. Infrastructure
- **Retry Handler** (`src/retry_handler.py`): `@with_retry` decorator, error categories, `graceful_degrade()` context manager
- **Audit Logger** (`src/audit_logger.py`): Structured JSON logging with timing, monthly summaries
- **Config** (`src/config.py`): All env vars, vault paths, `ensure_vault_structure()`
- **Dashboard** (`src/dashboard.py`): Auto-generates `Dashboard.md` with task counts + recent activity

## Data Flow

```
External Input → Watcher → /Needs_Action → Brain (Plan) → Sensitive?
                                                              │
                                              ┌───────────────┼──────────┐
                                              ▼ No                       ▼ Yes
                                         Execute directly     /Pending_Approval
                                              │                     │
                                              ▼               User moves to
                                           /Done         /Approved or /Rejected
                                                              │
                                                         Execute → /Done
```

## Folder Structure

```
ai_employee/
├── src/
│   ├── config.py              # Configuration & env vars
│   ├── brain.py               # LLM reasoning engine
│   ├── runner.py              # Main orchestration loop
│   ├── dashboard.py           # Dashboard generator
│   ├── linkedin_poster.py     # LinkedIn (Playwright)
│   ├── odoo_client.py         # Odoo accounting client (mock)
│   ├── ceo_briefing.py        # Weekly CEO briefing generator
│   ├── ralph_wiggum.py        # Autonomous task loop
│   ├── retry_handler.py       # Error recovery & retry logic
│   ├── audit_logger.py        # Structured audit logging
│   ├── watchers/
│   │   ├── base_watcher.py    # Abstract watcher base class
│   │   ├── gmail_watcher.py   # Gmail polling
│   │   └── whatsapp_watcher.py # WhatsApp monitoring
│   └── social_media/
│       ├── facebook_poster.py  # Facebook (mock)
│       ├── instagram_poster.py # Instagram (mock)
│       └── twitter_poster.py   # Twitter/X (mock)
├── mcp_servers/
│   ├── email_server/          # Gmail MCP server
│   └── odoo_server/           # Odoo accounting MCP server (mock)
├── vault/                     # Obsidian vault
│   ├── Needs_Action/          # Incoming tasks
│   ├── Plans/                 # Generated plans
│   ├── Pending_Approval/      # Awaiting human approval
│   ├── Approved/              # Human-approved tasks
│   ├── Rejected/              # Human-rejected tasks
│   ├── Done/                  # Completed tasks & outputs
│   ├── Briefings/             # CEO briefings
│   ├── Accounting/            # Financial data
│   ├── Logs/                  # Activity + audit logs
│   ├── Inbox/                 # Raw incoming items
│   ├── Dashboard.md           # Auto-generated dashboard
│   ├── Business_Goals.md      # Business objectives & metrics
│   └── Company_Handbook.md    # Rules of engagement
├── scripts/
│   ├── start_all.sh           # Start all services
│   ├── stop_all.sh            # Stop all services
│   ├── setup_cron.sh          # Configure cron jobs
│   └── ralph_loop.sh          # Start Ralph Wiggum loop
└── ARCHITECTURE.md            # This file
```

## Security

- Credentials stored in `.env` (never committed)
- Sensitive tasks require human approval before execution
- DRY_RUN mode prevents real external actions
- Audit logging tracks every action with timestamps
- Permission boundaries: auto-approve thresholds for different action types

## Swapping Mocks for Real APIs

### Facebook/Instagram
Replace `MockFacebookAPI`/`MockInstagramAPI` in the poster files with real Meta Graph API calls:
```python
import requests
response = requests.post(
    f"https://graph.facebook.com/v19.0/{page_id}/feed",
    data={"message": text, "access_token": token}
)
```

### Twitter/X
Replace `MockTwitterAPI` with `tweepy` or direct Twitter API v2 calls.

### Odoo
Replace mock methods in `OdooClient` with real XML-RPC/JSON-RPC:
```python
import xmlrpc.client
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
```

Or use the Odoo MCP server (`mcp_servers/odoo_server/`) with real HTTP calls to `{odoo_url}/jsonrpc`.

---

## Platinum Tier: Dual-Agent Architecture

### Overview

```
┌──────────────┐     vault_sync.git     ┌──────────────┐
│  Cloud Agent │ ◄──── Git Sync ────► │  Local Agent │
│  (draft-only)│     (bare repo)       │(full authority)│
└──────┬───────┘                       └──────┬───────┘
       │                                      │
  vault_cloud/                           vault_local/
```

### Cloud Agent (`src/platinum/cloud_runner.py`)
- Scans `Needs_Action/email/`, `social/`, `accounting/`, `general/`
- Claims tasks atomically via `In_Progress/cloud/`
- Generates drafts using LLM, writes to `Pending_Approval/<domain>/`
- Writes signals to `Signals/` for Local to consume
- **CANNOT**: approve, send, write Dashboard, touch WhatsApp/payments

### Local Agent (`src/platinum/local_runner.py`)
- Processes approvals across all domain subfolders
- Executes sends with full authority (email, social posts, Odoo entries)
- Merges Cloud signals into Dashboard (single-writer rule)
- Owns WhatsApp session and payment/banking actions
- Runs CEO Briefing schedule

### Vault Sync (`src/platinum/vault_sync.py`)
- Git-based sync using a bare repo as intermediary
- Pull with `--rebase --autostash`, fallback to `--strategy-option=theirs`
- Background sync thread every 5 seconds
- Only markdown files sync — secrets never leave their agent

### Claim-by-Move (`src/platinum/claim_manager.py`)
- `os.rename()` is atomic on same filesystem
- First agent to move file from `Needs_Action/<domain>/` to `In_Progress/<agent>/` owns it
- Other agent's claim attempt raises `FileNotFoundError` — safely skipped

### Domain Routing (`src/platinum/domain_router.py`)
Tasks are routed by filename prefix or content keywords:
- `EMAIL_*` → `email/`
- `FACEBOOK_*`, `TWEET_*` → `social/`
- `INVOICE_*` → `accounting/`
- Everything else → `general/`

### Signal Bus (`src/platinum/signal_bus.py`)
- Cloud writes small `.md` files to `Signals/`
- Local reads, consumes (deletes), and merges into Dashboard
- Preserves single-writer rule for Dashboard.md

### Health Monitoring (`src/platinum/watchdog.py`)
- Checks Cloud/Local PIDs every 30 seconds
- Monitors Git sync freshness (last commit < 120s)
- Writes health report to `Updates/health_status.md`

### Platinum Demo Flow
```
Email arrives → Cloud claims → Cloud drafts reply → Pending_Approval/email/
    → Git sync → Local sees approval → User approves → Approved/
    → Local sends (mock) → Done/ → Logs/ → Dashboard updated
```
