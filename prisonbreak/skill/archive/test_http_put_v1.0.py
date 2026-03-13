"""skill/test_http_put.py - Test if HTTP server allows PUT method and attempt to upload a test file.

SKILL_META:
{
  "name": "test_http_put",
  "description": "Test if HTTP server allows PUT method and attempt to upload a test file.",
  "category": "http",
  "test_target": "已发现的HTTP服务器104.18.27.120:80",
  "test_args": "104.18.27.120 80 /test.txt 'baby test'",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import http.client
from typing import Any

def main(host: str, port: int = 80, path: str = '/test.txt', content: str = 'test') -> dict[str, Any]:
    """Test if HTTP server allows PUT method and attempt to upload a test file."""
    result: dict[str, Any] = {"allowed": False, "response": "", "error": "", "success": False}

    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        headers = {"Content-Type": "text/plain", "Content-Length": str(len(content))}
        conn.request("PUT", path, content, headers)
        response = conn.getresponse()
        result["response"] = f"{response.status} {response.reason}"

        if 200 <= response.status < 300:
            result["allowed"] = True
            result["success"] = True

        response.read()
        conn.close()

    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
    except Exception as e:
        result["error"] = f"Error: {e}"

    return result

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 1:
        h = args[0]
        p = int(args[1]) if len(args) > 1 else 80
        pt = args[2] if len(args) > 2 else '/test.txt'
        c = args[3] if len(args) > 3 else 'test'
        print(json.dumps(main(h, p, pt, c), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(main("104.18.27.120", 80, "/test.txt", "baby test"), ensure_ascii=False, indent=2))