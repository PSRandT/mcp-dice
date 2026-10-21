import socket
import subprocess
import sys
import time
from unittest.mock import patch

import httpx
import pytest

from mcp_dice.server import parse_dice_notation, roll_dice
from tools.verify_mcp import run_http, run_stdio, INVALID


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("notation,expected", [
    ("1d20", (1, 20, 0)), ("3d6", (3, 6, 0)), ("2d8+1", (2, 8, 1)),
    ("1d20-2", (1, 20, -2)), ("1d100", (1, 100, 0)), ("1d2", (1, 2, 0)),
    ("100d1000000-1000000", (100, 1000000, -1000000)),
])
def test_parser(notation, expected):
    assert parse_dice_notation(notation) == expected


@pytest.mark.parametrize("notation", INVALID + [None, 42, "1d20\n"])
def test_parser_rejects(notation):
    with pytest.raises(ValueError):
        parse_dice_notation(notation)


@pytest.mark.parametrize("args", [(101, 6, 0), (1, 1000001, 0), (1, 6, 1000001)])
def test_limit_before_random(args):
    with patch("random.randint") as random_call:
        with pytest.raises(ValueError):
            roll_dice(*args)
        random_call.assert_not_called()


@pytest.fixture
def endpoint():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "mcp_dice.http_server:create_app",
             "--factory", "--fd", str(sock.fileno()), "--log-level", "warning"],
            pass_fds=(sock.fileno(),),
        )
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(100):
                assert process.poll() is None, "HTTP server exited"
                try:
                    if httpx.get(base + "/health", timeout=0.2, trust_env=False).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.05)
            else:
                pytest.fail("HTTP startup timed out")
            yield base
        finally:
            process.terminate()
            process.wait(timeout=5)


@pytest.mark.anyio
async def test_real_http(endpoint):
    await run_http(endpoint + "/mcp")


@pytest.mark.anyio
async def test_real_stdio():
    await run_stdio()


def test_http_routes_and_body_limit(endpoint):
    with httpx.Client(base_url=endpoint, trust_env=False) as client:
        assert client.get("/health").json() == {"ok": True, "service": "mcp-dice"}
        for method in ["GET", "HEAD", "DELETE"]:
            response = client.request(method, "/mcp")
            assert response.status_code == 405
            assert response.headers["allow"] == "POST"
            assert "location" not in response.headers
            if method == "HEAD":
                assert response.content == b""
        response = client.post("/mcp", content=b" " * 17000,
                               headers={"content-type": "application/json"})
        assert response.status_code == 413
        assert client.get("/health").status_code == 200
