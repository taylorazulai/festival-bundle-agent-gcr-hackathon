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

### Verify Gemini is active (not fallback)

1. Put your key in `festival-bundle-agent/.env` as `GEMINI_API_KEY=...` (no quotes).
2. Start the server from that folder: `python3 src/agent_main.py`
3. Open the UI — you should **not** see the amber “Running in fallback mode” banner.
4. Or check: `curl -s http://localhost:8080/health | python3 -m json.tool` and confirm `"fallback_mode": false`.

If the banner stays visible with a key set, restart the server, confirm the `.env` path, and check startup logs for Gemini/ADK errors.

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB Atlas connection string | — |
| `MDB_MCP_CONNECTION_STRING` | MCP server connection string (falls back to `MONGO_URI`) | — |
| `MONGO_DB_NAME` | Database name | `festival_bundle_agent` |
| `GEMINI_API_KEY` | Google AI API key | — |
| `AGENT_MODEL` | Gemini model name | `gemini-3.1-flash-lite` |
| `USE_LOCAL_DATA` | Use seed JSON instead of MongoDB | `false` |
| `PORT` | Server port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Gemini model choice (inactive GCP projects)

Google may restrict **preview / high-demand Flash** models on inactive projects:

- `gemini-2.5-flash`
- `gemini-2.5-flash-lite`
- `gemini-3-flash-preview`

Prefer **stable** models that stay available regardless of project activity, for example:

| Model | Role |
|-------|------|
| `gemini-3.1-flash-lite` | Default here — fast, low cost, stable Flash tier |
| `gemini-2.5-pro` | Stronger reasoning; higher cost/latency |
| `gemini-3.1-pro` | Newer stable Pro tier |
| `gemini-2.0-flash` | Older stable Flash fallback |

Avoid `gemini-flash-latest` on inactive projects; it may alias to a restricted Flash model.

### Fix `403 API_KEY_SERVICE_BLOCKED`

This means the key in `.env` is tied to a **Google Cloud project** where `generativelanguage.googleapis.com` is not allowed for that key (common with keys created in Cloud Console).

**Fastest fix (recommended for local dev):**

1. Open [Google AI Studio → API keys](https://aistudio.google.com/apikey).
2. Create an API key (not restricted to a blocked GCP project).
3. Set `GEMINI_API_KEY=` in `festival-bundle-agent/.env`.
4. Restart: `python3 src/agent_main.py`.

**If you must use a GCP project key:**

1. [Google Cloud Console](https://console.cloud.google.com/) → select the same project as the key.
2. **APIs & Services → Library** → search **Generative Language API** → **Enable**.
3. **APIs & Services → Credentials** → your API key → **API restrictions** → either “Don’t restrict” (dev only) or restrict to **Generative Language API**.
4. Ensure billing is enabled on the project.
5. Restart the agent and send a chat message; `/health` should show `"fallback_mode": false`.

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
