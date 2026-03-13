"""skill/test_http_post_upload_http.py - Test if HTTP server allows file upload via POST with multipart/form-data and attempt to upload a test file.

SKILL_META:
{
  "name": "test_http_post_upload_http",
  "description": "Test if HTTP server allows file upload via POST with multipart/form-data and attempt to upload a test file.",
  "category": "http",
  "test_target": "209.51.188.20:80 potential upload path",
  "test_args": "209.51.188.20 80 /upload test.txt b'test content'",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

def build_multipart_request(boundary: str, filename: str, file_content: bytes) -> bytes:
    """Build multipart/form-data request body."""
    body = b"--" + boundary.encode() + b"\r\n"
    body += b'Content-Disposition: form-data; name="file"; filename="' + filename.encode() + b'"\r\n'
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += file_content + b"\r\n"
    body += b"--" + boundary.encode() + b"--\r\n"
    return body

def send_upload_request(
    host: str, port: int, path: str, filename: str, content: bytes
) -> tuple[int, str]:
    """Send HTTP POST request for file upload."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = build_multipart_request(boundary, filename, content)

    request = f"POST {path} HTTP/1.1\r\n"
    request += f"Host: {host}:{port}\r\n"
    request += "Content-Type: multipart/form-data; boundary=" + boundary + "\r\n"
    request += f"Content-Length: {len(body)}\r\n"
    request += "Connection: close\r\n\r\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((host, port))
        sock.sendall(request.encode() + body)
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
    finally:
        sock.close()

    response_str = response.decode("utf-8", errors="replace")
    status_line = response_str.split("\r\n")[0]
    parts = status_line.split(" ")
    status_code = int(parts[1]) if len(parts) > 1 else 0
    return status_code, response_str

def main(
    host: str = "209.51.188.20",
    port: int = 80,
    path: str = "/upload",
    filename: str = "test.txt",
    content: bytes = b"test content"
) -> dict[str, Any]:
    """Test HTTP file upload endpoint."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        status_code, response = send_upload_request(host, port, path, filename, content)
        results["data"]["status_code"] = status_code
        results["data"]["response_length"] = len(response)

        if status_code in (200, 201):
            results["success"] = True
            results["message"] = "File upload successful"
        elif status_code == 405:
            results["message"] = "Method not allowed"
        elif status_code == 404:
            results["message"] = "Upload endpoint not found"
        else:
            results["message"] = f"Server returned status {status_code}"
    except ConnectionRefusedError as e:
        results["message"] = f"Connection refused: {e}"
    except socket.timeout:
        results["message"] = "Connection timed out"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    return results

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 5:
        host, port, path, filename, content = args[0], int(args[1]), args[2], args[3], args[4].encode()
        result = main(host, port, path, filename, content)
    else:
        result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))