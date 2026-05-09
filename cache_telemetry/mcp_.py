# server.py
#
# Simple MCP HTTP/SSE server that exposes all data from every .jsonl file.
#
# Install:
#   pip install mcp
#
# Run:
#   python server.py ./data
#
# Server:
#   http://localhost:8000/sse
#
# Example Inspector:
#   npx @modelcontextprotocol/inspector
#
# Example Claude Desktop MCP config:
# {
#   "mcpServers": {
#     "jsonl-server": {
#       "url": "http://localhost:8000/sse"
#     }
#   }
# }

import json
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

DATA_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else ".")

mcp = FastMCP("jsonl-server")


def load_all_jsonl() -> list[dict[str, Any]]:
    results = []

    if not DATA_DIR.exists():
        return [{
            "error": f"Directory does not exist: {DATA_DIR}"
        }]

    for file_path in DATA_DIR.rglob("*.jsonl"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        parsed = json.loads(line)

                        results.append({
                            "file": str(file_path),
                            "line": line_num,
                            "data": parsed,
                        })

                    except json.JSONDecodeError as e:
                        results.append({
                            "file": str(file_path),
                            "line": line_num,
                            "error": f"JSON decode error: {e}",
                            "raw": line,
                        })

        except Exception as e:
            results.append({
                "file": str(file_path),
                "error": str(e),
            })

    return results


@mcp.tool()
def get_jsonl_data() -> list[dict[str, Any]]:
    """
    Return all JSON objects from all .jsonl files.
    """
    return load_all_jsonl()


@mcp.tool()
def list_jsonl_files() -> list[str]:
    """
    List all discovered .jsonl files.
    """
    return [str(p) for p in DATA_DIR.rglob("*.jsonl")]


if __name__ == "__main__":
    mcp.run(
        transport="sse",
        # host="0.0.0.0",
        # port=8000,
    )