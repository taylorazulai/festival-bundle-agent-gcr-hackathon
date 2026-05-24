"""Secondary FastAPI entry point — re-exports agent_main app."""

from src.agent_main import app

__all__ = ["app"]

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=port, reload=False)
