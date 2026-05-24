# 🎪 Festival Bundle Agent

[![Live Demo](https://img.shields.io/badge/Live%20Demo-festival--agent--t5j6ocuqwa--uc.a.run.app-orange?style=for-the-badge)](https://festival-agent-t5j6ocuqwa-uc.a.run.app)
[![Google Cloud](https://img.shields.io/badge/Built%20with-Google%20Cloud-4285F4?logo=google-cloud&logoColor=white)](https://cloud.google.com/agent-builder)
[![MongoDB](https://img.shields.io/badge/Data%20Layer-MongoDB%20Atlas-47A248?logo=mongodb&logoColor=white)](https://www.mongodb.com/atlas)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> AI-powered inventory and bundle optimization for festival vendors.  
> Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — MongoDB Partner Track.

**[🚀 Try it live](https://festival-agent-t5j6ocuqwa-uc.a.run.app)** · **[📦 Repository](https://github.com/taylorazulai/festival-bundle-agent-gcr-hackathon)**

---

## 📸 Preview

![Festival Bundle Agent — Bundle recommendations with pricing and margins](docs/screenshot.png)

---

## Problem & Solution

Festival vendors juggle perishable inventory, tight margins, and fast-moving crowds. Festival Bundle Agent is a conversational assistant that:

1. **Queries live inventory** from MongoDB Atlas (via pymongo and the official **MongoDB MCP Server**)
2. **Generates complementary product bundles** with margin-aware pricing
3. **Writes promo copy** ready for social posts and booth signage

### Try it now

Open the [live demo](https://festival-agent-t5j6ocuqwa-uc.a.run.app) and try:

- `Show overstocked items`
- `Create bundles for drinks and snacks`
- `What bundles can I create?`
- `Give me promo copy for my best margin deal`

---

## 🛠️ Built With

| Technology | Role |
|------------|------|
| [Google Cloud Agent Builder](https://cloud.google.com/agent-builder) | Agent orchestration and multi-step reasoning |
| [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/) | LLM for natural language understanding and tool selection |
| [MongoDB Atlas](https://www.mongodb.com/atlas) | Live production database for festival inventory |
| [MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server) | Model Context Protocol integration for tool-based data access |
| [FastAPI](https://fastapi.tiangolo.com/) | Python backend API |
| [Docker](https://www.docker.com/) | Containerization |
| [Google Cloud Run](https://cloud.google.com/run) | Serverless deployment |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│   User      │────▶│  FastAPI (Python)   │────▶│ Gemini (Agent    │
│  (Browser)  │     │  + Agent Builder    │     │ Builder / ADK)   │
└─────────────┘     └──────────┬──────────┘     └──────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌──────────┐     ┌───────────┐     ┌──────────┐
       │ PyMongo  │     │ MongoDB   │     │ Rule-Based│
       │(fallback)│     │ MCP Server│     │ Fallback │
       └────┬─────┘     └─────┬─────┘     └──────────┘
            │                 │
            └────────┬────────┘
                     ▼
              ┌──────────────┐
              │ MongoDB Atlas│
              │   (M0 Free)  │
              └──────────────┘
```

---

## 🔌 MongoDB MCP Integration

This project integrates the [official MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server) via a custom Python bridge (`src/mcp_client.py`), enabling the agent to query live Atlas data through the Model Context Protocol.

- **Protocol**: JSON-RPC over stdio
- **Tools exposed**: `find`, `aggregate`, `count`, `distinct`
- **Fallback**: Direct PyMongo connection if MCP is unavailable

See [MCP_SETUP.md](MCP_SETUP.md) for connection strings, local testing, and Cloud Run notes.

---

## 🚀 Quick Start

```bash
git clone https://github.com/taylorazulai/festival-bundle-agent-gcr-hackathon.git
cd festival-bundle-agent
cp .env.example .env   # add your keys
docker build -t festival-agent .
docker run -p 8080:8080 --env-file .env festival-agent
```

Open **http://localhost:8080**

- **Full local setup** (venv, seed data, tests): [SETUP.md](SETUP.md)
- **Cloud Run deployment**: [DEPLOY.md](DEPLOY.md)

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Chat UI |
| `/health` | GET | Service status (MongoDB, Gemini, MCP, agent readiness) |
| `/ready` | GET | Readiness probe (503 until startup completes) |
| `/chat` | POST | `{ "message": "..." }` → `{ "response", "bundles", "tool_calls" }` |

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
| `query_inventory` | Filter inventory via pymongo / local JSON |
| `mcp_query_inventory` | Query inventory through **MongoDB MCP Server** (live Atlas) |
| `generate_bundles` | Complementary bundle recommendations with pricing |
| `calculate_bundle_pricing` | Margin and pricing breakdown |
| `generate_promo` | Marketing copy (tagline, description, social caption) |

---

## Resilience & Fallbacks

- **No Gemini key** → rule-based responses using the same tool layer
- **MCP unavailable** → pymongo / local JSON inventory queries
- **MongoDB unreachable** → `USE_LOCAL_DATA=true` reads bundled seed files
- **Slow requests** → 15s chat timeout with a helpful retry message

Check `/health` in the UI footer or via curl for MongoDB, Gemini, and MCP status.

---

## Project Structure

```
festival-bundle-agent/
├── src/
│   ├── agent_main.py       # FastAPI app, Gemini agent loop, /chat
│   ├── mcp_client.py       # MongoDB MCP Server stdio bridge
│   ├── tools/              # Inventory, bundles, pricing, promo, MCP
│   └── db/                 # MongoDB client and seeding
├── frontend/               # Chat UI with bundle cards
├── docs/                   # Screenshots and assets for README
├── tests/
├── deploy.sh
├── SETUP.md
└── DEPLOY.md
```

---

## Acknowledgments

- [Google Cloud Agent Builder / ADK](https://google.github.io/adk-docs/)
- [MongoDB Atlas](https://www.mongodb.com/atlas) — Partner Track
- [MongoDB MCP Server](https://github.com/mongodb-js/mongodb-mcp-server)
- [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/)

## License

MIT — see [LICENSE](LICENSE)
