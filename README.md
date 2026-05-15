# GuthrieAI — Chatroom for Bots

![GuthrieAI Logo](app/static/images/logo.png)

A chatroom where multiple AI bots participate in conversations, each with a distinct role. A hidden **RouterBot** reads every message and automatically routes it to the right bot. Built with Flask, HTMX, SQLite, and Ollama — fully local, no API keys, no cost.

---

## Bots

| Bot | Role | Handles |
|---|---|---|
| EmailBot | Email Assistant | Drafting, replying, improving emails |
| CodeBot | Code Assistant | Bugs, scripts, debugging, code review |
| AccountingBot | Accounting Assistant | Invoices, budgets, expenses, finance |
| JokeBot | Entertainment Bot | Jokes, greetings, casual conversation |

You can also **create custom bots** with any name, system prompt, and model.

---

## Requirements

- [Docker](https://www.docker.com/products/docker-desktop/) and Docker Compose
- ~3GB disk space (tinyllama + phi3:mini)
- 6GB RAM recommended

No API keys. Everything runs locally via [Ollama](https://ollama.com).

---

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/chatroomforbots.git
cd chatroomforbots
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5001**

> First run pulls `tinyllama` (~600MB) and `phi3:mini` (~2.3GB) — once only.

---

## How RouterBot Works

Every message goes through a 5-step routing chain before any bot responds:

1. **Keyword fast path** — 2+ keyword matches for one bot → instant route, no LLM call
2. **Missing specialist check** — if keywords point to a bot not in this chat → stops and tells the user
3. **LLM routing** — `phi3:mini` classifies the message using last 3 messages + last active bot as context
4. **Context fallback** — if LLM fails, stay with the last active bot rather than jumping to JokeBot
5. **JokeBot fallback** — catch-all for greetings, casual chat, and anything unmatched

The routing decision is shown in the chat so you can see which bot was picked and why.

---

## Features

- Multiple conversations — create and switch between chatrooms
- Add/remove bots per conversation
- Create custom bots with a name, role, system prompt, and model
- Change bot model via dropdown (any locally pulled Ollama model)
- Edit bot system prompt from the All Bots panel
- Typing indicator + instant input clear on send
- Stop button to cancel while bot is thinking
- Real-time updates via HTMX polling (no page refresh needed)

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | Flask session secret |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama API endpoint |
| `DEFAULT_MODEL` | `tinyllama` | Default model for new bots |
| `ROUTER_MODEL` | `phi3:mini` | Model used by RouterBot |
| `ROUTER_CONFIDENCE_THRESHOLD` | `1` | Min keyword matches for fallback routing |
| `BOT_MEMORY_MESSAGES` | `5` | Prior messages sent as bot context |

---

## Project Structure

```
chatroomforbots/
├── app/
│   ├── __init__.py          # App factory + default bot seeding
│   ├── models.py            # SQLAlchemy models
│   ├── routes/
│   │   ├── chat.py          # POST /message, GET /messages
│   │   ├── bots.py          # Bot CRUD + /ollama/models
│   │   └── conversations.py # Conversation CRUD
│   ├── services/
│   │   ├── ollama.py        # Ollama HTTP client
│   │   └── router.py        # RouterBot logic
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── partials/messages.html
│   └── static/              # CSS + logo
├── instance/chat.db         # SQLite (auto-created, gitignored)
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── requirements.txt
```

---

## Ports

| Port | Service |
|---|---|
| `5001` | Web app (host) → Flask (container: 5000) |
| `11434` | Ollama API |

---

## Adding Ollama Models

```bash
docker exec -it guthrieai_ollama ollama pull <model-name>
```

Then select it from the model dropdown in the UI.

---

## Running Without Docker

```bash
ollama serve && ollama pull tinyllama && ollama pull phi3:mini
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set OLLAMA_BASE_URL=http://localhost:11434 in .env
python run.py
```

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Main chatroom page |
| `POST` | `/message` | Send a user message — triggers routing and bot response |
| `GET` | `/messages/<conv_id>` | Fetch messages for a conversation (HTMX polls every 2s) |
| `POST` | `/conversations` | Create a new conversation |
| `DELETE` | `/conversations/<id>` | Delete a conversation |
| `POST` | `/conversations/<id>/bots` | Add a bot to a conversation |
| `DELETE` | `/conversations/<id>/bots/<bot_id>` | Remove a bot from a conversation |
| `POST` | `/bots` | Create a custom bot |
| `POST` | `/bots/<id>` | Update a bot (name, role, system prompt, model) |
| `POST` | `/bots/<id>/delete` | Delete a bot (non-default only) |
| `GET` | `/ollama/models` | List available Ollama models (JSON) |
