"""skill/deploy_remote_http_post.py - Use HTTP POST to upload payload to remote server

SKILL_META:
{
  "name": "deploy_remote_http_post",
  "description": "Use HTTP POST to upload payload to remote server",
  "category": "deploy",
  "test_target": "209.51.188.20:80/pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub --payload_file test_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import argparse
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import mimetypes
import os

def main(host: str, port: int, path: str, payload_file: str) -> dict[str, Any]:
    """Upload payload to remote server via HTTP POST.

    Args:
        host: Target host address
        port: Target port number
        path: URL path for upload endpoint
        payload_file: Local file path to upload

    Returns:
        Dictionary with success status, message, and response data
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # Validate and read payload file
        if not os.path.exists(payload_file):
            raise FileNotFoundError(f"Payload file not found: {payload_file}")

        if not os.path.isfile(payload_file):
            raise ValueError(f"Not a regular file: {payload_file}")

        with open(payload_file, 'rb') as f:
            file_content = f.read()

        # Prepare multipart form data
        boundary = '----WebKitFormBoundary' + os.urandom(16).hex()
        filename = os.path.basename(payload_file)

        # Build multipart body
        body_parts = []
        body_parts.append(f'--{boundary}\r\n'.encode())
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        )

        # Try to guess content type
        content_type, _ = mimetypes.guess_type(payload_file)
        if content_type:
            body_parts.append(f'Content-Type: {content_type}\r\n'.encode())
        else:
            body_parts.append(b'Content-Type: application/octet-stream\r\n')

        body_parts.append(b'\r\n')
        body_parts.append(file_content)
        body_parts.append(b'\r\n')
        body_parts.append(f'--{boundary}--\r\n'.encode())

        body = b''.join(body_parts)

        # Build URL and request
        url = f"http://{host}:{port}{path}"
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'Mozilla/5.0 (compatible; Python-urllib)'
        }

        request = Request(url, data=body, headers=headers, method='POST')

        # Send request
        with urlopen(request, timeout=30) as response:
            response_data = response.read()
            status_code = response.getcode()

            results["data"] = {
                "status_code": status_code,
                "response": response_data.decode('utf-8', errors='ignore'),
                "headers": dict(response.headers),
                "url": url
            }

            # Consider 2xx status codes as success
            if 200 <= status_code < 300:
                results["success"] = True
                results["message"] = f"Upload successful (HTTP {status_code})"
            else:
                results["message"] = f"Upload failed with HTTP {status_code}"

    except FileNotFoundError as e:
        results["message"] = f"File error: {e}"
    except ValueError as e:
        results["message"] = f"Validation error: {e}"
    except HTTPError as e:
        results["message"] = f"HTTP error: {e.code} {e.reason}"
        results["data"] = {"status_code": e.code, "error": str(e)}
    except URLError as e:
        results["message"] = f"URL error: {e.reason}"
    except TimeoutError:
        results["message"] = "Request timed out"
    except OSError as e:
        results["message"] = f"OS error: {e}"
    except Exception as e:
        results["message"] = f"Unexpected error: {type(e).__name__}: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload payload via HTTP POST")
    parser.add_argument("--host", required=True, help="Target host address")
    parser.add_argument("--port", type=int, required=True, help="Target port number")
    parser.add_argument("--path", required=True, help="URL path for upload endpoint")
    parser.add_argument("--payload_file", required=True, help="Local file path to upload")

    # Parse command line arguments
    if len(sys.argv) == 1:
        # Use test arguments if none provided
        args = parser.parse_args([
            "--host", "209.51.188.20",
            "--port", "80",
            "--path", "/pub",
            "--payload_file", "test_payload.py"
        ])
    else:
        args = parser.parse_args()

    result = main(args.host, args.port, args.path, args.payload_file)
    print(json.dumps(result, ensure_ascii=False, indent=2))