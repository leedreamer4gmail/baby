"""skill/fetch_http_content.py - Fetch content from a remote HTTP server using basic GET request.

SKILL_META:
{
  "name": "fetch_http_content",
  "description": "Fetch content from a remote HTTP server using basic GET request.",
  "category": "http",
  "test_target": "example.com host to fetch homepage content",
  "test_args": "104.18.27.120 80 /",
  "version": "1.0"
}
"""
from __future__ import annotations

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
    if len(sys.argv) >= 4:
        host_arg = sys.argv[1]
        port_arg = int(sys.argv[2])
        path_arg = sys.argv[3]
        print(json.dumps(main(host_arg, port_arg, path_arg), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(main("example.com", 80, "/"), ensure_ascii=False, indent=2))