# mcp-dice: A MCP Server for Rolling Dice

[![smithery badge](https://smithery.ai/badge/mcp-dice)](https://smithery.ai/protocol/mcp-dice)
![screenshot](https://github.com/user-attachments/assets/ff7615b8-46ba-4be5-8287-8e1bf348ae28)

A Model Context Protocol (MCP) server that enables Large Language Models (LLMs) to roll dice. It accepts standard dice notation (e.g., `1d20`) and returns both individual rolls and their sum.

<a href="https://glama.ai/mcp/servers/vzu553gv26"><img width="380" height="200" src="https://glama.ai/mcp/servers/vzu553gv26/badge" /></a>

## Features

- Supports standard dice notation (e.g., `1d20`, `3d6`, `2d8+1`)
- Returns both individual rolls and the total sum
- Easy integration with Claude Desktop
- Compatible with MCP Inspector for debugging

## Independent remote deployment

This fork preserves the upstream 0.1.2 dice behavior and stdio entry point.
Upstream baseline: `535bb98c95f2c5ffc4802d6397980154f0b3808b`.
Both transports use the same `Server` instance and tool handlers.
Randomness remains `random.randint(1, n_sides)`; no game rules are interpreted.

### Local run and tests

```bash
uv sync --extra dev --frozen
uv run pytest
uv run mcp-dice                 # original stdio entry point
uv run mcp-dice-http            # HTTP on 127.0.0.1:8000
# In another terminal:
uv run python tools/verify_mcp.py --stdio
uv run python tools/verify_mcp.py http://127.0.0.1:8000/mcp
```

`python -m mcp_dice` is also a stdio entry point. `uvx mcp-dice` still refers
to the upstream PyPI release; it does not automatically install this fork.

### HTTP contract

- `POST /mcp`: official MCP SDK Streamable HTTP, stateless JSON responses.
- `GET /mcp`, `HEAD /mcp`, and other non-POST methods: 405, `Allow: POST`, no redirect or HTML.
- `GET /health`: `{"ok": true, "service": "mcp-dice"}`.
- No authentication. HTTP request bodies are limited to 16 KiB.
- `HOST` defaults to `127.0.0.1`; `PORT` defaults to `8000`.
- Tool annotations: `readOnlyHint=true`, `destructiveHint=false`, `openWorldHint=false`.

The SDK is locked in `uv.lock` (MCP 1.30.0); deployment uses `uv sync --frozen`.

### Input limits

Lowercase `NdM` with an optional signed integer modifier. At most 64 characters,
1–100 dice, 2–1,000,000 sides per die, modifier −1,000,000 to +1,000,000.
Invalid or out-of-range calls return MCP `isError: true` without rolling dice.
The original normalized output notation and local ISO timestamp format remain.
`rolls`, `sum`, `modifier`, `total`, `notation`, and `timestamp` are preserved.

### Render and ChatGPT

Create a Render Blueprint from your independent fork using `render.yaml`.
The free Python service starts `mcp-dice-http`, listens on `0.0.0.0:$PORT`,
and receives HTTPS through Render. It does not depend on the upstream author.
When Render reports Live, copy its actual service URL and append `/mcp`.

```bash
uv run python tools/verify_mcp.py https://YOUR-ACTUAL-HOST.onrender.com/mcp
```

Run this public SDK gate before ChatGPT setup. It verifies initialize, tool
metadata, all requested dice forms, arithmetic consistency, limits, tool errors,
and successful calls after errors.

In ChatGPT create `Dice Roller` with the actual HTTPS `/mcp` URL and no auth.
Confirm `roll_dice` is visible; invoke `1d20`, `3d6+2`, and `1d100` and inspect
the actual MCP invocation records. SDK success alone is not ChatGPT acceptance.

Free Render instances sleep when idle; open `/health` and wait for it to return
200 before scanning. Cold starts can exceed the client's timeout. This minimal
service bounds each request but does not include distributed traffic quotas.

Rollback: redeploy a previous working commit in this fork, or remove only this
Render service. The original author's repository and service are unaffected.

## Installation

### Installing via Smithery

To install Dice Roller for Claude Desktop automatically via [Smithery](https://smithery.ai/protocol/mcp-dice):

```bash
npx @smithery/cli install mcp-dice --client claude
```

Make `uv` available: https://docs.astral.sh/uv/getting-started/installation/

## Usage

### Basic Command Line Usage

```shell
# Using uvx
uvx mcp-dice
```

### Input Format

The server accepts a JSON object with a `notation` field:
```json
{
  "notation": "2d6+3"
}
```

Example responses:
```json
{
  "rolls": [
    3,
    1
  ],
  "sum": 4,
  "modifier": 3,
  "total": 7,
  "notation": "2d6+3",
  "timestamp": "2024-12-03T16:36:38.926452"
}
```

## Claude Desktop Configuration

### Location
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

### Examples

<details>
<summary>macOS Configuration</summary>

```json
{
  "mcpServers": {
    "dice": {
      "command": "uvx",
      "args": ["mcp-dice"]
    }
  }
}
```

</details>

<details>
<summary>WSL Configuration</summary>

```json
{
  "mcpServers": {
    "dice": {
      "command": "wsl",
      "args": [
        "-e",
        "zsh",
        "-lc",
        "uvx mcp-dice"
      ]
    }
  }
}
```

Note: Replace `zsh` with your login shell.
</details>

## Development and Debugging

### Installing Development Dependencies

```shell
# Clone the repository
git clone https://github.com/yourusername/mcp-dice
cd mcp-dice

# Install development dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```shell
uv run pytest
```

### Using MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a useful tool for debugging your MCP server. Install and run it using npm:

```shell
npx @modelcontextprotocol/inspector uvx mcp-dice
```

### Claude Desktop Configuration for Development

<details>
<summary>macOS configuration (local dev)</summary>

```json
{
  "mcpServers": {
    "dice": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "path/to/mcp-dice-repo",
        "mcp-dice"
      ]
    }
  }
}
```

Note: Replace `path/to/mcp-dice-repo` with the path to the repository on your filesystem.
</details>

<details>
<summary>Windows (WSL) configuration (local dev)</summary>

```json
{
  "mcpServers": {
    "dice": {
      "command": "wsl",
      "args": [
        "-e",
        "zsh",
        "-lc",
        "uv run --directory path/to/mcp-dice-repo mcp-dice"
      ]
    }
  }
}
```

Note: Replace `zsh` with your login shell. Also, replace `path/to/mcp-dice-repo` with the path to the repository on your WSL filesystem.
</details>
