"""skill/fetch_http_content.py - Fetch content from a remote HTTP server using basic GET request.

SKILL_META:
{
  "name": "fetch_http_content",
  "description": "Fetch content from a remote HTTP server using basic GET request.",
  "category": "http",
  "test_target": "example.com host to fetch homepage content",
  "test_args": "104.18.27.120 80 /",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import http.client
import json
import sys
from typing import Any

def main(host: str, port: int, path: str) -> dict[str, Any]:
    """Fetch content from a remote HTTP server using basic GET request."""
    result: dict[str, Any] = {
        "success": False,
        "content": "",
        "headers": {},
        "error": ""
    }

    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        try:
            conn.request("GET", path)
            response = conn.getresponse()

            result["headers"] = dict(response.getheaders())
            result["content"] = response.read().decode("utf-8", errors="replace")
            result["success"] = True
        finally:
            conn.close()

    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
    except OSError as e:
        result["error"] = f"Network error: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch content from a remote HTTP server")
    parser.add_argument("host", nargs="?", default="example.com", help="Remote host")
    parser.add_argument("port", nargs="?", type=int, default=80, help="Remote port")
    parser.add_argument("path", nargs="?", default="/", help="Request path")
    args = parser.parse_args()

    port = args.port
    if isinstance(port, str):
        try:
            port = int(port)
        except ValueError:
            print(json.dumps({"success": False, "error": "Invalid port number"}, ensure_ascii=False, indent=2))
            sys.exit(1)

    result = main(args.host, port, args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))