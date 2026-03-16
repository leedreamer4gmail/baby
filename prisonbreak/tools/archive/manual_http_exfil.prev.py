"""skill/manual_http_exfil.py - 使用http.client.HTTPConnection手动构建并发送非multipart POST请求，支持自定义headers、纯文本body或简单form字段，可指定超时，严格RFC合规且输出完整响应字典

SKILL_META:
{
  "name": "manual_http_exfil",
  "description": "使用http.client.HTTPConnection手动构建并发送非multipart POST请求，支持自定义headers、纯文本body或简单form字段，可指定超时，严格RFC合规且输出完整响应字典",
  "category": "HTTP",
  "test_target": "httpbin.org/post (预期status 200且body包含脚本内容片段)",
  "test_args": "--url http://httpbin.org/post --data_path skill/manual_http_exfil.py --field_name script --timeout 15",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from http.client import HTTPConnection, HTTPResponse
from typing import Any

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TOKEN_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~A-Za-z0-9]+$")

def parse_headers(headers_str: str | None) -> dict[str, str]:
    """解析JSON格式headers字符串为字典，验证header名合法性(RFC7230 token)"""
    if not headers_str:
        return {}
    try:
        parsed = json.loads(headers_str)
        if not isinstance(parsed, dict):
            return {}
        result: dict[str, str] = {}
        for key, val in parsed.items():
            if TOKEN_PATTERN.match(key):
                result[key] = str(val)
        return result
    except (json.JSONDecodeError, ValueError):
        result = {}
        for line in headers_str.split(","):
            line = line.strip()
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                if TOKEN_PATTERN.match(key):
                    result[key] = val.strip()
        return result

def build_form_body(data: str, field_name: str) -> str:
    """构建application/x-www-form-urlencoded格式body"""
    encoded = urllib.parse.quote(data, safe="")
    return f"{field_name}={encoded}"

def send_manual_post(
    host: str,
    port: int,
    path: str,
    body: str,
    headers: dict[str, str],
    timeout: float,
    debug: bool = False,
) -> tuple[int, dict[str, str], str]:
    """手动构建并发送POST请求"""
    if debug:
        print(f"[DEBUG] Connecting to {host}:{port}", file=sys.stderr)
    conn = HTTPConnection(host, port, timeout=timeout)
    if debug:
        conn.set_debuglevel(1)
    try:
        conn.request("POST", path, body=body, headers=headers)
        if debug:
            print(f"[DEBUG] Request sent to {path}", file=sys.stderr)
        response: HTTPResponse = conn.getresponse()
        status = response.status
        resp_headers = dict(response.getheaders())
        resp_body = response.read().decode("utf-8", errors="replace")
        if debug:
            print(f"[DEBUG] Response status: {status}", file=sys.stderr)
        return status, resp_headers, resp_body
    finally:
        conn.close()

def main(
    url: str = "http://httpbin.org/post",
    data_path: str = "",
    field_name: str = "script",
    timeout: float = 45.0,
    headers: str = "",
    debug: bool = False,
) -> dict[str, Any]:
    """手动HTTP POST文件传输工具"""
    result: dict[str, Any] = {
        "success": False,
        "status_code": 0,
        "headers": {},
        "body": "",
        "used_manual_post": True,
    }
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        if debug:
            print(f"[DEBUG] Target: {host}:{port}{path}", file=sys.stderr)

        if data_path:
            try:
                with open(data_path, "r", encoding="utf-8") as f:
                    data_content = f.read()
            except FileNotFoundError:
                result["message"] = f"文件未找到: {data_path}"
                return result
            except IOError as e:
                result["message"] = f"读取文件错误: {e}"
                return result
        else:
            data_content = ""

        custom_headers = parse_headers(headers)
        body = build_form_body(data_content, field_name)

        if debug:
            payload_size = len(body)
            boundary = "non-multipart" if "multipart/form-data" not in body else "N/A"
            print(f"[DEBUG] Payload size: {payload_size} bytes", file=sys.stderr)
            print(f"[DEBUG] Boundary: {boundary}", file=sys.stderr)

        req_headers: dict[str, str] = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(body)),
            "User-Agent": DEFAULT_UA,
        }
        req_headers.update(custom_headers)

        if debug:
            print(f"[DEBUG] Headers: {req_headers}", file=sys.stderr)
            print(f"[DEBUG] Body length: {len(body)}", file=sys.stderr)

        status, resp_headers, resp_body = send_manual_post(
            host, port, path, body, req_headers, timeout, debug
        )

        result["status_code"] = status
        result["headers"] = resp_headers
        result["body"] = resp_body
        result["success"] = True
        result["message"] = "请求成功"

    except ConnectionError as e:
        result["message"] = f"连接错误: {e}"
    except TimeoutError as e:
        result["message"] = f"超时错误: {e}"
    except Exception as e:
        result["message"] = f"错误: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="手动HTTP POST文件传输工具")
    parser.add_argument("--url", default="http://httpbin.org/post", help="目标URL")
    parser.add_argument("--data_path", default="", help="要传输的文件路径")
    parser.add_argument("--field_name", default="script", help="表单字段名")
    parser.add_argument("--timeout", type=float, default=45.0, help="超时秒数")
    parser.add_argument("--headers", default="", help="自定义Headers，JSON格式")
    parser.add_argument("--debug", action="store_true", help="启用调试输出")
    args = parser.parse_args()
    result = main(
        url=args.url,
        data_path=args.data_path,
        field_name=args.field_name,
        timeout=args.timeout,
        headers=args.headers,
        debug=args.debug,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))