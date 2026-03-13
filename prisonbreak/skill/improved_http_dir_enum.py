"""skill/improved_http_dir_enum.py - Enumerate potential HTTP directories by sending GET/HEAD requests to common paths with improved parameter handling.

SKILL_META:
{
  "name": "improved_http_dir_enum",
  "description": "Enumerate potential HTTP directories by sending GET/HEAD requests to common paths with improved parameter handling.",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "--host 209.51.188.20 --port 80 --paths /upload,/uploads,/files,/tmp,/pub,/admin,/api/upload.php,/upload.php,/fileupload,/webdav",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
from http.client import HTTPConnection, HTTPSConnection
from typing import Any

def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Enumerate HTTP directories")
    parser.add_argument("--host", type=str, help="Target host")
    parser.add_argument("--port", type=int, help="Target port")
    parser.add_argument("--paths", type=str, help="Comma-separated paths to check")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    return parser.parse_args(args)

def check_path(host: str, port: int, path: str, timeout: int = 5) -> dict[str, Any]:
    """Check a single path on the HTTP server."""
    result: dict[str, Any] = {"path": path, "status": None, "found": False, "error": None}
    try:
        if port == 443 or port == 8443:
            context = ssl.create_default_context()
            conn = HTTPSConnection(host, port=port, timeout=timeout, context=context)
        else:
            conn = HTTPConnection(host, port=port, timeout=timeout)

        conn.request("HEAD", path, headers={"Host": host})
        response = conn.getresponse()
        result["status"] = response.status
        result["found"] = response.status in [200, 301, 302, 303, 307, 308, 401, 403]
        if result["found"]:
            result["location"] = response.getheader("Location", "")
        conn.close()
    except socket.timeout:
        result["error"] = "timeout"
    except ConnectionRefusedError:
        result["error"] = "connection_refused"
    except Exception as e:
        result["error"] = str(e)
    return result

def main() -> dict[str, Any]:
    """Main function for HTTP directory enumeration."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # 使用 sys.argv 作为参数源
        argv = sys.argv[1:] if len(sys.argv) > 1 else []
        parsed = parse_args(argv)

        # 验证必要参数
        if not parsed.host or not parsed.port or not parsed.paths:
            results["message"] = "错误: 缺少必要参数，请提供 --host, --port, --paths"
            return results

        host = parsed.host
        port = parsed.port
        paths = [p.strip() for p in parsed.paths.split(",") if p.strip()]
        timeout = parsed.timeout

        results["data"]["host"] = host
        results["data"]["port"] = port
        results["data"]["paths_checked"] = len(paths)
        results["data"]["found"] = []

        for path in paths:
            if not path.startswith("/"):
                path = "/" + path
            check_result = check_path(host, port, path, timeout)
            if check_result["found"]:
                results["data"]["found"].append(check_result)

        results["success"] = True
        results["message"] = f"扫描完成，发现 {len(results['data']['found'])} 个可能存在的路径"

    except SystemExit as e:
        results["message"] = f"参数解析错误: {e.code}"
    except ValueError as e:
        results["message"] = f"参数值错误: {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))