"""skill/check_http_methods.py - Send OPTIONS request to HTTP server and parse allowed methods.

SKILL_META:
{
  "name": "check_http_methods",
  "description": "Send OPTIONS request to HTTP server and parse allowed methods.",
  "category": "http",
  "test_target": "209.51.188.20 HTTP service",
  "test_args": "209.51.188.20 80 /",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
from http.client import HTTPConnection, HTTPException, socket
from typing import Any

def parse_allow_header(header_value: str | None) -> list[str]:
    """Parse HTTP Allow header value into list of methods."""
    if not header_value:
        return []
    return [method.strip().upper() for method in header_value.split(",") if method.strip()]

def main(host: str, port: int = 80, path: str = "/") -> dict[str, Any]:
    """Send OPTIONS request to HTTP server and parse allowed methods."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    conn: HTTPConnection | None = None

    try:
        conn = HTTPConnection(host, port, timeout=10)
        conn.request("OPTIONS", path)
        response = conn.getresponse()

        allow_header = response.getheader("Allow")
        allowed_methods = parse_allow_header(allow_header)

        results["success"] = True
        results["message"] = "完成"
        results["data"] = {
            "status_code": response.status,
            "status_reason": response.reason,
            "allowed_methods": allowed_methods,
            "raw_allow_header": allow_header
        }

    except socket.timeout:
        results["message"] = "连接超时"
    except socket.error as e:
        results["message"] = f"网络错误: {e}"
    except HTTPException as e:
        results["message"] = f"HTTP错误: {e}"
    finally:
        if conn:
            conn.close()

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        h = sys.argv[1]
        p = int(sys.argv[2]) if len(sys.argv) > 2 else 80
        pt = sys.argv[3] if len(sys.argv) > 3 else "/"
    else:
        h, p, pt = "209.51.188.20", 80, "/"

    result = main(h, p, pt)
    print(json.dumps(result, ensure_ascii=False, indent=2))