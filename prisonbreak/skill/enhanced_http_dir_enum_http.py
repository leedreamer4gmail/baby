"""skill/enhanced_http_dir_enum_http.py - Enumerate potential HTTP directories with robust parameter handling and GET/HEAD requests.

SKILL_META:
{
  "name": "enhanced_http_dir_enum_http",
  "description": "Enumerate potential HTTP directories with robust parameter handling and GET/HEAD requests.",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "--host 209.51.188.20 --port 80 --paths /upload,/uploads,/files,/tmp,/pub,/admin,/api/upload.php,/upload.php,/fileupload,/webdav",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
import io
from typing import Any
import http.client
import socket

def parse_args(args: list[str] | None = None) -> dict[str, Any]:
    """Parse command line arguments robustly."""
    parser = argparse.ArgumentParser(description='HTTP Directory Enumeration')
    parser.add_argument('--host', type=str, default='209.51.188.20', help='Target host')
    parser.add_argument('--port', type=int, default=80, help='Target port (default: 80)')
    parser.add_argument('--paths', type=str, default='/upload,/uploads,/files,/tmp,/pub,/admin,/api/upload.php,/upload.php,/fileupload,/webdav', 
                        help='Comma-separated paths')
    try:
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            parsed = parser.parse_args(args)
        finally:
            sys.stderr = old_stderr
    except SystemExit:
        raise ValueError("Missing required arguments: --host and --paths")
    return {
        'host': parsed.host,
        'port': parsed.port,
        'paths': [p.strip() for p in parsed.paths.split(',') if p.strip()]
    }

def check_path(host: str, port: int, path: str) -> dict[str, Any]:
    """Check if a path exists using HEAD then GET fallback."""
    result: dict[str, Any] = {'path': path, 'status': 0, 'method': 'NONE'}
    try:
        conn = http.client.HTTPConnection(host, port, timeout=8)
        conn.request('HEAD', path)
        resp = conn.getresponse()
        result['status'] = resp.status
        result['method'] = 'HEAD'
        if resp.status == 405:
            conn.request('GET', path)
            resp = conn.getresponse()
            result['status'] = resp.status
            result['method'] = 'GET'
        result['exists'] = 200 <= resp.status < 400
        result['server'] = resp.getheader('Server', 'Unknown')
        result['content_length'] = resp.getheader('Content-Length', '0')
        conn.close()
    except (socket.timeout, ConnectionRefusedError, OSError) as e:
        result['error'] = str(e)
        result['exists'] = False
    except Exception as e:
        result['error'] = str(e)
        result['exists'] = False
    return result

def main(args: list[str] | None = None) -> dict[str, Any]:
    """Enumerate potential HTTP directories."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        if args is None:
            args = sys.argv[1:] if len(sys.argv) > 1 else []
        params = parse_args(args)
        host = params['host']
        port = params['port']
        paths = params['paths']

        found: list[dict[str, Any]] = []
        checked: list[dict[str, Any]] = []

        for path in paths:
            result = check_path(host, port, path)
            checked.append(result)
            if result.get('exists', False):
                found.append(result)

        results["success"] = True
        results["message"] = f"Scanned {len(paths)} paths, found {len(found)} accessible"
        results["data"] = {
            "target": f"{host}:{port}",
            "total_scanned": len(paths),
            "found": found,
            "all_checked": checked
        }
    except ValueError as e:
        results["message"] = f"Argument error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"
    return results

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))