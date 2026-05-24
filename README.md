# Festival Bundle Agent

**Your AI-powered festival inventory bundling assistant** — built for the Google Cloud Rapid Agent Hackathon (MongoDB Partner Track).

> Demo: _[Add hosted URL after Cloud Run deployment]_

## What It Does

Festival Bundle Agent helps small festival vendors manage inventory and create optimized product bundles in real time. Ask questions like:

- "What bundles can I create with items I'm overstocked on?"
- "Show me the pricing breakdown for a drink-and-snack combo"
- "Give me promo copy for my best margin deal"

The agent queries MongoDB Atlas inventory, analyzes margins and stock levels, and returns actionable bundle recommendations with pricing, margin breakdowns, and promotional descriptions.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent | Google ADK / Gemini (function calling) |
| Model | Gemini 2.0 Flash (configurable via `AGENT_MODEL`) |
| Database | MongoDB Atlas (pymongo) |
| API | FastAPI + Uvicorn |
| Frontend | Vanilla HTML/CSS/JS chat UI |
| Deployment | Docker, Cloud Run ready |

## Setup

### Prerequisites

- Python 3.11+
- MongoDB Atlas cluster (or use local JSON fallback)
- Google AI API key ([aistudio.google.com](https://aistudio.google.com))

### Quick Start

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python src/db/seed_data.py
python src/agent_main.py
```

Open **http://localhost:8080**

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | — |
| `GEMINI_API_KEY` | Google AI API key | — |
| `AGENT_MODEL` | Gemini model name | `gemini-2.0-flash` |
| `USE_LOCAL_DATA` | Use seed JSON instead of MongoDB | `false` |
| `PORT` | Server port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |

## How to Run

```bash
# Local server
python src/agent_main.py

# Run tests
pytest tests/ -v
python tests/test_scenarios.py

# Docker
docker build -t festival-agent .
docker run -p 8080:8080 -e USE_LOCAL_DATA=true festival-agent

# Docker Compose (includes MongoDB)
docker compose up
```

## Deploy to Google Cloud Run

1. Seed MongoDB Atlas: `python scripts/seed_atlas.py`
2. Ensure `gcloud` is authenticated and project is set
3. Store secrets: `bash scripts/setup_gcp_secrets.sh` (reads `MONGO_URI` and `GEMINI_API_KEY` from `.env`)
4. Deploy: `bash deploy.sh`
5. Submit the resulting URL to Devpost

## Project Structure

```
festival-bundle-agent/
├── src/
│   ├── agent_main.py      # Agent + FastAPI entry point
│   ├── agent_config.py    # Persona and model config
│   ├── tools/             # Inventory, bundles, pricing, promo, MCP tools
│   ├── db/                # MongoDB client and seeding
│   ├── api/               # Secondary server entry point
│   └── utils/             # Logging
├── frontend/              # Chat UI
├── data/                  # Seed products and sales
├── tests/                 # Unit and scenario tests
├── scripts/
│   ├── seed_atlas.py      # Seed MongoDB Atlas for production
│   └── setup_gcp_secrets.sh
├── deploy.sh              # Cloud Run deployment script
├── Dockerfile
├── docker-compose.yml
└── setup.sh
```

## Tools

| Tool | Purpose |
|------|---------|
| `query_inventory` | Filter inventory (all, overstocked, low stock, category) |
| `mcp_query_inventory` | MongoDB MCP Server inventory query |
| `generate_bundles` | Create complementary bundle recommendations |
| `calculate_bundle_pricing` | Detailed margin and pricing breakdown |
| `generate_promo` | Marketing copy (tagline, description, social caption) |

## Acknowledgments

- Google Cloud Agent Builder / ADK
- MongoDB Atlas Partner Track
- Google Cloud Rapid Agent Hackathon

## License

MIT — see [LICENSE](LICENSE)
