"""skill/http_dir_enum_http.py - Enumerate potential HTTP directories by sending GET requests to common paths.

SKILL_META:
{
  "name": "http_dir_enum_http",
  "description": "Enumerate potential HTTP directories by sending GET requests to common paths.",
  "category": "http",
  "test_target": "209.51.188.20:80 to discover potential POST upload directories",
  "test_args": "209.51.188.20 80 ['/upload', '/uploads', '/fileupload', '/admin/upload', '/tmp']",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
from typing import Any

DEFAULT_PATHS: list[str] = [
    "/upload", "/uploads", "/fileupload",
    "/admin/upload", "/tmp", "/cgi-bin/",
    "/scripts", "/api", "/assets"
]

def main(host: str, port: int, paths: list[str] | None = None) -> dict[str, Any]:
    """Enumerate potential HTTP directories by sending GET requests to common paths."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    paths_to_check: list[str] = paths if paths else DEFAULT_PATHS
    found: list[dict[str, Any]] = []

    try:
        from fetch_http_content import main as fetch_http_content_run

        for path in paths_to_check:
            try:
                url: str = f"http://{host}:{port}{path}"
                resp: dict[str, Any] = fetch_http_content_run(url, "GET")

                if resp.get("success"):
                    status: int = resp.get("status_code", 0)
                    if status != 404:
                        found.append({
                            "path": path,
                            "url": url,
                            "status_code": status,
                            "content_length": resp.get("content_length", 0)
                        })
            except Exception:
                continue

        results["success"] = len(found) > 0
        results["message"] = f"Found {len(found)} accessible paths"
        results["data"] = {"found_paths": found, "total_checked": len(paths_to_check)}

    except ImportError as e:
        results["message"] = f"Import error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        h: str = sys.argv[1]
        p: int = int(sys.argv[2])
        pts: list[str] = sys.argv[3].split(",") if len(sys.argv) > 3 else None
        r = main(h, p, pts)
    else:
        r = main("209.51.188.20", 80)
    print(json.dumps(r, ensure_ascii=False, indent=2))