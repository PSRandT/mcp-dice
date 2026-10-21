"""HTTP adapter for the same low-level MCP server used by stdio."""
import os
from contextlib import asynccontextmanager

import uvicorn
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from .server import app as mcp_server


def create_app():
    manager = StreamableHTTPSessionManager(
        mcp_server, stateless=True, json_response=True,
        max_request_body_size=16 * 1024,
    )

    @asynccontextmanager
    async def lifespan(app):
        async with manager.run():
            yield

    # ASGI callable instance keeps Starlette from wrapping it as a Request endpoint.
    class MCPEndpoint:
        async def __call__(self, scope, receive, send):
            if scope["method"] != "POST":
                response = JSONResponse(
                    {"jsonrpc": "2.0", "id": None,
                     "error": {"code": -32000, "message": "Only POST is supported"}},
                    status_code=405, headers={"Allow": "POST"},
                )
                await response(scope, receive, send)
                return
            await manager.handle_request(scope, receive, send)

    async def health(request):
        return JSONResponse({"ok": True, "service": "mcp-dice"})

    return Starlette(
        routes=[Route("/mcp", MCPEndpoint()), Route("/health", health)],
        lifespan=lifespan,
    )


def main():
    uvicorn.run(create_app(), host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
