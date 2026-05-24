#!/bin/bash
# Store MONGO_URI and GEMINI_API_KEY from .env in Google Cloud Secret Manager.
# Creates secrets on first run; adds a new version if they already exist.
# Grants Cloud Run's default service account access to read both secrets.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

read_env_var() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" | head -1 | cut -d= -f2-
}

upsert_secret() {
  local name="$1"
  local value="$2"

  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    echo -n "$value" | gcloud secrets versions add "$name" --data-file=-
    echo "Updated secret: $name (new version)"
  else
    echo -n "$value" | gcloud secrets create "$name" --data-file=-
    echo "Created secret: $name"
  fi
}

grant_secret_access() {
  local secret_name="$1"
  local service_account="$2"

  gcloud secrets add-iam-policy-binding "$secret_name" \
    --member="serviceAccount:${service_account}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
  echo "Granted Secret Accessor on: $secret_name"
}

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  echo "Copy .env.example to .env and set MONGO_URI and GEMINI_API_KEY." >&2
  exit 1
fi

MONGO_URI="$(read_env_var MONGO_URI)"
GEMINI_API_KEY="$(read_env_var GEMINI_API_KEY)"

if [[ -z "$MONGO_URI" || "$MONGO_URI" == *"<user>"* || "$MONGO_URI" == "paste-your-uri-here" ]]; then
  echo "ERROR: Set a valid MONGO_URI in .env before running this script." >&2
  exit 1
fi

if [[ -z "$GEMINI_API_KEY" || "$GEMINI_API_KEY" == "your-gemini-api-key" || "$GEMINI_API_KEY" == "paste-your-key-here" ]]; then
  echo "ERROR: Set a valid GEMINI_API_KEY in .env before running this script." >&2
  exit 1
fi

PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: No gcloud project set. Run: gcloud config set project YOUR_PROJECT_ID" >&2
  exit 1
fi

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Using gcloud project: $PROJECT_ID"
echo "Cloud Run runtime service account: $RUNTIME_SA"
echo "Reading secrets from: $ENV_FILE"
echo ""

upsert_secret "mongo-uri" "$MONGO_URI"
upsert_secret "gemini-api-key" "$GEMINI_API_KEY"

echo ""
echo "Granting Cloud Run access to secrets..."
grant_secret_access "mongo-uri" "$RUNTIME_SA"
grant_secret_access "gemini-api-key" "$RUNTIME_SA"

echo ""
echo "Done. Deploy with: bash deploy.sh"
