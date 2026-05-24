"""Python bridge to the MongoDB MCP Server (Node.js via stdio JSON-RPC)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Python bridge to the MongoDB MCP Server (Node.js via stdio JSON-RPC).
    https://github.com/mongodb-js/mongodb-mcp-server
    """

    def __init__(self, connection_string: str | None = None) -> None:
        self.connection_string = (
            connection_string
            or os.getenv("MDB_MCP_CONNECTION_STRING")
            or os.getenv("MONGO_URI")
        )
        self.process: asyncio.subprocess.Process | None = None
        self._initialized = False
        self._tools: list[dict[str, Any]] = []
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def connect(self, timeout: float = 15.0) -> bool:
        """Start the MCP server subprocess and perform initialize handshake."""
        if self._initialized:
            return True

        if not self.connection_string:
            logger.warning("MCP: No connection string provided")
            return False

        env = os.environ.copy()
        env["MDB_MCP_CONNECTION_STRING"] = self.connection_string

        if not shutil.which("mongodb-mcp-server"):
            logger.warning(
                "MCP: mongodb-mcp-server binary not found in PATH for current user"
            )
            return False

        try:
            logger.info("MCP: Starting mongodb-mcp-server subprocess...")
            self.process = await asyncio.create_subprocess_exec(
                "mongodb-mcp-server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            logger.info("MCP: Subprocess started. PID=%s", self.process.pid)

            init_msg = {
                "jsonrpc": "2.0",
                "id": self._next(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "festival-agent", "version": "1.0.0"},
                },
            }

            await self._send(init_msg)
            await asyncio.sleep(0.5)
            init_resp = await asyncio.wait_for(self._receive(), timeout=timeout)

            if "error" in init_resp:
                logger.error("MCP: Initialize error: %s", init_resp["error"])
                await self.close()
                return False

            await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

            tools_msg = {
                "jsonrpc": "2.0",
                "id": self._next(),
                "method": "tools/list",
            }
            await self._send(tools_msg)
            tools_resp = await asyncio.wait_for(self._receive(), timeout=timeout)

            self._tools = tools_resp.get("result", {}).get("tools", [])
            logger.info(
                "MCP: Connected. Available tools: %s",
                [t["name"] for t in self._tools],
            )

            self._initialized = True
            return True

        except FileNotFoundError:
            logger.warning(
                "MCP: 'mongodb-mcp-server' not found. Install it globally in the image."
            )
            return False
        except asyncio.TimeoutError:
            logger.warning("MCP: Connection timed out. MCP server unavailable.")
            await self.close()
            return False
        except Exception as exc:
            logger.warning("MCP: Unexpected error during connect: %s", exc)
            await self.close()
            return False

    async def call_tool(
        self, name: str, arguments: dict[str, Any], timeout: float = 10.0
    ) -> dict[str, Any]:
        """Call an MCP tool by name."""
        if not self._initialized or not self.process:
            return {"error": "MCP client not initialized"}

        async with self._lock:
            msg = {
                "jsonrpc": "2.0",
                "id": self._next(),
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }

            await self._send(msg)
            resp = await asyncio.wait_for(self._receive(), timeout=timeout)
            return resp.get("result", {})

    def list_tools(self) -> list[dict[str, Any]]:
        return self._tools

    async def close(self) -> None:
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except Exception:
                self.process.kill()
            self.process = None
        self._initialized = False
        self._tools = []

    def _next(self) -> int:
        self._next_id += 1
        return self._next_id

    async def _send(self, msg: dict[str, Any]) -> None:
        if not self.process or not self.process.stdin:
            raise ConnectionError("MCP server stdin unavailable")
        data = json.dumps(msg) + "\n"
        self.process.stdin.write(data.encode())
        await self.process.stdin.drain()

    async def _receive(self) -> dict[str, Any]:
        if not self.process or not self.process.stdout:
            raise ConnectionError("MCP server stdout unavailable")
        line = await self.process.stdout.readline()
        if not line:
            raise ConnectionError("MCP server closed stdout")
        return json.loads(line.decode())
