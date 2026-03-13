"""skill/deploy_remote_http_post.py - Use HTTP POST to upload payload to remote server

SKILL_META:
{
  "name": "deploy_remote_http_post",
  "description": "Use HTTP POST to upload payload to remote server",
  "category": "deploy",
  "test_target": "209.51.188.20:80/pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub --payload_file test_payload.py",
  "version": "2.0"
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

DEFAULT_PAYLOAD = b"print('Deployed')"

def main(host: str, port: int, path: str, payload_file: str = None, embedded_payload: bool = False) -> dict[str, Any]:
    """Upload payload to remote server via HTTP POST."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        if embedded_payload:
            file_content = DEFAULT_PAYLOAD
            filename = "embedded_payload.py"
        elif payload_file:
            if not os.path.exists(payload_file):
                raise FileNotFoundError(f"Payload file not found: {payload_file}")
            if not os.path.isfile(payload_file):
                raise ValueError(f"Not a regular file: {payload_file}")
            with open(payload_file, 'rb') as f:
                file_content = f.read()
            filename = os.path.basename(payload_file)
        else:
            raise ValueError("Either payload_file or embedded_payload must be specified")

        boundary = '----WebKitFormBoundary' + os.urandom(16).hex()
        body_parts = [
            f'--{boundary}\r\n'.encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        ]

        content_type, _ = mimetypes.guess_type(filename)
        if content_type:
            body_parts.append(f'Content-Type: {content_type}\r\n'.encode())
        else:
            body_parts.append(b'Content-Type: application/octet-stream\r\n')

        body_parts.extend([b'\r\n', file_content, b'\r\n', f'--{boundary}--\r\n'.encode()])
        body = b''.join(body_parts)

        url = f"http://{host}:{port}{path}"
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'User-Agent': 'Mozilla/5.0 (compatible; Python-urllib)'
        }

        request = Request(url, data=body, headers=headers, method='POST')

        with urlopen(request, timeout=30) as response:
            response_data = response.read()
            status_code = response.getcode()

            try:
                response_text = response_data.decode('utf-8')
            except UnicodeDecodeError:
                response_text = response_data.decode('latin-1', errors='ignore')

            results["data"] = {
                "status_code": status_code,
                "response": response_text,
                "headers": dict(response.headers),
                "url": url,
                "payload_source": "embedded" if embedded_payload else "file",
                "filename": filename
            }

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
        response_text = ""
        try:
            if hasattr(e, 'read'):
                response_text = e.read().decode('utf-8', errors='ignore')
        except:
            pass
        results["message"] = f"HTTP error: {e.code} {e.reason}"
        results["data"] = {"status_code": e.code, "error": str(e), "response": response_text}
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
    parser.add_argument("--payload_file", help="Local file path to upload")
    parser.add_argument("--embedded_payload", action="store_true", 
                       help="Use embedded payload instead of file")

    if len(sys.argv) == 1:
        args = parser.parse_args([
            "--host", "209.51.188.20",
            "--port", "80",
            "--path", "/pub",
            "--payload_file", "test_payload.py"
        ])
    else:
        args = parser.parse_args()

    if not args.payload_file and not args.embedded_payload:
        parser.error("Either --payload_file or --embedded_payload must be specified")

    result = main(args.host, args.port, args.path, args.payload_file, args.embedded_payload)
    print(json.dumps(result, ensure_ascii=False, indent=2))