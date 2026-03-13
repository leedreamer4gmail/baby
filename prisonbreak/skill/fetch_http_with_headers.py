"""skill/fetch_http_with_headers.py - Fetch HTTP content with custom headers to bypass detections like Cloudflare.

SKILL_META:
{
  "name": "fetch_http_with_headers",
  "description": "Fetch HTTP content with custom headers to bypass detections like Cloudflare.",
  "category": "http",
  "test_target": "Cloudflare-protected HTTP server at 104.18.27.120:80",
  "test_args": "104.18.27.120 80 / '{\"User-Agent\": \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\"}'",
  "version": "1.0"
}
"""
from __future__ import annotations

import http.client
import json
import sys
from typing import Any

def main(host: str, port: int, path: str, headers: str) -> dict[str, Any]:
    """Fetch HTTP content with custom headers.

    Args:
        host: Target hostname or IP address
        port: Target port number
        path: Request path (e.g., /api/endpoint)
        headers: JSON string of custom headers

    Returns:
        dict with status, content, error, and success keys
    """
    result: dict[str, Any] = {"status": 0, "content": "", "error": "", "success": False}

    try:
        # Parse headers JSON string
        try:
            headers_dict: dict[str, str] = json.loads(headers)
        except json.JSONDecodeError as e:
            result["error"] = f"Invalid headers JSON: {e}"
            return result

        # Validate headers is a dict
        if not isinstance(headers_dict, dict):
            result["error"] = "Headers must be a JSON object (dict)"
            return result

        # Ensure path starts with /
        if not path.startswith("/"):
            path = "/" + path

        # Create connection and request
        conn = http.client.HTTPConnection(host, port, timeout=30)

        try:
            conn.request("GET", path, headers=headers_dict)
            response = conn.getresponse()

            result["status"] = response.status
            result["content"] = response.read().decode("utf-8", errors="replace")
            result["success"] = True
        finally:
            conn.close()

    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
    except Exception as e:
        result["error"] = f"Request failed: {e}"

    return result

if __name__ == "__main__":
    # Default test parameters for structure validation
    default_host = "104.18.27.120"
    default_port = 80
    default_path = "/"
    default_headers = '{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}'

    if len(sys.argv) >= 5:
        arg_host = sys.argv[1]
        arg_port = int(sys.argv[2])
        arg_path = sys.argv[3]
        arg_headers = sys.argv[4]
    else:
        # Use default test parameters
        arg_host = default_host
        arg_port = default_port
        arg_path = default_path
        arg_headers = default_headers

    result = main(arg_host, arg_port, arg_path, arg_headers)
    print(json.dumps(result, ensure_ascii=False, indent=2))