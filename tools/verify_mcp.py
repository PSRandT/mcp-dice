"""Verify the real MCP protocol over HTTP or stdio with the official SDK."""
import argparse
import asyncio
import json
import sys
from datetime import datetime

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

VALID = ["1d20", "3d6", "2d8+1", "1d20-2", "1d100", "1d2", "10d10",
         "3d6+2", "2d8-3", "100d1000000+1000000"]
INVALID = ["d20", "1d", "abc", "0d6", "1d1", "2d6++", "2D6",
           "101d6", "1d1000001", "1d6+1000001", "1d6-1000001",
           "999999999d999999999", "9" * 1000 + "d6"]


def check_roll(result, notation):
    assert not result.isError, result
    data = json.loads(result.content[0].text)
    assert set(data) == {"rolls", "sum", "modifier", "total", "notation", "timestamp"}
    dice, rest = notation.split("d")
    import re
    match = re.fullmatch(r"(\d+)([+-]\d+)?", rest)
    sides, modifier = int(match[1]), int(match[2] or 0)
    assert len(data["rolls"]) == int(dice)
    assert all(type(v) is int and 1 <= v <= sides for v in data["rolls"])
    assert data["sum"] == sum(data["rolls"])
    assert data["modifier"] == modifier
    assert data["total"] == data["sum"] + modifier
    assert data["notation"] == notation
    datetime.fromisoformat(data["timestamp"])
    return data


async def verify(session):
    initialized = await session.initialize()
    print(f"initialize PASS protocol={initialized.protocolVersion}")
    listed = await session.list_tools()
    assert [t.name for t in listed.tools] == ["roll_dice"]
    tool = listed.tools[0]
    assert tool.description and "2d6+3" in tool.description
    assert tool.inputSchema["required"] == ["notation"]
    assert tool.inputSchema["properties"]["notation"]["type"] == "string"
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.openWorldHint is False
    print("tools/list PASS " + listed.model_dump_json(exclude_none=True))
    for notation in VALID:
        data = check_roll(await session.call_tool("roll_dice", {"notation": notation}), notation)
        print(f"roll_dice PASS {notation} total={data['total']}")
    for notation in INVALID:
        result = await session.call_tool("roll_dice", {"notation": notation})
        assert result.isError, notation
        assert result.content[0].text
        print(f"tool error PASS {notation[:40]}")
    for args in [{}, {"notation": None}, {"notation": 20}]:
        result = await session.call_tool("roll_dice", args)
        assert result.isError
    check_roll(await session.call_tool("roll_dice", {"notation": "1d20"}), "1d20")
    print("recovery after invalid inputs PASS")


async def run_http(url):
    async def log_response(response):
        await response.aread()
        print(f"HTTP {response.request.method} {response.status_code} "
              f"{response.headers.get('content-type', '')}")
    async with httpx.AsyncClient(timeout=60, event_hooks={"response": [log_response]}) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await verify(session)


async def run_stdio():
    parameters = StdioServerParameters(command=sys.executable, args=["-m", "mcp_dice"])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await verify(session)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?")
    parser.add_argument("--stdio", action="store_true")
    args = parser.parse_args()
    if not args.stdio and not args.url:
        parser.error("provide an HTTPS MCP URL or --stdio")
    asyncio.run(run_stdio() if args.stdio else run_http(args.url))
