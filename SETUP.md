# Local Setup

Detailed instructions for running Festival Bundle Agent on your machine. For production deployment, see [DEPLOY.md](DEPLOY.md).

## Prerequisites

- Python 3.11+
- Google AI API key ([aistudio.google.com](https://aistudio.google.com))
- MongoDB Atlas cluster **or** local mode (`USE_LOCAL_DATA=true`)
- Node.js 20+ (optional locally — only needed to test MCP outside Docker)

## One-command setup

```bash
chmod +x setup.sh
./setup.sh
```

## Manual setup

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY; set MONGO_URI for Atlas
python3 src/db/seed_data.py
python3 src/agent_main.py
```

Open **http://localhost:8080**

> **Tip:** Set `USE_LOCAL_DATA=true` in `.env` to run without Atlas. Inventory reads from `data/seed_products.json`.

## Environment variables

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

## Tests

```bash
source venv/bin/activate
python3 -m pytest tests/ -v
python3 tests/test_scenarios.py
```

## Docker (local)

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

## MongoDB MCP (local)

See [MCP_SETUP.md](MCP_SETUP.md) for connection strings, Atlas network access, and standalone MCP testing.
