#!/bin/bash
set -euo pipefail

PROJECT_ID="$(gcloud config get-value project)"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
IMAGE="gcr.io/$PROJECT_ID/festival-agent"

grant_secret_access() {
  local secret_name="$1"
  gcloud secrets add-iam-policy-binding "$secret_name" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet >/dev/null
  echo "Granted Secret Accessor on: $secret_name -> $RUNTIME_SA"
}

echo "Project: $PROJECT_ID"
echo "Cloud Run runtime service account: $RUNTIME_SA"
echo ""

for secret in mongo-uri gemini-api-key; do
  if ! gcloud secrets describe "$secret" >/dev/null 2>&1; then
    echo "ERROR: Secret '$secret' not found. Run: bash scripts/setup_gcp_secrets.sh" >&2
    exit 1
  fi
  grant_secret_access "$secret"
done

echo ""
echo "Building container..."
gcloud builds submit --tag "$IMAGE"

echo "Deploying to Cloud Run..."
gcloud run deploy festival-agent \
  --image "$IMAGE" \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="AGENT_MODEL=gemini-2.0-flash,LOG_LEVEL=INFO,USE_LOCAL_DATA=false" \
  --set-secrets="MONGO_URI=mongo-uri:latest,GEMINI_API_KEY=gemini-api-key:latest"

echo "Done. URL:"
gcloud run services describe festival-agent --platform managed --region us-central1 --format 'value(status.url)'
