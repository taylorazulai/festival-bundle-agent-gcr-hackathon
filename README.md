# Festival Bundle Agent

**AI-powered festival inventory bundling** — built for the [Google Cloud Rapid Agent Hackathon](https://googlecloudagent.devpost.com/) (MongoDB Partner Track).

> **Live demo:** [https://festival-agent-t5j6ocuqwa-uc.a.run.app](https://festival-agent-t5j6ocuqwa-uc.a.run.app)  
> **Repository:** [festival-bundle-agent-gcr-hackathon](https://github.com/taylorazulai/festival-bundle-agent-gcr-hackathon)

---

## Problem & Solution

Festival vendors juggle perishable inventory, tight margins, and fast-moving crowds. Festival Bundle Agent is a conversational assistant that:

1. **Queries live inventory** from MongoDB Atlas (via pymongo and the official MongoDB MCP Server)
2. **Generates complementary product bundles** with margin-aware pricing
3. **Writes promo copy** ready for social posts and booth signage

Ask natural-language questions — the agent picks tools, shows its math, and returns bundle cards in the chat UI.

### Try it now

Open the [live demo](https://festival-agent-t5j6ocuqwa-uc.a.run.app) and try:

- `Show overstocked items`
- `Create bundles for drinks and snacks`
- `What bundles can I create?`
- `Give me promo copy for my best margin deal`

---

## Architecture

```
┌─────────────┐     POST /chat      ┌──────────────────────────────┐
│  Chat UI    │ ──────────────────► │  FastAPI + Gemini Agent Loop │
│  (browser)  │ ◄────────────────── │  (Google ADK / google-genai)     │
└─────────────┘   bundles + text    └───────────┬──────────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
           ┌────────────────┐          ┌─────────────────┐        ┌─────────────────┐
           │ Local tools    │          │ MongoDB MCP     │        │ Rule-based      │
           │ (bundles,      │          │ Server (stdio)  │        │ fallback        │
           │  pricing,      │          │                 │        │ (no API key)    │
           │  promo)        │          └────────┬────────┘        └─────────────────┘
           └────────────────┘                   │
                                                ▼
                                       ┌─────────────────┐
                                       │ MongoDB Atlas   │
                                       │ (inventory +    │
                                       │  sales data)    │
                                       └─────────────────┘
```

**Hackathon integrations**

| Sponsor / Tech | Role |
|----------------|------|
| **Google Cloud / ADK** | Gemini 2.0 Flash agent with function calling via Google ADK (falls back to google-genai, then rule-based logic) |
| **MongoDB Atlas** | Primary data store for festival inventory; seeded product catalog with stock and sales history |
| **MongoDB MCP Server** | Live Atlas queries exposed as MCP tools over stdio JSON-RPC inside the Cloud Run container |
| **Cloud Run** | Production deployment with Secret Manager for `MONGO_URI` and `GEMINI_API_KEY` |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent | Google ADK + Gemini function calling |
| Model | Gemini 2.0 Flash (`AGENT_MODEL`) |
| Database | MongoDB Atlas (pymongo) |
| MCP | Official `mongodb-mcp-server` (Node.js, stdio) |
| API | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS — full-width chat UI with bundle cards |
| Deployment | Docker → Google Cloud Run |

---

## Quick Start (Local)

### Prerequisites

- Python 3.11+
- Google AI API key ([aistudio.google.com](https://aistudio.google.com))
- MongoDB Atlas cluster **or** local mode (`USE_LOCAL_DATA=true`)
- Node.js 20+ (optional locally — only needed to test MCP outside Docker)

### One-command setup

```bash
chmod +x setup.sh
./setup.sh
```

### Manual setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY; set MONGO_URI for Atlas
python src/db/seed_data.py
python src/agent_main.py
```

Open **http://localhost:8080**

> **Tip:** Set `USE_LOCAL_DATA=true` in `.env` to run without Atlas. Inventory reads from `data/seed_products.json`.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | — |
| `MDB_MCP_CONNECTION_STRING` | MCP server connection string (falls back to `MONGO_URI`) | — |
| `MONGO_DB_NAME` | Database name | `festival_bundle_agent` |
| `GEMINI_API_KEY` | Google AI API key | — |
| `AGENT_MODEL` | Gemini model name | `gemini-2.0-flash` |
| `USE_LOCAL_DATA` | Use seed JSON instead of MongoDB | `false` |
| `PORT` | Server port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat UI |
| `/health` | GET | Service status (MongoDB, Gemini, MCP, agent readiness) |
| `/ready` | GET | Readiness probe (503 until startup completes) |
| `/chat` | POST | `{ "message": "..." }` → `{ "response", "bundles", "tool_calls" }` |

Example:

```bash
curl -s https://festival-agent-t5j6ocuqwa-uc.a.run.app/health
curl -s -X POST https://festival-agent-t5j6ocuqwa-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show overstocked items"}'
```

---

## Agent Tools

| Tool | Purpose |
|------|---------|
| `query_inventory` | Filter inventory (all, overstocked, low stock, category) via pymongo / local JSON |
| `mcp_query_inventory` | Query inventory through MongoDB MCP Server (live Atlas) |
| `generate_bundles` | Create complementary bundle recommendations with pricing |
| `calculate_bundle_pricing` | Detailed margin and pricing breakdown |
| `generate_promo` | Marketing copy (tagline, description, social caption) |

The agent orchestrates these tools automatically based on the user's question.

---

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
python tests/test_scenarios.py
```

---

## Docker

```bash
# Build and run (local JSON fallback)
docker build -t festival-agent .
docker run -p 8080:8080 \
  -e USE_LOCAL_DATA=true \
  -e GEMINI_API_KEY=your-key \
  festival-agent

# Full stack with local MongoDB
docker compose up
```

The production image pre-installs `mongodb-mcp-server` globally via npm so the Python MCP bridge can spawn it without `npx` at runtime.

---

## Deploy to Google Cloud Run

1. **Seed Atlas** (once): `python scripts/seed_atlas.py`
2. **Store secrets** from `.env`: `bash scripts/setup_gcp_secrets.sh`
3. **Deploy**: `bash deploy.sh`

The deploy script builds with Cloud Build, deploys to `us-central1`, and wires Secret Manager for `MONGO_URI` and `GEMINI_API_KEY`.

See [MCP_SETUP.md](MCP_SETUP.md) for MongoDB MCP Server details (connection string, Atlas network access, local testing).

---

## Project Structure

```
festival-bundle-agent/
├── src/
│   ├── agent_main.py       # FastAPI app, Gemini agent loop, /chat endpoint
│   ├── agent_config.py     # Persona, model config, tool registration
│   ├── agent_fallback.py   # Rule-based fallback when Gemini unavailable
│   ├── mcp_client.py       # MongoDB MCP Server stdio bridge
│   ├── tools/              # Inventory, bundles, pricing, promo, MCP integration
│   ├── db/                 # MongoDB client and seeding
│   └── api/                # Alternate server entry point
├── frontend/               # Full-width chat UI (HTML/CSS/JS)
├── data/                   # Seed products and sales JSON
├── tests/                  # Unit and scenario tests
├── scripts/
│   ├── seed_atlas.py       # Seed MongoDB Atlas for production
│   └── setup_gcp_secrets.sh
├── deploy.sh               # Cloud Run deployment
├── Dockerfile
├── docker-compose.yml
└── setup.sh
```

---

## Resilience & Fallbacks

The agent is designed to stay usable under hackathon/demo conditions:

- **No Gemini key** → rule-based responses using the same tool layer
- **MCP unavailable** → pymongo / local JSON inventory queries
- **MongoDB unreachable** → `USE_LOCAL_DATA=true` reads from bundled seed files
- **Slow requests** → 15s chat timeout with a helpful retry message

Check `/health` in the UI footer or via curl to see MongoDB, Gemini, and MCP status.

---

## Acknowledgments

- [Google Cloud Agent Builder / ADK](https://google.github.io/adk-docs/)
- [MongoDB Atlas](https://www.mongodb.com/atlas) — Partner Track
- [MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server)
- [Google Cloud Rapid Agent Hackathon](https://googlecloudagent.devpost.com/)

## License

MIT — see [LICENSE](LICENSE)
