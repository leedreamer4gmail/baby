"""skill/custom_http_client.py - 一个简单的自定义HTTP客户端工具，使用Python标准库的socket模块构建基本的GET请求，支持添加头部（如Host），返回响应状态码、头部和完整内容，以绕过urllib的SSL和超时问题探索远程网页

SKILL_META:
{
  "name": "custom_http_client",
  "description": "一个简单的自定义HTTP客户端工具，使用Python标准库的socket模块构建基本的GET请求，支持添加头部（如Host），返回响应状态码、头部和完整内容，以绕过urllib的SSL和超时问题探索远程网页",
  "category": "网络侦察",
  "test_target": "GitHub注册页面，预期返回200状态码和包含CSRF令牌的HTML内容，确认工具能绕过超时问题",
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
from urllib.parse import urlparse

def main(
    url: str,
    headers: str | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "success": False,
        "status_code": 0,
        "headers": {},
        "full_content": "",
        "message": "",
    }
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query

        headers_dict: dict[str, str] = {"Host": host}
        if headers:
            for h in headers.split(","):
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers_dict[k.strip()] = v.strip()

        request_lines = [f"GET {path} HTTP/1.1", f"Host: {host}"]
        for k, v in headers_dict.items():
            request_lines.append(f"{k}: {v}")
        request_lines.extend(["", ""])
        request_data = "\r\n".join(request_lines).encode("utf-8")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        # 先建立TCP连接，再包装SSL
        sock.connect((host, port))

        if parsed.scheme == "https":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=host)

        sock.sendall(request_data)

        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if len(response) > 10 * 1024 * 1024:
                    break
            except socket.timeout:
                break
        sock.close()

        if not response:
            results["message"] = "No response received"
            return results

        response_text = response.decode("utf-8", errors="replace")
        parts = response_text.split("\r\n\r\n", 1)

        if len(parts) < 2:
            results["message"] = "Invalid response format"
            return results

        header_part, body = parts
        header_lines = header_part.split("\r\n")

        if header_lines and header_lines[0].startswith("HTTP/"):
            status_line = header_lines[0]
            status_parts = status_line.split(" ", 2)
            if len(status_parts) >= 2:
                results["status_code"] = int(status_parts[1])

        for line in header_lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                results["headers"][k.strip()] = v.strip()

        if results["status_code"] in (301, 302, 303, 307, 308):
            location = results["headers"].get("Location", "")
            results["message"] = f"Redirect to: {location}"
        else:
            results["message"] = "Success"

        results["full_content"] = body
        results["success"] = True

    except socket.timeout:
        results["message"] = "Timeout: connection timed out"
    except socket.gaierror as e:
        results["message"] = f"DNS error: {e}"
    except ConnectionRefusedError:
        results["message"] = "Connection refused"
    except ssl.SSLError as e:
        results["message"] = f"SSL error: {e}"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Custom HTTP client using socket")
    parser.add_argument(
        "--url",
        default="https://httpbin.org/get",
        help="Target URL (default: https://httpbin.org/get)",
    )
    parser.add_argument(
        "--headers",
        default=None,
        help="Additional headers in format 'Key1:Value1,Key2:Value2'",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds (default: 10)",
    )
    args = parser.parse_args()

    result = main(url=args.url, headers=args.headers, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))