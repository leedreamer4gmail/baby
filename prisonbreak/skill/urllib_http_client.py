"""skill/urllib_http_client.py - 一个简单的HTTP客户端工具，使用Python标准库的urllib.request模块发送GET/POST/PUT请求，支持自定义头部、超时和HTTPS连接，返回响应状态码、头部和完整内容，以探索远程服务

SKILL_META:
{
  "name": "urllib_http_client",
  "description": "一个简单的HTTP客户端工具，使用Python标准库的urllib.request模块发送GET/POST/PUT请求，支持自定义头部、超时和HTTPS连接，返回响应状态码、头部和完整内容，以探索远程服务",
  "category": "其他",
  "test_target": "GitHub注册页面，预期返回200状态码、相关头部和完整HTML内容（包含<form>元素和可能的CSRF令牌），确认工具能正确处理HTTPS连接而不超时",
  "test_args": "--url https://github.com/signup --method GET --timeout 10",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

def main(
    url: str,
    method: str = "GET",
    headers: str = "",
    data: str = "",
    timeout: int = 30,
) -> dict[str, Any]:
    """发送HTTP请求并返回响应详情"""
    result: dict[str, Any] = {
        "success": False,
        "status_code": 0,
        "headers": {},
        "full_content": "",
        "message": "",
        "method": method,
    }

    try:
        # 解析自定义头部
        header_dict: dict[str, str] = {}
        if headers:
            for h in headers.split(","):
                if ":" in h:
                    key, val = h.split(":", 1)
                    header_dict[key.strip()] = val.strip()

        # 准备请求数据
        req_data: bytes | None = None
        if method in ("POST", "PUT") and data:
            req_data = data.encode("utf-8")
            if "Content-Type" not in header_dict:
                header_dict["Content-Type"] = "application/x-www-form-urlencoded"

        # 构建请求对象
        request = urllib.request.Request(url, data=req_data, headers=header_dict, method=method)

        # 发送请求
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result["status_code"] = response.status
            result["headers"] = dict(response.headers)
            result["full_content"] = response.read().decode("utf-8", errors="replace")
            result["success"] = True
            result["message"] = "请求成功"

    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["headers"] = dict(e.headers) if e.headers else {}
        try:
            result["full_content"] = e.read().decode("utf-8", errors="replace")
        except Exception:
            result["full_content"] = ""
        result["message"] = f"HTTP错误: {e.code} {e.reason}"
        result["success"] = True  # HTTP错误也视为有响应

    except urllib.error.URLError as e:
        result["message"] = f"URL错误: {e.reason}"

    except TimeoutError:
        result["message"] = "请求超时"

    except Exception as e:
        result["message"] = f"错误: {type(e).__name__}: {e}"

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="简单的HTTP客户端工具")
    parser.add_argument("--url", default="http://httpbin.org/get", help="请求URL")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT"], help="HTTP方法")
    parser.add_argument("--headers", default="", help="自定义头部，格式: key:value,key:value")
    parser.add_argument("--data", default="", help="POST/PUT请求数据")
    parser.add_argument("--timeout", type=int, default=30, help="超时秒数")

    args = parser.parse_args()

    result = main(
        url=args.url,
        method=args.method,
        headers=args.headers,
        data=args.data,
        timeout=args.timeout,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))