"""skill/deploy_remote_ftp_v3.py - 通过匿名FTP部署payload文件到远程主机

SKILL_META:
{
  "name": "deploy_remote_ftp_v3",
  "description": "通过匿名FTP部署payload文件到远程主机",
  "category": "deploy",
  "test_target": "209.51.188.20:21",
  "test_args": "--host 209.51.188.20 --port 21 --directory /pub --payload_file my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

try:
    from upload_ftp_anon_dir import main as upload_ftp_anon_dir_run
except ImportError:
    upload_ftp_anon_dir_run = None

def main(
    host: str,
    port: int = 21,
    directory: str = "/pub",
    payload_file: str = "my_payload.py",
) -> dict[str, Any]:
    """通过匿名FTP部署payload文件到远程主机

    Args:
        host: FTP主机地址
        port: FTP端口，默认21
        directory: 远程目录，默认/pub
        payload_file: 本地payload文件路径，默认my_payload.py

    Returns:
        包含执行结果的字典
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        # 检查参数
        if not host:
            raise ValueError("必须提供host参数")

        # 检查payload文件是否存在
        if not os.path.exists(payload_file):
            raise FileNotFoundError(f"payload文件不存在: {payload_file}")

        if not os.path.isfile(payload_file):
            raise ValueError(f"payload文件不是普通文件: {payload_file}")

        # 检查upload_ftp_anon_dir工具是否可用
        if upload_ftp_anon_dir_run is None:
            raise ImportError("无法导入upload_ftp_anon_dir工具")

        # 调用upload_ftp_anon_dir工具上传文件
        upload_result = upload_ftp_anon_dir_run(
            host=host,
            port=port,
            directory=directory,
            local_file=payload_file,
        )

        if not upload_result.get("success", False):
            raise RuntimeError(f"上传失败: {upload_result.get('message', '未知错误')}")

        # 构建结果
        results["success"] = True
        results["message"] = f"成功部署payload文件到 {host}:{port}{directory}"
        results["data"] = {
            "host": host,
            "port": port,
            "directory": directory,
            "payload_file": payload_file,
            "upload_result": upload_result,
        }

    except (ValueError, FileNotFoundError, ImportError, RuntimeError) as e:
        results["message"] = f"部署失败: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="通过匿名FTP部署payload文件到远程主机")
    parser.add_argument("--host", type=str, required=True, help="FTP主机地址")
    parser.add_argument("--port", type=int, default=21, help="FTP端口，默认21")
    parser.add_argument("--directory", type=str, default="/pub", help="远程目录，默认/pub")
    parser.add_argument("--payload_file", type=str, default="my_payload.py", help="本地payload文件路径，默认my_payload.py")

    # 解析命令行参数
    if len(sys.argv) == 1:
        # 如果没有参数，使用测试参数
        test_args = [
            "--host", "209.51.188.20",
            "--port", "21",
            "--directory", "/pub",
            "--payload_file", "my_payload.py"
        ]
        args = parser.parse_args(test_args)
    else:
        args = parser.parse_args()

    # 运行主函数
    result = main(
        host=args.host,
        port=args.port,
        directory=args.directory,
        payload_file=args.payload_file,
    )

    # 输出JSON格式结果
    print(json.dumps(result, ensure_ascii=False, indent=2))