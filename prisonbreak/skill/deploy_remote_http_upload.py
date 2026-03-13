"""skill/deploy_remote_http_upload.py - 通过HTTP POST上传payload到远程主机，实现部署

SKILL_META:
{
  "name": "deploy_remote_http_upload",
  "description": "通过HTTP POST上传payload到远程主机，实现部署",
  "category": "deploy",
  "test_target": "209.51.188.20:80，支持POST的HTTP服务",
  "test_args": "--host 209.51.188.20 --port 80 --path /upload.php --payload_file my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
from typing import Any

from fetch_http_with_headers import main as fetch_http_with_headers_run

def read_payload_file(file_path: str) -> str:
    """读取本地payload文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Payload文件未找到: {file_path}") from e
    except PermissionError as e:
        raise PermissionError(f"无权限读取文件: {file_path}") from e
    except UnicodeDecodeError as e:
        raise UnicodeDecodeError(f"文件编码错误: {file_path}") from e

def build_upload_url(host: str, port: int, path: str) -> str:
    """构建上传URL"""
    scheme = "http"
    if port == 443:
        scheme = "https"

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        return f"{scheme}://{host}{path}"
    return f"{scheme}://{host}:{port}{path}"

def main(host: str, port: int, path: str, payload_file: str) -> dict[str, Any]:
    """通过HTTP POST上传payload到远程主机

    Args:
        host: 目标主机IP或域名
        port: 目标端口
        path: 上传路径
        payload_file: 本地payload文件路径

    Returns:
        dict: 包含执行结果的字典
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # 1. 读取payload文件
        payload_content = read_payload_file(payload_file)

        # 2. 构建上传URL
        upload_url = build_upload_url(host, port, path)

        # 3. 准备POST请求参数
        post_data = {"payload": payload_content}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Deploy-Agent/1.0"
        }

        # 4. 调用已有工具发送POST请求
        fetch_result = fetch_http_with_headers_run(
            url=upload_url,
            method="POST",
            headers=headers,
            data=post_data
        )

        # 5. 处理响应
        if fetch_result["success"]:
            response_data = fetch_result.get("data", {})
            status_code = response_data.get("status_code", 0)
            response_body = response_data.get("body", "")

            results["data"] = {
                "status_code": status_code,
                "response": response_body,
                "upload_url": upload_url,
                "payload_size": len(payload_content)
            }

            if 200 <= status_code < 300:
                results["success"] = True
                results["message"] = f"上传成功，状态码: {status_code}"
            else:
                results["message"] = f"上传失败，状态码: {status_code}"
        else:
            results["message"] = f"HTTP请求失败: {fetch_result.get('message', '未知错误')}"

    except FileNotFoundError as e:
        results["message"] = f"文件错误: {e}"
    except PermissionError as e:
        results["message"] = f"权限错误: {e}"
    except UnicodeDecodeError as e:
        results["message"] = f"编码错误: {e}"
    except ConnectionError as e:
        results["message"] = f"连接错误: {e}"
    except TimeoutError as e:
        results["message"] = f"超时错误: {e}"
    except ValueError as e:
        results["message"] = f"参数错误: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {type(e).__name__}: {e}"

    return results

if __name__ == "__main__":
    # 简化参数解析，直接使用位置参数
    if len(sys.argv) != 5:
        error_result = {
            "success": False,
            "message": "参数错误，请使用: python deploy_remote_http_upload.py HOST PORT PATH PAYLOAD_FILE",
            "data": {}
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)

    try:
        host = sys.argv[1]
        port = int(sys.argv[2])
        path = sys.argv[3]
        payload_file = sys.argv[4]

        result = main(host, port, path, payload_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except ValueError as e:
        error_result = {
            "success": False,
            "message": f"端口号必须是整数: {e}",
            "data": {}
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)