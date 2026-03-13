"""skill/test_http_post_upload.py - Test if HTTP server allows file upload via POST method.

SKILL_META:
{
  "name": "test_http_post_upload",
  "description": "Test if HTTP server allows file upload via POST method.",
  "category": "http",
  "test_target": "209.51.188.20 HTTP server for POST upload vulnerability",
  "test_args": "209.51.188.20 80 /upload test.txt 'Test content'",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

def build_multipart_request(path: str, host: str, filename: str, content: str) -> str:
    """Build multipart/form-data POST request manually."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: text/plain\r\n\r\n"
            f"{content}\r\n"
            f"--{boundary}--\r\n")
    request = (f"POST {path} HTTP/1.1\r\n"
               f"Host: {host}\r\n"
               f"Content-Type: multipart/form-data; boundary={boundary}\r\n"
               f"Content-Length: {len(body)}\r\n"
               "Connection: close\r\n"
               "\r\n")
    return request + body

def send_http_request(host: str, port: int, request: str) -> str:
    """Send HTTP request via socket and return response."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10)
        sock.connect((host, port))
        sock.sendall(request.encode("utf-8"))
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
        return response.decode("utf-8", errors="replace")

def main(host: str = "209.51.188.20", port: int = 80, path: str = "/upload",
         test_file_name: str = "test.txt", test_content: str = "Test content") -> dict[str, Any]:
    """Test HTTP POST file upload capability."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        request = build_multipart_request(path, host, test_file_name, test_content)
        response = send_http_request(host, port, request)
        status_line = response.split("\r\n")[0]
        status_code = int(status_line.split()[1])
        results["data"]["status_line"] = status_line
        results["data"]["response_length"] = len(response)
        results["data"]["uploaded_file"] = test_file_name
        results["data"]["uploaded_content"] = test_content
        if 200 <= status_code < 300:
            results["success"] = True
            results["message"] = f"File upload successful (status {status_code})"
        else:
            results["message"] = f"Upload failed with status {status_code}"
    except ConnectionRefusedError as e:
        results["message"] = f"Connection refused: {e}"
    except socket.timeout as e:
        results["message"] = f"Connection timeout: {e}"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    except (IndexError, ValueError) as e:
        results["message"] = f"Response parsing error: {e}"
    return results

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 5:
        r = main(host=args[0], port=int(args[1]), path=args[2],
                 test_file_name=args[3], test_content=args[4])
    else:
        r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))