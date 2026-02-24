# AI Employee - Personal Autonomous Task Processor

A local-first, file-based AI employee that reads tasks, generates plans, executes them, and logs everything automatically.

## Architecture

```
vault/
├── Needs_Action/    ← Drop your .md task files here
├── Plans/           ← AI-generated plans appear here
├── Done/            ← Completed tasks + output deliverables
└── Logs/            ← JSON audit logs
```

### Flow

```
Needs_Action/my_task.md
  → AI reads task
    → Plans/PLAN_my_task.md (action plan)
      → Done/OUTPUT_my_task.md (actual deliverable - blog, email, report, etc.)
        → Done/my_task.md (original task archived)
          → Logs/2026-02-24.json (audit log)
```

## Tech Stack

- **Language:** Python 3.13+
- **Package Manager:** UV
- **LLM:** Groq (Llama 3.3 70B) - Free tier
- **Storage:** Local Markdown files (vault)

## Setup

### 1. Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Get Groq API Key (Free)

1. Go to https://console.groq.com/keys
2. Create a free API key
3. Copy the key

### 4. Configure .env

```
GROQ_API_KEY=your_groq_api_key_here
VAULT_PATH=vault
CHECK_INTERVAL=10
DRY_RUN=false
```

## Usage

### 1. Create a Task

Drop any `.md` file in `vault/Needs_Action/`:

```markdown
## Write a blog post about AI
- Topic: AI in 2026
- Length: 500 words
- Tone: Simple, engaging
```

### 2. Run the AI Employee

```bash
uv run python -m src.runner
```

### 3. Check Results

- **Plan** → `vault/Plans/PLAN_<task_name>.md`
- **Output** → `vault/Done/OUTPUT_<task_name>.md`
- **Original task** → `vault/Done/<task_name>.md`
- **Log** → `vault/Logs/<date>.json`

### 4. Stop

Press `Ctrl+C` to stop the runner.

## Features

- **Plan + Execute** — AI generates a plan AND produces the actual deliverable
- **Duplicate Protection** — Same task won't be processed twice
- **Error Handling** — Failed tasks stay in Needs_Action for retry, errors are logged
- **Dry Run Mode** — Set `DRY_RUN=true` in `.env` to test without LLM calls
- **Audit Logging** — Every action logged with timestamp in JSON format

## Project Structure

```
ai_employ/
├── pyproject.toml
├── .env                   # Secrets (gitignored)
├── .gitignore
├── README.md
├── documents.txt          # Hackathon spec
├── vault/
│   ├── Needs_Action/      # Input tasks
│   ├── Plans/             # AI plans
│   ├── Done/              # Completed + outputs
│   └── Logs/              # Audit logs
└── src/
    ├── __init__.py
    ├── config.py           # Paths, settings, env loading
    ├── brain.py            # AI logic (plan + execute + log)
    └── runner.py           # Polling loop
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | Your Groq API key (required) |
| `VAULT_PATH` | `vault` | Path to vault directory |
| `CHECK_INTERVAL` | `10` | Seconds between folder checks |
| `DRY_RUN` | `false` | Skip LLM calls and file moves |

## Tier Progress

- [x] **Bronze** — Local file-based task processor with plan + execute
- [ ] **Silver** — Watchers (Gmail, WhatsApp), approval system, MCP
- [ ] **Gold** — Multi-domain integration, Odoo, CEO Briefing
- [ ] **Platinum** — Cloud-deployed 24/7 system
