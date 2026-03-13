"""skill/enum_http_post_upload_http.py - Enumerate common HTTP upload endpoints and attempt POST file upload with multipart/form-data.

SKILL_META:
{
  "name": "enum_http_post_upload_http",
  "description": "Enumerate common HTTP upload endpoints and attempt POST file upload with multipart/form-data.",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "209.51.188.20 80 ['/upload.php', '/uploads/', '/fileupload/', '/admin/upload.php', '/tmp/upload'] 'test.txt' b'test content'",
  "version": "1.0"
}
"""
from __future__ import annotations

import http.client
import json
import sys
from typing import Any

def build_multipart(file_name: str, file_content: bytes) -> tuple[bytes, str]:
    boundary = "----WebKitFormBoundary" + "".join(["a" for _ in range(16)])
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += file_content
    body += f"\r\n--{boundary}--\r\n".encode()
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type

def try_upload(host: str, port: int, path: str, file_name: str, file_content: bytes) -> dict[str, Any]:
    result: dict[str, Any] = {"path": path, "status": 0, "success": False, "response": ""}
    try:
        body, content_type = build_multipart(file_name, file_content)
        conn = http.client.HTTPConnection(host, port, timeout=10)
        conn.request("POST", path, body, {"Content-Type": content_type})
        resp = conn.getresponse()
        result["status"] = resp.status
        result["response"] = resp.read(1024).decode("utf-8", errors="ignore")
        result["success"] = 200 <= resp.status < 300
        conn.close()
    except ConnectionRefusedError:
        result["response"] = "Connection refused"
    except TimeoutError:
        result["response"] = "Connection timeout"
    except Exception as e:
        result["response"] = f"Error: {type(e).__name__}: {e}"
    return result

def main(host: str, port: int, paths: list[str], file_name: str, file_content: bytes) -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        results["data"]["host"] = host
        results["data"]["port"] = port
        results["data"]["file_name"] = file_name
        results["data"]["attempts"] = []
        for path in paths:
            attempt = try_upload(host, port, path, file_name, file_content)
            results["data"]["attempts"].append(attempt)
        results["success"] = True
        results["message"] = f"Completed {len(paths)} upload attempts"
    except Exception as e:
        results["message"] = f"Error: {type(e).__name__}: {e}"
    return results

if __name__ == "__main__":
    if len(sys.argv) >= 6:
        target_host = sys.argv[1]
        target_port = int(sys.argv[2])
        paths = json.loads(sys.argv[3])
        filename = sys.argv[4]
        content = sys.argv[5].encode()
        result = main(target_host, target_port, paths, filename, content)
    else:
        result = main(
            "209.51.188.20",
            80,
            ["/upload.php", "/uploads/", "/fileupload/", "/admin/upload.php", "/tmp/upload"],
            "test.txt",
            b"test content"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))