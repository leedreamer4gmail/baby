"""skill/deploy_http_post_multipart.py - 使用HTTP POST多部分表单上传payload到远程路径

SKILL_META:
{
  "name": "deploy_http_post_multipart",
  "description": "使用HTTP POST多部分表单上传payload到远程路径",
  "category": "deploy",
  "test_target": "209.51.188.20:80 /pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub --payload_file clone.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
import http.client
import mimetypes

def build_multipart_body(
    fields: dict[str, tuple[str, bytes, str]]
) -> tuple[bytes, str]:
    """构建 multipart/form-data 请求体"""
    boundary = "----FormBoundary" + "".join(
        format(i, "02x") for i in os.urandom(8)
    )

    body = b""
    for name, (filename, content, content_type) in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content
        body += b"\r\n"

    body += f"--{boundary}--\r\n".encode()
    return body, boundary

def main(
    host: str = None,
    port: int = None,
    path: str = None,
    payload_file: str = None
) -> dict[str, Any]:
    """使用HTTP POST多部分表单上传payload到远程路径"""
    result: dict[str, Any] = {
        "success": False,
        "response_code": 0,
        "message": ""
    }

    # 如果没有传入参数，从 sys.argv 解析
    if host is None or port is None or path is None or payload_file is None:
        if len(sys.argv) >= 5 and sys.argv[1].startswith("--"):
            # 命令行参数格式: --host IP --port PORT --path PATH --payload_file FILE
            parser = argparse.ArgumentParser(description="HTTP POST multipart upload")
            parser.add_argument("--host", required=True, help="Target host IP")
            parser.add_argument("--port", type=int, required=True, help="Target port")
            parser.add_argument("--path", required=True, help="Upload path")
            parser.add_argument("--payload_file", required=True, help="Payload file to upload")
            args = parser.parse_args()
            host = args.host
            port = args.port
            path = args.path
            payload_file = args.payload_file
        elif len(sys.argv) >= 5:
            # 位置参数格式: IP PORT PATH FILE
            host = sys.argv[1]
            port = int(sys.argv[2])
            path = sys.argv[3]
            payload_file = sys.argv[4]
        else:
            result["message"] = "Missing required arguments"
            return result

    try:
        if not os.path.exists(payload_file):
            result["message"] = f"Payload file not found: {payload_file}"
            return result

        with open(payload_file, "rb") as f:
            file_content = f.read()

        content_type = mimetypes.guess_type(payload_file)[0] or "application/octet-stream"
        filename = os.path.basename(payload_file)
        fields = {"file": (filename, file_content, content_type)}

        body, boundary = build_multipart_body(fields)

        conn = http.client.HTTPConnection(host, port, timeout=30)
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body))
        }

        conn.request("POST", path, body, headers)
        response = conn.getresponse()

        response_body = response.read().decode("utf-8", errors="replace")
        response_code = response.status
        conn.close()

        result["response_code"] = response_code
        result["message"] = response_body[:500] if response_body else "Empty response"
        result["success"] = True if 200 <= response_code < 300 else False

    except FileNotFoundError as e:
        result["message"] = f"File error: {e}"
    except ConnectionRefusedError as e:
        result["message"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["message"] = f"Connection timeout: {e}"
    except OSError as e:
        result["message"] = f"Network error: {e}"
    except Exception as e:
        result["message"] = f"Unexpected error: {e}"

    return result

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))