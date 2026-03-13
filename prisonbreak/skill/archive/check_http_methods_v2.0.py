"""skill/check_http_methods.py - Send OPTIONS request to HTTP server and parse allowed methods.

SKILL_META:
{
  "name": "check_http_methods",
  "description": "Send OPTIONS request to HTTP server and parse allowed methods.",
  "category": "http",
  "test_target": "209.51.188.20 HTTP service",
  "test_args": "209.51.188.20 80 /",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
from http.client import HTTPConnection, HTTPException, IncompleteRead
from typing import Any

def parse_allow_header(header_value: str | None) -> list[str]:
    """Parse HTTP Allow header value into list of methods."""
    if not header_value:
        return []
    return [method.strip().upper() for method in header_value.split(",") if method.strip()]

def main(host: str, port: int = 80, path: str = "/", follow_redirects: bool = False) -> dict[str, Any]:
    """Send OPTIONS request to HTTP server and parse allowed methods."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    conn: HTTPConnection | None = None

    try:
        conn = HTTPConnection(host, port, timeout=10)

        current_path = path
        redirect_count = 0
        max_redirects = 5
        last_response = None

        while redirect_count < max_redirects:
            conn.request("OPTIONS", current_path)
            response = conn.getresponse()
            last_response = response

            if follow_redirects and response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location:
                    results["message"] = "重定向无Location头"
                    break

                if location.startswith("/"):
                    current_path = location
                elif location.startswith("http"):
                    from urllib.parse import urlparse
                    parsed = urlparse(location)
                    if parsed.hostname:
                        host = parsed.hostname
                        port = parsed.port or 80
                        conn = HTTPConnection(host, port, timeout=10)
                    current_path = parsed.path or "/"

                redirect_count += 1
                continue

            allow_header = response.getheader("Allow")
            allow_header_cors = response.getheader("Access-Control-Allow-Methods")

            allowed_methods = parse_allow_header(allow_header)
            if not allowed_methods and allow_header_cors:
                allowed_methods = parse_allow_header(allow_header_cors)

            results["success"] = True
            results["message"] = "完成"
            results["data"] = {
                "status_code": response.status,
                "status_reason": response.reason,
                "allowed_methods": allowed_methods,
                "raw_allow_header": allow_header,
                "redirects_followed": redirect_count
            }
            break
        else:
            results["message"] = f"超过最大重定向次数({max_redirects})"

    except ConnectionRefusedError:
        results["message"] = "连接被拒绝"
    except TimeoutError:
        results["message"] = "连接超时"
    except OSError as e:
        results["message"] = f"网络错误: {e}"
    except IncompleteRead:
        results["message"] = "响应读取不完整"
    except HTTPException as e:
        results["message"] = f"HTTP错误: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {e}"
    finally:
        if conn:
            conn.close()

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send OPTIONS request to HTTP server and parse allowed methods."
    )
    parser.add_argument(
        "--host", type=str, default="209.51.188.20",
        help="HTTP server hostname or IP (default: 209.51.188.20)"
    )
    parser.add_argument(
        "--port", type=int, default=80,
        help="HTTP server port (default: 80)"
    )
    parser.add_argument(
        "--path", type=str, default="/",
        help="URL path to check (default: /)"
    )
    parser.add_argument(
        "--follow-redirects", action="store_true",
        help="Follow HTTP redirects"
    )

    args = parser.parse_args()

    result = main(args.host, args.port, args.path, args.follow_redirects)
    print(json.dumps(result, ensure_ascii=False, indent=2))