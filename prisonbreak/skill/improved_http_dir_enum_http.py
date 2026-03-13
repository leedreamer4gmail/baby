"""skill/improved_http_dir_enum_http.py - Improved enumeration of HTTP directories with bug fixes and expanded path support via GET requests.

SKILL_META:
{
  "name": "improved_http_dir_enum_http",
  "description": "Improved enumeration of HTTP directories with bug fixes and expanded path support via GET requests.",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "209.51.188.20 80 ['/upload', '/uploads', '/fileupload', '/admin/upload', '/tmp', '/files', '/pub', '/incoming', '/webdav', '/api/upload']",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any

try:
    from fetch_http_content import main as fetch_http_content_run
except ImportError:
    fetch_http_content_run = None

def check_path(host: str, port: int, path: str) -> dict[str, Any]:
    """Check a single path on the target host."""
    url = f"http://{host}:{port}{path}"
    try:
        result = fetch_http_content_run(host, port, path)
        if result.get("success"):
            data = result.get("data", {})
            status = data.get("status_code", 0) if isinstance(data, dict) else 0
            return {"path": path, "status": status, "found": status in [200, 201, 204, 301, 302, 303, 307, 308]}
        return {"path": path, "status": 0, "found": False}
    except Exception:
        return {"path": path, "status": 0, "found": False}

def main(host: str, port: int, paths: list[str]) -> dict[str, Any]:
    """Enumerate HTTP directories on target host."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {"found_paths": []}}

    if not host or not isinstance(port, int) or not paths:
        results["message"] = "Invalid parameters"
        return results

    if fetch_http_content_run is None:
        results["message"] = "fetch_http_content tool not available"
        return results

    try:
        found_paths: list[dict[str, Any]] = []

        for path in paths:
            if not path.startswith("/"):
                path = "/" + path

            result = check_path(host, port, path)

            if result.get("found"):
                found_paths.append({"path": result["path"], "status": result["status"]})

            time.sleep(0.1)

        results["success"] = True
        results["message"] = f"Scanned {len(paths)} paths, found {len(found_paths)} accessible"
        results["data"]["found_paths"] = found_paths

    except ConnectionError as e:
        results["message"] = f"Connection error: {e}"
    except TimeoutError as e:
        results["message"] = f"Timeout error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        target_host = sys.argv[1]
        target_port = int(sys.argv[2])
        try:
            target_paths = json.loads(sys.argv[3])
        except json.JSONDecodeError:
            target_paths = sys.argv[3].strip("[]").replace("'", "").replace(" ", "").split(",")
    else:
        target_host = "209.51.188.20"
        target_port = 80
        target_paths = ["/upload", "/uploads", "/fileupload", "/admin/upload", "/tmp", "/files", "/pub", "/incoming", "/webdav", "/api/upload"]

    result = main(target_host, target_port, target_paths)
    print(json.dumps(result, ensure_ascii=False, indent=2))