"""skill/test_http_put_fixed_http.py - Test if HTTP server allows PUT method and attempt to upload a test file with fixed parameter handling.

SKILL_META:
{
  "name": "test_http_put_fixed_http",
  "description": "Test if HTTP server allows PUT method and attempt to upload a test file with fixed parameter handling.",
  "category": "http",
  "test_target": "209.51.188.20:80 /pub/",
  "test_args": "209.51.188.20 80 /pub/ 'test data' test.txt",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import http.client
import urllib.parse
from typing import Any

def check_put_method(host: str, port: int, path: str = "/") -> bool:
    """Check if HTTP server allows PUT method at given path."""
    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request("OPTIONS", path)
        response = conn.getresponse()
        allow_header = response.getheader("Allow", "")
        if allow_header and "PUT" in allow_header.upper():
            conn.close()
            return True
        conn.close()
        # Direct PUT test
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request("PUT", path, body="")
        response = conn.getresponse()
        conn.close()
        # 405 Method Not Allowed means PUT is explicitly disallowed
        return response.status != 405
    except Exception:
        return False

def upload_file(host: str, port: int, path: str, content: str, filename: str) -> dict[str, Any]:
    """Attempt to upload a file using PUT method."""
    result: dict[str, Any] = {"status_code": 0, "success": False, "message": "", "headers": {}}
    try:
        full_path = f"{path.rstrip('/')}/{filename}"
        conn = http.client.HTTPConnection(host, port, timeout=15)
        headers = {"Content-Type": "application/octet-stream", "Content-Length": str(len(content))}
        conn.request("PUT", full_path, body=content)
        response = conn.getresponse()
        result["status_code"] = response.status
        result["headers"] = dict(response.getheaders())
        result["message"] = f"Response: {response.status} {response.reason}"
        if 200 <= response.status < 400:
            result["success"] = True
        elif response.status in (301, 302, 307, 308):
            location = response.getheader("Location")
            if location:
                result["message"] += f", Redirect to: {location}"
                parsed = urllib.parse.urlparse(location)
                new_path = parsed.path or path
                # Follow redirect
                result = upload_file(host, port, new_path, content, filename)
        conn.close()
    except http.client.HTTPException as e:
        result["message"] = f"HTTP Error: {e}"
    except ConnectionRefusedError:
        result["message"] = "Connection refused"
    except TimeoutError:
        result["message"] = "Connection timeout"
    except Exception as e:
        result["message"] = f"Error: {type(e).__name__}: {e}"
    return result

def main(params: dict[str, Any] | list[str] | None = None) -> dict[str, Any]:
    """Test HTTP PUT method and upload capability."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    host: str = ""
    port: int = 80
    path: str = "/pub/"
    content: str = "test data"
    filename: str = "test.txt"

    # Parse parameters
    if params is None:
        params = sys.argv[1:]

    if isinstance(params, list):
        if len(params) >= 1:
            host = str(params[0])
        if len(params) >= 2:
            try:
                port = int(params[1])
            except (ValueError, TypeError):
                port = 80
        if len(params) >= 3:
            path = str(params[2])
        if len(params) >= 4:
            content = str(params[3])
        if len(params) >= 5:
            filename = str(params[4])
    elif isinstance(params, dict):
        host = str(params.get("host", ""))
        try:
            port = int(params.get("port", 80))
        except (ValueError, TypeError):
            port = 80
        path = str(params.get("path", "/pub/"))
        content = str(params.get("content", "test data"))
        filename = str(params.get("filename", "test.txt"))

    if not host:
        results["message"] = "Missing required parameter: host"
        return results

    try:
        # Check PUT on the target path
        put_allowed = check_put_method(host, port, path)
        results["data"]["put_method_allowed"] = put_allowed

        # Even if OPTIONS doesn't show PUT, try upload (some servers don't advertise)
        if not put_allowed:
            # Try a quick PUT test with minimal body
            conn = http.client.HTTPConnection(host, port, timeout=10)
            test_path = f"{path.rstrip('/')}/.put_test"
            conn.request("PUT", test_path, body="x")
            response = conn.getresponse()
            conn.close()
            if response.status != 405:
                put_allowed = True

        results["data"]["put_method_allowed"] = put_allowed

        if not put_allowed:
            results["message"] = "PUT method not allowed on server"
            return results

        upload_result = upload_file(host, port, path, content, filename)
        results["data"]["upload"] = upload_result
        results["success"] = upload_result["success"]
        results["message"] = upload_result["message"]
    except ValueError as e:
        results["message"] = f"Parameter conversion error: {e}"
    except ConnectionRefusedError:
        results["message"] = f"Cannot connect to {host}:{port}"
    except TimeoutError:
        results["message"] = f"Connection to {host}:{port} timed out"
    except Exception as e:
        results["message"] = f"Error: {type(e).__name__}: {e}"
    return results

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))