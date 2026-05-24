# MongoDB MCP Server Integration

This project integrates the official MongoDB MCP (Model Context Protocol) Server
to provide live, tool-based access to MongoDB Atlas inventory data.

## MCP Architecture

```
[User] → [Festival Bundle Agent] → [MongoDB MCP Server] → [MongoDB Atlas]
                  ↑
            [Google Agent Builder + Gemini]
```

The MongoDB MCP Server is a Node.js process that exposes MongoDB operations
as standardized tools via JSON-RPC over stdio.

## Tools Exposed by MCP Server

- `find` — Query documents with filters, projection, sorting
- `aggregate` — Run aggregation pipelines
- `count` — Count matching documents
- `distinct` — Get unique values for a field

## Connection String

The MCP client reads `MDB_MCP_CONNECTION_STRING` first, then falls back to `MONGO_URI`.
No duplicate secret is required in Cloud Run — the same Atlas URI works for both pymongo and MCP.

## Local Testing

```bash
# Test MCP server standalone
export MDB_MCP_CONNECTION_STRING="mongodb+srv://..."
npx -y mongodb-mcp-server@latest
# Then paste: {"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

## Cloud Run Deployment

The Dockerfile installs Node.js so `npx mongodb-mcp-server@latest` works inside
the container. The agent initializes the MCP client during startup and falls
back to pymongo if the MCP server is unavailable.

Ensure Atlas **Network Access** allows Cloud Run (`0.0.0.0/0`) and the database user has
**readWrite** on the database named in `MONGO_DB_NAME` (default: `festival_bundle_agent`).
