"""skill/fetch_http_fixed_headers.py - Fetch HTTP content with fixed browser-mimicking headers to bypass protections like Cloudflare.

SKILL_META:
{
  "name": "fetch_http_fixed_headers",
  "description": "Fetch HTTP content with fixed browser-mimicking headers to bypass protections like Cloudflare.",
  "category": "http",
  "test_target": "Cloudflare-protected HTTP server at 104.18.27.120:80",
  "test_args": "104.18.27.120 80 /",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

def main(host: str = "104.18.27.120", port: int = 80, path: str = "/") -> dict[str, Any]:
    """Fetch HTTP content with fixed browser-mimicking headers."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    fixed_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        request_lines = [f"GET {path} HTTP/1.1", f"Host: {host}"]
        for key, value in fixed_headers.items():
            request_lines.append(f"{key}: {value}")
        request_lines.append("")
        request = "\r\n".join(request_lines) + "\r\n"

        sock.sendall(request.encode("utf-8"))

        response = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
                if len(response) > 1024 * 1024:
                    break
            except socket.timeout:
                break
        sock.close()

        if not response:
            results["message"] = "错误: 未收到响应"
            return results

        response_str = response.decode("utf-8", errors="replace")
        if "\r\n\r\n" in response_str:
            header_part, body = response_str.split("\r\n\r\n", 1)
        else:
            header_part, body = response_str, ""

        if not header_part:
            results["message"] = "错误: 响应头为空"
            return results

        status_line = header_part.split("\r\n")[0]

        results["success"] = True
        results["message"] = "完成"
        results["data"] = {
            "status_line": status_line,
            "header_lines": header_part,
            "body_length": len(body),
            "body_preview": body[:1000] if body else "",
        }

    except socket.timeout:
        results["message"] = "错误: 连接超时"
    except ConnectionRefusedError:
        results["message"] = "错误: 连接被拒绝"
    except OSError as e:
        results["message"] = f"错误: 网络异常 - {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        host_arg = sys.argv[1]
        port_arg = int(sys.argv[2])
        path_arg = sys.argv[3]
    elif len(sys.argv) >= 2:
        host_arg = sys.argv[1]
        port_arg = 80
        path_arg = "/"
    else:
        host_arg = "104.18.27.120"
        port_arg = 80
        path_arg = "/"

    result = main(host_arg, port_arg, path_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))