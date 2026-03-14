"""skill/socket_http_client.py - 一个简单的自定义HTTP客户端工具，使用Python标准库的socket模块发送基本的HTTP GET请求，支持添加头部（如Host），返回响应状态码、头部和完整内容，以绕过urllib的SSL和超时问题探索远程服务

SKILL_META:
{
  "name": "socket_http_client",
  "description": "一个简单的自定义HTTP客户端工具，使用Python标准库的socket模块发送基本的HTTP GET请求，支持添加头部（如Host），返回响应状态码、头部和完整内容，以绕过urllib的SSL和超时问题探索远程服务",
  "category": "other",
  "test_target": "GitHub注册页面，预期返回200状态码、相关头部和完整HTML内容（包含<form>元素和可能的CSRF令牌），确认工具能正确处理HTTPS连接而不超时",
  "test_args": "--url https://github.com/signup --timeout 10",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import socket
import ssl
from typing import Any

def parse_url(url: str) -> tuple[str, int, str, bool]:
    """解析URL，返回 (host, port, path, is_https)"""
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    is_https = url.startswith("https://")
    # 去掉协议前缀
    rest = url.split("://", 1)[1]

    # 分离 path
    if "/" in rest:
        host_port, path = rest.split("/", 1)
        path = "/" + path
    else:
        host_port = rest
        path = "/"

    # 分离 host 和 port
    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 443 if is_https else 80

    return host, port, path, is_https

def build_request(path: str, host: str, extra_headers: list[str] | None = None) -> bytes:
    """构建 HTTP GET 请求字节数据"""
    lines = [f"GET {path} HTTP/1.1", f"Host: {host}", "Connection: close"]
    if extra_headers:
        lines.extend(extra_headers)
    request = "\r\n".join(lines) + "\r\n\r\n"
    return request.encode("utf-8")

def parse_response(data: bytes) -> dict[str, Any]:
    """解析 HTTP 响应，返回 status_code, headers, body"""
    text = data.decode("utf-8", errors="replace")

    if "\r\n\r\n" in text:
        header_part, body = text.split("\r\n\r\n", 1)
    else:
        header_part, body = text, ""

    # 解析状态行
    status_line = header_part.split("\r\n")[0]
    parts = status_line.split()
    status_code = int(parts[1]) if len(parts) > 1 else 0

    # 解析头部
    headers: dict[str, str] = {}
    for line in header_part.split("\r\n")[1:]:
        if ": " in line:
            key, val = line.split(": ", 1)
            headers[key.lower()] = val

    return {"status_code": status_code, "headers": headers, "body": body}

def main(url: str, headers: list[str] | None = None, timeout: int = 5) -> dict[str, Any]:
    """使用 socket 发送 HTTP GET 请求，返回响应状态码、头部和完整内容"""
    result: dict[str, Any] = {
        "success": False,
        "status_code": 0,
        "headers": {},
        "full_content": "",
        "message": ""
    }

    try:
        host, port, path, is_https = parse_url(url)
        request_data = build_request(path, host, headers)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        try:
            if is_https:
                context = ssl.create_default_context()
                sock = context.wrap_socket(sock, server_hostname=host)

            sock.connect((host, port))
            sock.sendall(request_data)

            # 接收响应
            response = b""
            while True:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response += chunk

        finally:
            sock.close()

        # 解析响应
        parsed = parse_response(response)
        result["status_code"] = parsed["status_code"]
        result["headers"] = parsed["headers"]
        result["full_content"] = parsed["body"]
        result["success"] = True
        result["message"] = "请求完成"

    except socket.timeout:
        result["message"] = f"连接超时 (timeout={timeout}s)"
    except socket.gaierror as e:
        result["message"] = f"DNS解析错误: {e}"
    except ConnectionRefusedError as e:
        result["message"] = f"连接被拒绝: {e}"
    except ssl.SSLError as e:
        result["message"] = f"SSL错误: {e}"
    except OSError as e:
        result["message"] = f"网络错误: {e}"

    return result

if __name__ == "__main__":
    # 所有目标参数必须通过 CLI 传入，禁止硬编码
    parser = argparse.ArgumentParser(description="基于 socket 的 HTTP 客户端工具")
    parser.add_argument("--url", default="http://httpbin.org/get", help="目标URL")
    parser.add_argument("--headers", nargs="*", help="额外头部，格式: Header-Name:value")
    parser.add_argument("--timeout", type=int, default=5, help="超时秒数")

    args = parser.parse_args()

    result = main(args.url, args.headers, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))