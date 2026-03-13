"""skill/test_http_webdav.py - Test if HTTP server supports WebDAV and attempt to upload a test file.

SKILL_META:
{
  "name": "test_http_webdav",
  "description": "Test if HTTP server supports WebDAV and attempt to upload a test file.",
  "category": "http",
  "test_target": "Cloudflare IP 104.18.26.120:80",
  "test_args": "104.18.26.120 80 baby_test.txt 'hello from baby'",
  "version": "1.0"
}
"""
from __future__ import annotations

import http.client
import json
import sys
from typing import Any

def check_webdav_support(host: str, port: int) -> tuple[bool, str]:
    """Check if server supports WebDAV using PROPFIND method."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request("PROPFIND", "/", headers={
            "Depth": "0",
            "Content-Type": "application/xml"
        })
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8", errors="ignore")
        conn.close()

        supported = status in (207, 405)
        return supported, f"PROPFIND status: {status}, body: {body[:200]}"
    except ConnectionRefusedError as e:
        return False, f"Connection refused: {e}"
    except TimeoutError as e:
        return False, f"Connection timeout: {e}"
    except OSError as e:
        return False, f"OS error: {e}"

def attempt_upload(host: str, port: int, test_file: str, content: str) -> tuple[bool, str]:
    """Attempt to upload a test file via PUT method."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        path = f"/{test_file}"
        conn.request("PUT", path, body=content, headers={
            "Content-Type": "text/plain"
        })
        response = conn.getresponse()
        status = response.status
        body = response.read().decode("utf-8", errors="ignore")
        conn.close()

        uploaded = status in (201, 204)
        return uploaded, f"PUT status: {status}, body: {body[:200]}"
    except ConnectionRefusedError as e:
        return False, f"Connection refused: {e}"
    except TimeoutError as e:
        return False, f"Connection timeout: {e}"
    except OSError as e:
        return False, f"OS error: {e}"

def main(
    host: str,
    port: int = 80,
    test_file: str = "baby_test.txt",
    content: str = "hello from baby"
) -> dict[str, Any]:
    """Test WebDAV support and upload capability on HTTP server."""
    results: dict[str, Any] = {
        "success": False,
        "supported": False,
        "uploaded": False,
        "response": "",
        "error": None,
        "message": "",
        "data": {}
    }

    try:
        supported, resp1 = check_webdav_support(host, port)
        results["response"] = resp1

        if supported:
            uploaded, resp2 = attempt_upload(host, port, test_file, content)
            results["response"] += " | " + resp2
            results["supported"] = supported
            results["uploaded"] = uploaded
        else:
            uploaded, resp2 = attempt_upload(host, port, test_file, content)
            results["response"] += " | " + resp2
            if uploaded:
                results["supported"] = True
                results["uploaded"] = True

        results["success"] = results["supported"] and results["uploaded"]
        results["message"] = "完成" if results["success"] else "WebDAV not supported or upload failed"
        results["data"] = {
            "host": host,
            "port": port,
            "test_file": test_file
        }
    except Exception as e:
        results["error"] = str(e)
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        h = sys.argv[1]
        p = int(sys.argv[2]) if len(sys.argv) > 2 else 80
        f = sys.argv[3] if len(sys.argv) > 3 else "baby_test.txt"
        c = sys.argv[4] if len(sys.argv) > 4 else "hello from baby"
        result = main(h, p, f, c)
    else:
        result = main("104.18.26.120")

    print(json.dumps(result, ensure_ascii=False, indent=2))