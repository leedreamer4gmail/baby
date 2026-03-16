"""skill/urllib_http_client.py - 一个简单的HTTP客户端工具，使用Python标准库的http.client模块发送GET/POST/PUT请求，支持自定义头部、超时和文件上传，返回响应状态码、头部和完整内容

TOOL_META:
{
  "name": "urllib_http_client",
  "description": "一个简单的HTTP客户端工具，使用Python标准库的http.client模块发送GET/POST/PUT请求，支持自定义头部、超时和文件上传，返回响应状态码、头部和完整内容",
  "category": "其他",
  "test_target": "GitHub注册页面，预期返回200状态码、相关头部和完整HTML内容（包含<form>元素和可能的CSRF令牌），确认工具能正确处理HTTP连接",
  "test_args": "--url http://httpbin.org/post --method POST --data \"test=hello\" --timeout 30",
  "version": "14.0"
}
"""
from __future__ import annotations

import argparse
import http.client
import json
import ssl
import sys
import urllib.parse
import uuid
from typing import Any

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 默认浏览器 headers
DEFAULT_BROWSER_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

def parse_headers(headers_str: str) -> dict[str, str]:
    """解析自定义header字符串为字典"""
    result = {}
    if not headers_str:
        return result
    for h in headers_str.split(","):
        if ":" in h:
            k, v = h.split(":", 1)
            result[k.strip()] = v.strip()
    return result

def build_multipart(fields: dict[str, str], file_field: str, file_path: str) -> tuple[bytes, str, str]:
    """手动拼接multipart/form-data请求体(RFC7578)"""
    boundary = str(uuid.uuid4()).replace("-", "")
    print(f"[BOUNDARY] {boundary}", file=sys.stderr)
    parts = []
    for name, value in fields.items():
        if name != file_field:
            part = f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n"
            parts.append(part.encode("utf-8"))
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
        filename = file_path.replace("\\", "/").split("/")[-1]
    except Exception as e:
        raise ValueError(f"读取文件失败: {file_path}")
    if len(file_data) > 10 * 1024 * 1024:
        raise ValueError("文件过大(>10MB)")
    header_part = f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
    parts.append(header_part.encode("utf-8"))
    parts.append(file_data)
    parts.append(b"\r\n--{boundary}--\r\n")
    body = b"".join(parts)
    return body, f"multipart/form-data; boundary={boundary}", boundary

def main(
    url: str,
    method: str = "GET",
    headers: str = "",
    data: str = "",
    timeout: int = 30,
    user_agent: str = DEFAULT_UA,
    file_field: str = "",
    file_path: str = "",
) -> dict[str, Any]:
    """发送HTTP请求并返回响应详情"""
    result: dict[str, Any] = {
        "success": False, "status_code": 0, "headers": {}, "full_content": "",
        "message": "", "method": method, "used_user_agent": user_agent,
        "used_multipart": False, "file_field": "", "generated_boundary": "",
        "boundary_used": "", "multipart_success": False, "files_content_length": 0,
    }
    if url.startswith("https://"):
        url = "http://" + url[8:]
    parsed = urllib.parse.urlparse(url)
    host, port = parsed.netloc.split(":") if ":" in parsed.netloc else (parsed.netloc, 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    is_ssl = False
    try:
        # 初始化默认浏览器 headers
        header_dict = dict(DEFAULT_BROWSER_HEADERS)
        header_dict["User-Agent"] = user_agent
        # 解析自定义 headers 并合并
        if headers:
            custom_headers = parse_headers(headers)
            header_dict.update(custom_headers)
        # 添加 Referer 和 Origin（如果自定义 headers 中没有提供）
        if "Referer" not in header_dict and parsed.scheme and parsed.netloc:
            header_dict["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        if "Origin" not in header_dict and parsed.scheme and parsed.netloc:
            header_dict["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
        req_data: bytes | None = None
        used_multipart = False
        generated_boundary = ""
        if file_path and file_field:
            if method == "GET":
                method = "POST"
            fields = {}
            if data:
                for item in data.split("&"):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        fields[urllib.parse.unquote(k)] = urllib.parse.unquote(v)
            req_data, content_type, generated_boundary = build_multipart(fields, file_field, file_path)
            header_dict["Content-Type"] = content_type
            header_dict["Content-Length"] = str(len(req_data))
            used_multipart = True
            result["file_field"] = file_field
            result["generated_boundary"] = generated_boundary
            result["boundary_used"] = generated_boundary
            result["multipart_success"] = True
            result["files_content_length"] = len(req_data)
        elif method in ("POST", "PUT") and data:
            req_data = data.encode("utf-8")
            if "Content-Type" not in header_dict:
                header_dict["Content-Type"] = "application/x-www-form-urlencoded"
            header_dict["Content-Length"] = str(len(req_data))
        print(f"[WIRE] Connecting to {host}:{port}", file=sys.stderr)
        conn = http.client.HTTPConnection(host, port=port if port != 80 else None, timeout=timeout)
        print(f"[WIRE] {method} {path} HTTP/1.1", file=sys.stderr)
        # 打印最终 headers
        print(f"[WIRE] Final Request Headers:", file=sys.stderr)
        for k, v in header_dict.items():
            print(f"[WIRE]   {k}: {v}", file=sys.stderr)
        conn.putrequest(method, path)
        for k, v in header_dict.items():
            conn.putheader(k, v)
        conn.endheaders()
        print(f"[WIRE] Request headers sent", file=sys.stderr)
        if req_data:
            # 打印 body 前512字节
            body_preview = req_data[:512]
            print(f"[WIRE] Sending body ({len(req_data)} bytes), first_512={body_preview.hex()}", file=sys.stderr)
            conn.send(req_data)
            print(f"[WIRE] Body sent", file=sys.stderr)
        response = conn.getresponse()
        print(f"[WIRE] {response.status} {response.reason}", file=sys.stderr)
        result["status_code"] = response.status
        result["headers"] = dict(response.getheaders())
        result["full_content"] = response.read().decode("utf-8", errors="replace")
        result["success"] = True
        result["message"] = "请求成功"
        result["used_user_agent"] = header_dict.get("User-Agent", user_agent)
        result["used_multipart"] = used_multipart
        conn.close()
    except http.client.HTTPException as e:
        result["message"] = f"HTTP错误: {type(e).__name__}: {e}"
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
    parser.add_argument("--user_agent", default=DEFAULT_UA, help="User-Agent字符串")
    parser.add_argument("--file_field", default="", help="文件字段名")
    parser.add_argument("--file_path", default="", help="要上传的文件路径")
    args = parser.parse_args()
    result = main(
        url=args.url, method=args.method, headers=args.headers, data=args.data,
        timeout=args.timeout, user_agent=args.user_agent,
        file_field=args.file_field, file_path=args.file_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))