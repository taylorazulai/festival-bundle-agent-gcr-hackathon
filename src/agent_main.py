"""Festival Bundle Agent — ADK/Gemini agent with FastAPI server."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# ============================================================
# LIGHTWEIGHT: FastAPI app created instantly
# No heavy imports above this line
# ============================================================
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Festival Bundle Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = PROJECT_ROOT / "frontend"
MAX_REQUEST_TIMEOUT_S = 15.0
MAX_AGENT_TURNS = 5
APP_VERSION = "1.0.0"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=0, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    bundles: list[dict[str, Any]] = Field(default_factory=list)
    timeout: bool = False


# ============================================================
# GLOBAL STATE - populated lazily during startup
# ============================================================
_agent_loop: Any = None
_db_client: Any = None
_mcp_client: Any = None
_startup_complete = False
_tool_functions: dict[str, Any] = {}
_tool_declarations: list[dict[str, Any]] = []


def _gemini_configured() -> bool:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    return bool(api_key and api_key != "your-gemini-api-key")


# ============================================================
# IMMEDIATELY AVAILABLE ENDPOINTS
# ============================================================


@app.get("/health")
async def health() -> dict[str, Any]:
    """Works instantly on startup. Reports init status."""
    return {
        "status": "healthy",
        "server": "running",
        "startup_complete": _startup_complete,
        "database": "connected" if _db_client else "initializing",
        "mcp": "connected" if _mcp_client and getattr(_mcp_client, "_initialized", False) else "initializing",
        "agent": "ready" if _agent_loop else "initializing",
        "gemini": _gemini_configured(),
        "version": APP_VERSION,
    }


@app.get("/ready")
async def ready() -> dict[str, str]:
    """Kubernetes-style readiness probe."""
    if not _startup_complete:
        raise HTTPException(status_code=503, detail="Service starting...")
    return {"status": "ready"}


# ============================================================
# AGENT RUNTIME (heavy imports deferred to startup)
# ============================================================


def _api_error_is_blocked(error: str) -> bool:
    blocked_markers = ("403", "PERMISSION_DENIED", "API_KEY_SERVICE_BLOCKED")
    return any(marker in error for marker in blocked_markers)


def _execute_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    func = _tool_functions.get(name)
    if not func:
        return {"status": "error", "message": f"Unknown tool: {name}"}
    start = time.time()
    logger.info("Tool called: %s args=%s", name, args)
    try:
        result = func(**args)
    except TypeError:
        import inspect

        sig = inspect.signature(func)
        filtered = {k: v for k, v in args.items() if k in sig.parameters}
        result = func(**filtered)
    except Exception as exc:
        logger.error("Tool execution failed: %s — %s", name, exc)
        result = {"status": "error", "message": str(exc)}
    logger.info("Tool returned in %.2fs: %s", time.time() - start, name)
    return result


class GeminiAgentLoop:
    """Manual agent loop using google-genai with function calling."""

    def __init__(self, model: str | None = None) -> None:
        from src.agent_config import AGENT_ADK_NAME, AGENT_PERSONA, DEFAULT_MODEL

        self.model = model or DEFAULT_MODEL
        self._agent_persona = AGENT_PERSONA
        self._agent_adk_name = AGENT_ADK_NAME
        self._client = None
        self._adk_agent = None
        self._use_adk = False
        self._init_backend()

    def _init_backend(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key or api_key == "your-gemini-api-key":
            logger.warning("GEMINI_API_KEY not set — agent will use rule-based fallback responses")
            return

        try:
            from google.adk.agents import Agent
            from google.adk.tools import FunctionTool

            tools = [FunctionTool(func=fn) for fn in _tool_functions.values()]
            self._adk_agent = Agent(
                name=self._agent_adk_name,
                model=self.model,
                instruction=self._agent_persona,
                tools=tools,
            )
            self._use_adk = True
            logger.info("Initialized Google ADK agent (model=%s)", self.model)
            return
        except Exception as exc:
            logger.info("ADK unavailable, using google-genai: %s", exc)

        try:
            from google import genai

            self._client = genai.Client(api_key=api_key)
            logger.info("Initialized google-genai client (model=%s)", self.model)
        except Exception as exc:
            logger.error("Failed to init Gemini client: %s", exc)

    async def run_adk(self, message: str) -> tuple[str, list[dict[str, Any]]]:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types

        session_service = InMemorySessionService()
        runner = Runner(
            agent=self._adk_agent,
            app_name=self._agent_adk_name,
            session_service=session_service,
        )
        session = await session_service.create_session(
            app_name=self._agent_adk_name, user_id="vendor"
        )
        tool_calls: list[dict[str, Any]] = []
        final_text = ""

        async for event in runner.run_async(
            user_id="vendor",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=message)]),
        ):
            if hasattr(event, "content") and event.content:
                for part in event.content.parts or []:
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        tool_calls.append({"name": fc.name, "args": dict(fc.args or {})})
                    if hasattr(part, "text") and part.text:
                        final_text = part.text

        return final_text or "I processed your request but have no text response.", tool_calls

    def run_genai(self, message: str) -> tuple[str, list[dict[str, Any]]]:
        from google.genai import types

        tool_calls: list[dict[str, Any]] = []
        contents: list[types.Content] = [
            types.Content(
                role="user",
                parts=[types.Part(text=f"{self._agent_persona}\n\nUser: {message}")],
            )
        ]

        tools_config = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=t["name"],
                    description=t["description"],
                    parameters=t["parameters"],
                )
                for t in _tool_declarations
            ]
        )

        for turn in range(1, MAX_AGENT_TURNS + 1):
            logger.info("Agent turn %s/%s", turn, MAX_AGENT_TURNS)

            if len(tool_calls) >= MAX_AGENT_TURNS:
                break

            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(tools=[tools_config]),
            )

            if not response.candidates:
                break

            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            function_calls = [p.function_call for p in parts if p.function_call]
            if not function_calls:
                text_parts = [p.text for p in parts if p.text]
                final = " ".join(text_parts).strip() or "Done."
                return final, tool_calls

            contents.append(candidate.content)
            response_parts: list[types.Part] = []

            for fc in function_calls:
                if len(tool_calls) >= MAX_AGENT_TURNS:
                    break
                args = dict(fc.args) if fc.args else {}
                tool_calls.append({"name": fc.name, "args": args})
                result = _execute_tool(fc.name, args)
                response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response=result,
                        )
                    )
                )

            contents.append(types.Content(role="user", parts=response_parts))

        return "I reached the maximum reasoning steps. Please try a simpler question.", tool_calls

    async def chat(self, message: str) -> tuple[str, list[dict[str, Any]]]:
        if self._use_adk and self._adk_agent:
            try:
                return await self.run_adk(message)
            except Exception as exc:
                error_text = str(exc)
                logger.warning("ADK run failed, falling back: %s", error_text)
                if _api_error_is_blocked(error_text):
                    from src.agent_fallback import process_message_fallback

                    result = await process_message_fallback(message)
                    return result["response"], result["tool_calls"]

        if self._client:
            try:
                return await asyncio.to_thread(self.run_genai, message)
            except Exception as exc:
                logger.error("GenAI run failed: %s", exc)
                from src.agent_fallback import process_message_fallback

                result = await process_message_fallback(message)
                return f"Agent error: {exc}. Using rule-based fallback.\n\n{result['response']}", result["tool_calls"]

        from src.agent_fallback import process_message_fallback

        result = await process_message_fallback(message)
        return result["response"], result["tool_calls"]


def _build_tool_registry() -> None:
    global _tool_functions, _tool_declarations

    from src.tools.calculate_pricing import calculate_bundle_pricing
    from src.tools.generate_bundles import generate_bundles
    from src.tools.generate_promo import generate_promo
    from src.tools.mcp_integration import mcp_query_inventory
    from src.tools.query_inventory import query_inventory

    _tool_functions = {
        "query_inventory": query_inventory,
        "mcp_query_inventory": mcp_query_inventory,
        "generate_bundles": generate_bundles,
        "calculate_bundle_pricing": calculate_bundle_pricing,
        "generate_promo": generate_promo,
    }

    _tool_declarations = [
        {
            "name": "query_inventory",
            "description": (
                "Query festival product inventory from MongoDB Atlas. Returns product details "
                "including name, category, cost, sell price, and stock quantity."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "overstocked", "low_stock", "category"],
                        "description": "Type of inventory filter",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by product category (Drinks, Food, Merchandise, Accessories)",
                    },
                    "stock_threshold": {
                        "type": "number",
                        "description": "Stock quantity threshold for overstocked/low_stock filters",
                        "default": 50,
                    },
                },
                "required": ["filter_type"],
            },
        },
        {
            "name": "generate_bundles",
            "description": (
                "Generate optimized product bundle recommendations from inventory. "
                "Identifies complementary products and calculates bundle pricing."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific product names to consider",
                    },
                    "max_bundle_size": {"type": "number", "default": 4},
                    "target_discount_percent": {"type": "number", "default": 15},
                    "num_bundles": {"type": "number", "default": 3},
                    "min_margin_percent": {
                        "type": "number",
                        "description": "Minimum margin percent filter",
                    },
                },
            },
        },
        {
            "name": "calculate_bundle_pricing",
            "description": (
                "Calculate detailed pricing and margin analysis for a specific product bundle."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bundle_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "product_id": {"type": "string"},
                                "quantity": {"type": "number", "default": 1},
                            },
                            "required": ["product_id"],
                        },
                    },
                    "discount_percent": {"type": "number", "default": 15},
                },
                "required": ["bundle_items"],
            },
        },
        {
            "name": "generate_promo",
            "description": "Generate marketing-ready promotional descriptions for product bundles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bundle_name": {"type": "string"},
                    "bundle_items": {"type": "array", "items": {"type": "string"}},
                    "bundle_price": {"type": "number"},
                    "original_price": {"type": "number"},
                    "tone": {
                        "type": "string",
                        "enum": ["festival", "professional", "casual"],
                        "default": "festival",
                    },
                },
                "required": ["bundle_name", "bundle_items", "bundle_price", "original_price"],
            },
        },
        {
            "name": "mcp_query_inventory",
            "description": "Query inventory via MongoDB MCP Server",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_type": {
                        "type": "string",
                        "enum": ["all", "overstocked", "low_stock"],
                        "description": "Type of inventory filter",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by product category (Drinks, Food, Merchandise, Accessories)",
                    },
                },
            },
        },
    ]


async def _initialize_agent() -> None:
    """All heavy imports and initialization happen here."""
    global _agent_loop, _db_client, _mcp_client, _startup_complete

    logger.info("=" * 50)
    logger.info("STARTUP: Beginning heavy initialization...")
    logger.info("=" * 50)

    use_local = os.getenv("USE_LOCAL_DATA", "false").lower() in ("1", "true", "yes")

    if not use_local:
        try:
            logger.info("STARTUP: Importing mongo client...")
            from src.db.mongo_client import get_mongo_client

            logger.info("STARTUP: Connecting to MongoDB...")
            _db_client = get_mongo_client()
            logger.info("STARTUP: MongoDB connected successfully")
        except Exception as exc:
            logger.warning("STARTUP: MongoDB connection failed: %s", exc)
            logger.warning("STARTUP: Will operate with limited functionality")
    else:
        logger.info("STARTUP: USE_LOCAL_DATA=true — skipping MongoDB connection")

    try:
        logger.info("STARTUP: Initializing MongoDB MCP client...")
        from src.mcp_client import MCPClient
        from src.tools.mcp_integration import set_mcp_client

        mcp = MCPClient()
        mcp_ready = await mcp.connect(timeout=8.0)
        if mcp_ready:
            _mcp_client = mcp
            set_mcp_client(mcp)
            logger.info("STARTUP: MongoDB MCP Server connected successfully")
            logger.info(
                "STARTUP: MCP tools available: %s",
                [t["name"] for t in mcp.list_tools()],
            )
        else:
            logger.warning("STARTUP: MCP server not available (npx may be missing)")
    except Exception as exc:
        logger.warning("STARTUP: MCP initialization skipped: %s", exc)

    try:
        logger.info("STARTUP: Importing agent tools...")
        _build_tool_registry()
        logger.info("STARTUP: Tools imported successfully")
    except Exception as exc:
        logger.error("STARTUP: Tool import failed: %s", exc)

    if _gemini_configured():
        logger.info("STARTUP: Gemini API key detected, initializing agent loop...")
    else:
        logger.warning("STARTUP: No Gemini API key — rule-based fallback only")

    try:
        _agent_loop = GeminiAgentLoop()
        logger.info("STARTUP: Agent loop initialized")
    except Exception as exc:
        logger.warning("STARTUP: Agent loop initialization failed: %s", exc)

    _startup_complete = True
    logger.info("=" * 50)
    logger.info("STARTUP: Initialization complete")
    logger.info("=" * 50)


@app.on_event("startup")
async def startup_event() -> None:
    """FastAPI startup — triggers background initialization."""
    asyncio.create_task(_initialize_agent())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _mcp_client
    if _mcp_client:
        logger.info("SHUTDOWN: Closing MCP client...")
        await _mcp_client.close()


# ============================================================
# CHAT ENDPOINT
# ============================================================


def _extract_bundles(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for tc in tool_calls:
        if tc.get("name") == "generate_bundles":
            result = tc.get("result") or {}
            bundles.extend(result.get("bundles", []))
    return bundles


async def _handle_chat(request: ChatRequest) -> ChatResponse:
    logger.info("Chat request (%s chars)", len(request.message))

    if not _startup_complete:
        return ChatResponse(
            response="The agent is still waking up. Please try again in a few seconds.",
            tool_calls=[],
        )

    if _agent_loop is None:
        from src.agent_fallback import process_message_fallback

        result = await process_message_fallback(request.message)
        return ChatResponse(**result)

    response_text, tool_calls = await _agent_loop.chat(request.message)

    enriched_calls: list[dict[str, Any]] = []
    bundles: list[dict[str, Any]] = []
    for turn_idx, tc in enumerate(tool_calls, start=1):
        if turn_idx > MAX_AGENT_TURNS:
            logger.info("Max agent turns reached — stopping tool execution")
            break
        name = tc.get("name", "")
        args = tc.get("args", {})
        if tc.get("result") is not None:
            result = tc["result"]
        elif name:
            result = await asyncio.to_thread(_execute_tool, name, args)
        else:
            result = {}
        entry = {"name": name, "args": args, "result": result}
        enriched_calls.append(entry)
        if name == "generate_bundles" and result.get("bundles"):
            bundles.extend(result["bundles"])

    if not bundles:
        bundles = _extract_bundles(enriched_calls)

    return ChatResponse(response=response_text, tool_calls=enriched_calls, bundles=bundles)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await asyncio.wait_for(_handle_chat(request), timeout=MAX_REQUEST_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning("Chat request timed out after %ss", MAX_REQUEST_TIMEOUT_S)
        return ChatResponse(
            response=(
                "I'm taking too long to think — let me give you my best quick answer... "
                "Try asking for specific items like 'Bundle Lemonade and Kettle Corn'."
            ),
            tool_calls=[],
            timeout=True,
        )
    except Exception as exc:
        logger.error("Chat endpoint error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ============================================================
# STATIC FRONTEND
# ============================================================

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import socket
    import uvicorn

    port = int(os.getenv("PORT", "8080"))

    def _port_in_use(check_port: int) -> tuple[bool, str | None]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", check_port))
                return False, None
            except OSError as exc:
                return True, str(exc)

    in_use, bind_error = _port_in_use(port)
    if in_use:
        logger.error(
            "Port %s already in use (%s). Try: lsof -i :%s or PORT=8081 python src/agent_main.py",
            port,
            bind_error,
            port,
        )
        raise SystemExit(
            f"Port {port} is already in use. Run `lsof -i :{port}` to find the process, "
            f"stop it, or start with PORT=8081 python src/agent_main.py"
        )

    uvicorn.run("src.agent_main:app", host="0.0.0.0", port=port, reload=False)
