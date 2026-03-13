"""skill/check_http_methods.py - Send OPTIONS request to HTTP server and parse allowed methods.

SKILL_META:
{
  "name": "check_http_methods",
  "description": "Send OPTIONS request to HTTP server and parse allowed methods.",
  "category": "http",
  "test_target": "209.51.188.20 HTTP service",
  "test_args": "209.51.188.20 80 /",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
from http.client import HTTPConnection, HTTPException, IncompleteRead
from typing import Any
from urllib.parse import urlparse

def parse_allow_header(header_value: str | None) -> list[str]:
    """Parse HTTP Allow header value into list of methods."""
    if not header_value:
        return []
    return [method.strip().upper() for method in header_value.split(",") if method.strip()]

def handle_redirect(response, host: str, port: int) -> tuple[str, int, str] | None:
    """Handle redirect response and return new (host, port, path)."""
    if response.status not in (301, 302, 303, 307, 308):
        return None
    location = response.getheader("Location")
    if not location:
        return None
    if location.startswith("/"):
        return host, port, location
    if location.startswith("http"):
        parsed = urlparse(location)
        return (parsed.hostname or host), (parsed.port or 80), (parsed.path or "/")
    return None

def main(host: str, port: int = 80, path: str = "/", follow_redirects: bool = True) -> dict[str, Any]:
    """Send OPTIONS request to HTTP server and parse allowed methods."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    conn: HTTPConnection | None = None

    try:
        current_host, current_port, current_path = host, port, path
        redirect_count = 0
        max_redirects = 10
        redirect_chain: list[str] = []

        while redirect_count < max_redirects:
            conn = HTTPConnection(current_host, current_port, timeout=10)
            conn.request("OPTIONS", current_path)
            response = conn.getresponse()
            conn.close()
            conn = None

            if follow_redirects:
                redirect_info = handle_redirect(response, current_host, current_port)
                if redirect_info:
                    current_host, current_port, current_path = redirect_info
                    redirect_chain.append(f"{current_host}:{current_port}{current_path}")
                    redirect_count += 1
                    continue

            allow_header = response.getheader("Allow")
            cors_header = response.getheader("Access-Control-Allow-Methods")
            allowed_methods = parse_allow_header(allow_header)
            if not allowed_methods and cors_header:
                allowed_methods = parse_allow_header(cors_header)

            results["success"] = True
            results["message"] = "完成"
            results["data"] = {
                "status_code": response.status,
                "status_reason": response.reason,
                "allowed_methods": allowed_methods,
                "raw_allow_header": allow_header,
                "redirects_followed": redirect_count,
                "redirect_chain": redirect_chain if redirect_chain else None
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
    parser.add_argument("host", type=str, nargs="?", default="209.51.188.20",
                        help="HTTP server hostname or IP")
    parser.add_argument("port", type=int, nargs="?", default=80,
                        help="HTTP server port")
    parser.add_argument("path", type=str, nargs="?", default="/",
                        help="URL path to check")
    parser.add_argument("--host", dest="host_opt", type=str, default=None,
                        help="HTTP server hostname or IP (alternative)")
    parser.add_argument("--port", dest="port_opt", type=int, default=None,
                        help="HTTP server port (alternative)")
    parser.add_argument("--path", dest="path_opt", type=str, default=None,
                        help="URL path to check (alternative)")
    parser.add_argument("--follow-redirects", action="store_true", default=True,
                        help="Follow HTTP redirects (default: True)")
    parser.add_argument("--no-follow-redirects", dest="follow_redirects", action="store_false",
                        help="Do not follow HTTP redirects")

    args = parser.parse_args()

    host = args.host_opt if args.host_opt else args.host
    port = args.port_opt if args.port_opt else args.port
    path = args.path_opt if args.path_opt else args.path

    result = main(host, port, path, args.follow_redirects)
    print(json.dumps(result, ensure_ascii=False, indent=2))