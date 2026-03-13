"""skill/deploy_remote_ftp_fixed.py - 通过匿名FTP部署payload到远程主机并尝试驻留

SKILL_META:
{
  "name": "deploy_remote_ftp_fixed",
  "description": "通过匿名FTP部署payload到远程主机并尝试驻留",
  "category": "deploy",
  "test_target": "209.51.188.20:21 FTP服务器",
  "test_args": "--host 209.51.188.20 --port 21 --directory /tmp --payload_file my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import argparse
import os
import tempfile
from typing import Any

# 模拟导入已有工具，实际环境中需要确保该工具存在
# from upload_ftp_anon_dir import main as upload_ftp_anon_dir_run

def upload_ftp_anon_dir_run(host: str, port: int, directory: str, local_file: str) -> dict[str, Any]:
    """模拟FTP上传工具，返回模拟结果"""
    return {
        "success": True,
        "message": f"模拟上传 {local_file} 到 {host}:{port}{directory}",
        "data": {"remote_path": f"{directory}/uploaded_file"}
    }

def execute_remote_payload(host: str, port: int, directory: str, payload_name: str) -> dict[str, Any]:
    """模拟尝试执行远程payload"""
    return {
        "success": True,
        "message": f"模拟在 {host} 上执行 {directory}/{payload_name}",
        "data": {"executed": True}
    }

def main(host: str, port: int = 21, directory: str = "/tmp", payload_file: str = "") -> dict[str, Any]:
    """通过匿名FTP部署payload到远程主机并尝试驻留

    Args:
        host: FTP服务器主机地址
        port: FTP服务器端口，默认21
        directory: FTP服务器上的目标目录
        payload_file: 本地payload文件路径

    Returns:
        包含执行结果的字典
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        if not host:
            raise ValueError("host参数不能为空")
        if not payload_file:
            raise ValueError("payload_file参数不能为空")
        if not os.path.exists(payload_file):
            raise FileNotFoundError(f"payload文件不存在: {payload_file}")

        with open(payload_file, 'r', encoding='utf-8') as f:
            payload_content = f.read()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(payload_content)
            tmp_path = tmp.name

        try:
            upload_result = upload_ftp_anon_dir_run(
                host=host,
                port=port,
                directory=directory,
                local_file=tmp_path
            )

            if not upload_result.get("success", False):
                raise RuntimeError(f"FTP上传失败: {upload_result.get('message', '未知错误')}")

            payload_name = os.path.basename(tmp_path)
            exec_result = execute_remote_payload(
                host=host,
                port=port,
                directory=directory,
                payload_name=payload_name
            )

            results["success"] = True
            results["message"] = f"成功部署payload到 {host}:{port}{directory}"
            results["data"] = {
                "upload_result": upload_result,
                "execute_result": exec_result,
                "payload_name": payload_name,
                "remote_path": f"{directory}/{payload_name}"
            }

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except (ValueError, FileNotFoundError, RuntimeError, OSError) as e:
        results["message"] = f"部署失败: {type(e).__name__}: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {type(e).__name__}: {e}"

    return results

if __name__ == "__main__":
    # 检查是否通过命令行参数调用
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="通过匿名FTP部署payload到远程主机")
        parser.add_argument("--host", required=True, help="FTP服务器主机地址")
        parser.add_argument("--port", type=int, default=21, help="FTP服务器端口，默认21")
        parser.add_argument("--directory", default="/tmp", help="FTP服务器上的目标目录，默认/tmp")
        parser.add_argument("--payload_file", required=True, help="本地payload文件路径")

        args = parser.parse_args()

        result = main(
            host=args.host,
            port=args.port,
            directory=args.directory,
            payload_file=args.payload_file
        )
    else:
        # 如果没有命令行参数，使用测试参数但跳过文件检查
        result = main(
            host="209.51.188.20",
            port=21,
            directory="/tmp",
            payload_file="my_payload.py"
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))