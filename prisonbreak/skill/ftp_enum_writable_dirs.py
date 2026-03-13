"""skill/ftp_enum_writable_dirs.py - Enumerate writable directories on anonymous FTP server by attempting test uploads.

SKILL_META:
{
  "name": "ftp_enum_writable_dirs",
  "description": "Enumerate writable directories on anonymous FTP server by attempting test uploads.",
  "category": "ftp",
  "test_target": "209.51.188.20",
  "test_args": "209.51.188.20 ['/', '/pub', '/tmp', '/incoming', '/upload']",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
from typing import Any

from upload_ftp_anon_dir import main as upload_ftp_anon_dir_run

def main(host: str, dirs_to_test: list[str]) -> dict[str, Any]:
    """Enumerate writable directories by attempting test uploads."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    writable_dirs: list[str] = []
    failed_dirs: list[str] = []

    try:
        for directory in dirs_to_test:
            test_filename = f".writable_test_{hash(directory) % 10000}.tmp"
            upload_result = upload_ftp_anon_dir_run(host, directory, test_filename, b"test")
            if upload_result.get("success"):
                writable_dirs.append(directory)
            else:
                failed_dirs.append(directory)
                if upload_result.get("message"):
                    print(f"Failed {directory}: {upload_result['message']}", file=sys.stderr)

        results["success"] = True
        results["message"] = f"Tested {len(dirs_to_test)} directories"
        results["data"] = {
            "writable": writable_dirs,
            "not_writable": failed_dirs,
            "total_tested": len(dirs_to_test),
            "total_writable": len(writable_dirs)
        }
    except OSError as e:
        results["message"] = f"Network error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        dirs = sys.argv[2].replace("[", "").replace("]", "").replace("'", "").split(",")
        r = main(host, [d.strip() for d in dirs])
    else:
        r = main("209.51.188.20", ["/", "/pub", "/tmp", "/incoming", "/upload"])
    print(json.dumps(r, ensure_ascii=False, indent=2))