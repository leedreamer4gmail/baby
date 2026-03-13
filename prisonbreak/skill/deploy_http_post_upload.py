"""skill/deploy_http_post_upload.py - 使用HTTP POST上传文件到指定路径

SKILL_META:
{
  "name": "deploy_http_post_upload",
  "description": "使用HTTP POST上传文件到指定路径",
  "category": "http",
  "test_target": "209.51.188.20:80/pub",
  "test_args": "--host 209.51.188.20 --port 80 --path /pub/test.py --payload_file test_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def main(
    host: str,
    port: int,
    path: str,
    payload_file: str,
) -> dict[str, Any]:
    """使用HTTP POST上传文件到指定路径

    Args:
        host: 目标主机
        port: 目标端口
        path: 上传路径
        payload_file: 要上传的文件路径

    Returns:
        包含执行结果的字典
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # 构建完整的URL
        base_url = f"http://{host}:{port}"
        full_url = urljoin(base_url, path)

        # 读取要上传的文件
        try:
            with open(payload_file, 'rb') as f:
                file_content = f.read()
        except FileNotFoundError:
            results["message"] = f"文件未找到: {payload_file}"
            return results
        except PermissionError:
            results["message"] = f"无权限读取文件: {payload_file}"
            return results
        except OSError as e:
            results["message"] = f"读取文件失败: {e}"
            return results

        # 准备multipart form-data
        boundary = '----WebKitFormBoundary' + ''.join(str(i) for i in range(10))
        filename = payload_file.split('/')[-1]

        # 构建请求体
        body_parts = []
        body_parts.append(f'--{boundary}')
        body_parts.append(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"'
        )

        # 猜测内容类型
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        body_parts.append(f'Content-Type: {content_type}')
        body_parts.append('')
        body_parts.append('')

        # 将各部分转换为字节
        body = b''
        for part in body_parts[:-1]:
            body += part.encode('utf-8') + b'\r\n'
        body += file_content + b'\r\n'
        body += f'--{boundary}--\r\n'.encode('utf-8')

        # 创建并发送请求
        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(body)),
            'User-Agent': 'Python-HTTP-Post-Upload/1.0'
        }

        request = Request(full_url, data=body, headers=headers, method='POST')

        try:
            with urlopen(request, timeout=30) as response:
                status_code = response.getcode()
                response_body = response.read().decode('utf-8', errors='ignore')

                results["data"] = {
                    "status_code": status_code,
                    "response": response_body,
                    "url": full_url,
                    "filename": filename
                }

                if 200 <= status_code < 300:
                    results["success"] = True
                    results["message"] = f"文件上传成功，状态码: {status_code}"
                else:
                    results["message"] = f"服务器返回错误状态码: {status_code}"

        except HTTPError as e:
            results["message"] = f"HTTP错误: {e.code} {e.reason}"
            results["data"] = {"status_code": e.code}
        except URLError as e:
            results["message"] = f"URL错误: {e.reason}"
        except TimeoutError:
            results["message"] = "请求超时"

    except Exception as e:
        results["message"] = f"上传过程中发生错误: {e}"

    return results

if __name__ == "__main__":
    # 直接解析命令行参数，不通过argparse的parse_args()来避免SystemExit异常
    args = sys.argv[1:]

    # 手动解析参数
    params = {}
    i = 0
    while i < len(args):
        if args[i] == "--host" and i + 1 < len(args):
            params["host"] = args[i + 1]
            i += 2
        elif args[i] == "--port" and i + 1 < len(args):
            try:
                params["port"] = int(args[i + 1])
            except ValueError:
                print(json.dumps({
                    "success": False,
                    "message": f"端口号必须是整数: {args[i + 1]}",
                    "data": {}
                }, ensure_ascii=False, indent=2))
                sys.exit(1)
            i += 2
        elif args[i] == "--path" and i + 1 < len(args):
            params["path"] = args[i + 1]
            i += 2
        elif args[i] == "--payload_file" and i + 1 < len(args):
            params["payload_file"] = args[i + 1]
            i += 2
        else:
            i += 1

    # 检查必需参数
    required_params = ["host", "port", "path", "payload_file"]
    missing_params = [p for p in required_params if p not in params]

    if missing_params:
        print(json.dumps({
            "success": False,
            "message": f"缺少必需参数: {', '.join(missing_params)}",
            "data": {}
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 执行主函数
    try:
        result = main(**params)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "message": f"执行失败: {e}",
            "data": {}
        }, ensure_ascii=False, indent=2))
        sys.exit(1)