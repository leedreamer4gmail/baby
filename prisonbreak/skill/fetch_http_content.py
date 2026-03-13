"""skill/fetch_http_content.py - Fetch content from a remote HTTP server using basic GET request.

SKILL_META:
{
  "name": "fetch_http_content",
  "description": "Fetch content from a remote HTTP server using basic GET request with redirect support.",
  "category": "http",
  "test_target": "example.com host to fetch homepage content",
  "test_args": "--host example.com --port 80 --path /",
  "version": "4.0"
}
"""
from __future__ import annotations

import argparse
import http.client
import json
import sys
from typing import Any
from urllib.parse import urlparse

REDIRECT_CODES = (301, 302, 303, 307, 308)
MAX_REDIRECTS = 3

def main(host: str, port: int, path: str) -> dict[str, Any]:
    """Fetch content from a remote HTTP server using basic GET request with redirect support."""
    result: dict[str, Any] = {
        "success": False,
        "content": "",
        "headers": {},
        "error": "",
        "redirects": []
    }

    current_host = host
    current_port = port
    current_path = path
    redirect_count = 0
    last_response = None

    try:
        while redirect_count <= MAX_REDIRECTS:
            conn = http.client.HTTPConnection(current_host, current_port, timeout=10)
            try:
                if not current_path.startswith("/"):
                    current_path = "/" + current_path

                conn.request("GET", current_path)
                response = conn.getresponse()
                last_response = response

                # Check for redirect
                if redirect_count < MAX_REDIRECTS and response.status in REDIRECT_CODES:
                    location = response.getheader("Location")
                    if location:
                        result["redirects"].append({
                            "from": f"http://{current_host}:{current_port}{current_path}",
                            "to": location,
                            "status": response.status
                        })
                        # Parse new location
                        parsed = urlparse(location)
                        if parsed.netloc:
                            # New host:port
                            if ":" in parsed.netloc:
                                current_host, port_str = parsed.netloc.split(":")
                                current_port = int(port_str)
                            else:
                                current_host = parsed.netloc
                                current_port = 80
                            current_path = parsed.path or "/"
                            if parsed.query:
                                current_path += "?" + parsed.query
                        else:
                            # Relative path
                            current_path = parsed.path or "/"
                            if parsed.query:
                                current_path += "?" + parsed.query
                        redirect_count += 1
                        continue

                # Not a redirect or max redirects reached
                result["headers"] = dict(response.getheaders())
                result["content"] = response.read().decode("utf-8", errors="replace")
                result["status_code"] = response.status
                result["success"] = True
                break
            finally:
                conn.close()

        if not result["success"] and redirect_count >= MAX_REDIRECTS:
            result["error"] = f"Too many redirects (>{MAX_REDIRECTS})"

    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
    except OSError as e:
        result["error"] = f"Network error: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch content from a remote HTTP server")
    parser.add_argument("--host", default="example.com", help="Remote host")
    parser.add_argument("--port", type=int, default=80, help="Remote port")
    parser.add_argument("--path", default="/", help="Request path")
    args = parser.parse_args()

    result = main(args.host, args.port, args.path)
    print(json.dumps(result, ensure_ascii=False, indent=2))