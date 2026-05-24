#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎪 Festival Bundle Agent — Setup"
echo "================================"

if [ ! -d "venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv venv
fi

echo "Activating venv and installing dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
  echo "⚠️  Edit .env with your MONGO_URI and GEMINI_API_KEY"
fi

echo "Seeding database (or loading local data)..."
export USE_LOCAL_DATA="${USE_LOCAL_DATA:-true}"
python src/db/seed_data.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials:"
echo "     - MONGO_URI (MongoDB Atlas connection string)"
echo "     - GEMINI_API_KEY (Google AI API key)"
echo "     - Set USE_LOCAL_DATA=false to use MongoDB Atlas"
echo ""
echo "  2. Run locally:"
echo "     source venv/bin/activate"
echo "     python src/agent_main.py"
echo ""
echo "  3. Open http://localhost:8080 in your browser"
echo ""
echo "  4. Run tests:"
echo "     pytest tests/ -v"
echo "     python tests/test_scenarios.py"
echo ""
echo "  5. Docker:"
echo "     docker build -t festival-agent ."
echo "     docker compose up"
