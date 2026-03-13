"""skill/fetch_http_with_headers_http.py - Fetch HTTP content with custom headers to bypass detections like Cloudflare.

SKILL_META:
{
  "name": "fetch_http_with_headers_http",
  "description": "Fetch HTTP content with custom headers to bypass detections like Cloudflare.",
  "category": "http",
  "test_target": "Cloudflare-protected IP 104.18.27.120:80，抓取根路径内容。",
  "test_args": "--host 104.18.27.120 --port 80 --path / --headers '{\"User-Agent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36\"}'",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any

def parse_args() -> tuple[str, int, str, dict[str, str]]:
    """Parse command line arguments."""
    args = sys.argv[1:]
    host = ""
    port = 80
    path = "/"
    headers: dict[str, str] = {}

    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            host = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            port = int(args[i + 1])
            i += 2
        elif args[i] == "--path" and i + 1 < len(args):
            path = args[i + 1]
            i += 2
        elif args[i] == "--headers" and i + 1 < len(args):
            headers = json.loads(args[i + 1])
            i += 2
        else:
            i += 1

    return host, port, path, headers

def main(host: str = "", port: int = 80, path: str = "/", headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch HTTP content with custom headers."""
    result: dict[str, Any] = {
        "success": False,
        "status": 0,
        "headers": {},
        "content": ""
    }

    if headers is None:
        headers = {}

    # Parse from sys.argv if not provided
    if not host and len(sys.argv) > 1:
        host, port, path, headers = parse_args()

    if not host:
        result["content"] = "Error: host is required"
        return result

    try:
        url = f"http://{host}:{port}{path}"
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, timeout=30) as response:
            result["status"] = response.status
            result["headers"] = dict(response.headers)
            result["content"] = response.read().decode("utf-8", errors="replace")
            result["success"] = True

    except json.JSONDecodeError as e:
        result["content"] = f"Error: Invalid JSON in headers: {e}"
    except ConnectionError as e:
        result["content"] = f"Error: Connection failed: {e}"
    except TimeoutError as e:
        result["content"] = f"Error: Request timeout: {e}"
    except Exception as e:
        result["content"] = f"Error: {type(e).__name__}: {e}"

    return result

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))