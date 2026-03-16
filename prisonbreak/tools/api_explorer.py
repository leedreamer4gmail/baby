"""skill/api_explorer.py - 一个简单的HTTP请求工具，使用Python标准库向指定URL发送GET/POST请求，返回响应状态码、头部和完整内容

TOOL_META:
{
  "name": "api_explorer",
  "description": "一个简单的HTTP请求工具，使用Python标准库向指定URL发送GET/POST请求，返回响应状态码、头部和完整内容（默认截断部分内容），以探索公共API或服务的可用性",
  "category": "网络侦察",
  "test_target": "知名公共API目录服务，预期返回200状态码和JSON响应，确认工具能正确获取远程信息",
  "test_args": "--url https://api.publicapis.org/entries --timeout 5",
  "version": "17.0"
}
"""
from __future__ import annotations

import argparse
import json
import ssl
import os
import urllib.request
from typing import Any
from urllib.parse import urlparse

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def main(url: str, timeout: int = 15, method: str = "GET", data: str = None, file: str = None, headers: str = None, full_content: bool = False) -> dict[str, Any]:
    """发送HTTP GET/POST请求并返回响应信息"""
    result: dict[str, Any] = {"success": False, "status_code": None, "request_headers": {}, "response_headers": {}, "content": "", "error": None}

    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            result["error"] = "Unsupported scheme. Use http or https."
            return result

        is_https = parsed.scheme == "https"

        # 解析请求头：先strip再json.loads，失败时fallback
        req_headers = {"User-Agent": DEFAULT_UA, "Accept": "*/*"}
        if headers:
            try:
                parsed_h = json.loads(headers.strip().strip("\"'"))
                if isinstance(parsed_h, dict):
                    req_headers.update(parsed_h)
            except (json.JSONDecodeError, TypeError) as e:
                print(f"[DEBUG] Failed to parse headers: {e}, using default UA")

        print(f"[DEBUG] Used headers: {req_headers}")
        result["request_headers"] = req_headers

        body = None
        if file and os.path.isfile(file):
            boundary = b"----WebKitFormBoundary" + os.urandom(16).hex()
            body = b""
            if data:
                body += b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"data\"\r\n\r\n" + data.encode("utf-8") + b"\r\n"
            filename = os.path.basename(file).encode()
            with open(file, "rb") as f:
                file_content = f.read()
            body += b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"" + filename + b"\"\r\nContent-Type: application/octet-stream\r\n\r\n" + file_content + b"\r\n--" + boundary + b"--\r\n"
            req_headers["Content-Type"] = f"multipart/form-data; boundary={boundary.decode()}"
        elif data:
            try:
                parsed_data = json.loads(data)
                body = json.dumps(parsed_data, ensure_ascii=False).encode("utf-8")
                req_headers["Content-Type"] = "application/json; charset=utf-8"
            except json.JSONDecodeError:
                body = data.encode("utf-8")
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        req = urllib.request.Request(url, data=body, headers=req_headers, method=method.upper())
        result["request_headers"] = dict(req.headers)

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        https_handler = urllib.request.HTTPSHandler(context=ctx)
        http_handler = urllib.request.HTTPHandler()
        opener = urllib.request.build_opener(https_handler if is_https else http_handler)

        response = opener.open(req, timeout=timeout)
        result["status_code"] = response.status
        result["response_headers"] = dict(response.headers)
        content = response.read().decode("utf-8", errors="replace")
        if full_content:
            result["content"] = content
        else:
            truncated = content[:100] if content else ""
            print(f"[DEBUG] Response truncated: {len(truncated)}/{len(content)} chars")
            result["content"] = truncated
        result["success"] = True
    except urllib.error.URLError as e:
        result["error"] = f"URLError: {e}"
    except ssl.SSLError as e:
        result["error"] = f"SSLError: {e}"
    except Exception as e:
        result["error"] = f"Error: {type(e).__name__}: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTTP API 探索工具")
    parser.add_argument("--url", default="http://httpbin.org/get", help="目标URL")
    parser.add_argument("--timeout", type=int, default=15, help="请求超时秒数")
    parser.add_argument("--method", default="GET", help="HTTP方法 (GET/POST)")
    parser.add_argument("--data", default=None, help="请求数据 (JSON或表单数据)")
    parser.add_argument("--file", default=None, help="上传文件路径 (multipart/form-data)")
    parser.add_argument("--headers", type=str, default=None, help="自定义请求头 (JSON格式)")
    parser.add_argument("--full_content", action="store_true", help="返回完整内容（默认仅返回前100字符）")
    args = parser.parse_args()
    result = main(args.url, args.timeout, args.method, args.data, args.file, args.headers, args.full_content)
    print(json.dumps(result, ensure_ascii=False, indent=2))