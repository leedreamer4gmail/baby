"""skill/api_explorer.py - 一个简单的HTTP请求工具，使用Python标准库向指定URL发送GET/POST请求，返回响应状态码、头部和完整内容

SKILL_META:
{
  "name": "api_explorer",
  "description": "一个简单的HTTP请求工具，使用Python标准库向指定URL发送GET/POST请求，返回响应状态码、头部和完整内容（默认截断部分内容），以探索公共API或服务的可用性",
  "category": "网络侦察",
  "test_target": "知名公共API目录服务，预期返回200状态码和JSON响应，确认工具能正确获取远程信息",
  "test_args": "--url https://api.publicapis.org/entries --timeout 5",
  "version": "8.0"
}
"""
from __future__ import annotations

import argparse
import json
import ssl
import os
import http.client
from typing import Any
from urllib.parse import urlparse

def parse_headers(headers_str: str) -> dict[str, str]:
    """解析头部字符串为字典"""
    headers = {}
    if not headers_str:
        return headers
    for part in headers_str.replace(',', '\n').split('\n'):
        part = part.strip()
        if part and ':' in part:
            key, value = part.split(':', 1)
            headers[key.strip()] = value.strip()
    return headers

def main(url: str, timeout: int = 5, method: str = "GET", data: str = None, file: str = None, headers: str = None, full_body: bool = False) -> dict[str, Any]:
    """发送HTTP GET/POST请求并返回响应信息"""
    result: dict[str, Any] = {"success": False, "status_code": None, "request_headers": {}, "response_headers": {}, "content_snippet": "", "full_content": "", "error": None}

    try:
        parsed = urlparse(url)
        host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        is_https = parsed.scheme == "https"
        conn_class = http.client.HTTPSConnection if is_https else http.client.HTTPConnection
        conn = conn_class(host, port, timeout=timeout, context=ctx)

        req_headers = parse_headers(headers)
        result["request_headers"] = req_headers

        body = None
        if file and os.path.isfile(file):
            boundary = b"----WebKitFormBoundary" + os.urandom(16).hex()
            body = b""
            if data:
                body += b"--" + boundary + b"\r\n"
                body += b'Content-Disposition: form-data; name="data"\r\n\r\n'
                body += data.encode("utf-8") + b"\r\n"
            filename = os.path.basename(file).encode()
            with open(file, "rb") as f:
                file_content = f.read()
            body += b"--" + boundary + b"\r\n"
            body += b'Content-Disposition: form-data; name="file"; filename="' + filename + b'"\r\n'
            body += b"Content-Type: application/octet-stream\r\n\r\n"
            body += file_content + b"\r\n"
            body += b"--" + boundary + b"--\r\n"
            req_headers["Content-Type"] = f"multipart/form-data; boundary={boundary.decode()}"
        elif data:
            try:
                parsed_data = json.loads(data)
                body = json.dumps(parsed_data, ensure_ascii=False).encode("utf-8")
                req_headers["Content-Type"] = "application/json; charset=utf-8"
            except json.JSONDecodeError:
                body = data.encode("utf-8")
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        conn.request(method.upper(), path, body=body, headers=req_headers)
        response = conn.getresponse()

        max_redirects = 5
        while response.status >= 300 and response.status < 400 and max_redirects > 0:
            location = response.getheader("Location")
            if not location:
                break
            conn.close()
            parsed = urlparse(location)
            host, port = parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            conn_class = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
            conn = conn_class(host, port, timeout=timeout, context=ctx)
            conn.request(method.upper(), path, body=body, headers=req_headers)
            response = conn.getresponse()
            max_redirects -= 1

        result["status_code"] = response.status
        result["response_headers"] = dict(response.getheaders())
        content = response.read()
        result["full_content"] = content.decode("utf-8", errors="replace")
        result["content_snippet"] = result["full_content"] if full_body else result["full_content"][:100]
        result["success"] = True
        conn.close()
    except ssl.SSLError as e:
        result["error"] = f"SSLError: {e}"
    except http.client.HTTPException as e:
        result["error"] = f"HTTPException: {e}"
    except OSError as e:
        result["error"] = f"OSError: {e}"
    except Exception as e:
        result["error"] = f"Error: {type(e).__name__}: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP API 探索工具")
    parser.add_argument("--url", default="http://httpbin.org/get", help="目标URL")
    parser.add_argument("--timeout", type=int, default=5, help="请求超时秒数")
    parser.add_argument("--method", default="GET", help="HTTP方法 (GET/POST)")
    parser.add_argument("--data", default=None, help="请求数据 (JSON或表单数据)")
    parser.add_argument("--file", default=None, help="上传文件路径 (multipart/form-data)")
    parser.add_argument("--headers", default=None, help="自定义请求头 (格式: 'Key:Value'，可逗号或换行分隔)")
    parser.add_argument("--full_body", action="store_true", help="返回完整内容片段（默认仅返回前100字符）")
    args = parser.parse_args()
    result = main(args.url, args.timeout, args.method, args.data, args.file, args.headers, args.full_body)
    print(json.dumps(result, ensure_ascii=False, indent=2))