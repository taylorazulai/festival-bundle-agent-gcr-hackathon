# Deploy to Google Cloud Run

Production deployment for Festival Bundle Agent.

## Steps

1. **Seed Atlas** (once): `python scripts/seed_atlas.py`
2. **Store secrets** from `.env`: `bash scripts/setup_gcp_secrets.sh`
3. **Deploy**: `bash deploy.sh`

The deploy script builds with Cloud Build, deploys to `us-central1`, and wires Secret Manager for `MONGO_URI` and `GEMINI_API_KEY`.

**Live service:** [https://festival-agent-t5j6ocuqwa-uc.a.run.app](https://festival-agent-t5j6ocuqwa-uc.a.run.app)

## MongoDB MCP in production

The Docker image includes Node.js and pre-installs `mongodb-mcp-server` so `src/mcp_client.py` can spawn the MCP process over stdio inside Cloud Run. See [MCP_SETUP.md](MCP_SETUP.md) for Atlas network access and troubleshooting.

## Health check

```bash
curl -s https://festival-agent-t5j6ocuqwa-uc.a.run.app/health
```
