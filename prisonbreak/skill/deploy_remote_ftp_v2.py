"""skill/deploy_remote_ftp_v2.py - 通过匿名FTP部署payload文件到远程主机

SKILL_META:
{
  "name": "deploy_remote_ftp_v2",
  "description": "通过匿名FTP部署payload文件到远程主机",
  "category": "deploy",
  "test_target": "209.51.188.20:21 的 pub 目录",
  "test_args": "--host 209.51.188.20 --port 21 --directory pub --payload_file my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
import os
import argparse
from typing import Any

def main(host: str, port: int, directory: str, payload_file: str) -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        # 检查payload文件是否存在
        if not os.path.exists(payload_file):
            raise FileNotFoundError(f"Payload文件 '{payload_file}' 不存在")

        # 检查payload文件是否有__main__入口
        with open(payload_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'if __name__ == "__main__"' not in content:
                raise ValueError(f"Payload文件 '{payload_file}' 缺少 __main__ 入口")

        # 导入并运行FTP连接工具
        from connect_ftp_anon import main as connect_ftp_anon_run
        from upload_ftp_anon_dir import main as upload_ftp_anon_dir_run

        # 连接FTP
        connect_result = connect_ftp_anon_run(host=host, port=port)
        if not connect_result.get("success"):
            raise ConnectionError(f"FTP连接失败: {connect_result.get('message')}")

        # 上传payload文件
        upload_result = upload_ftp_anon_dir_run(
            host=host,
            port=port,
            directory=directory,
            local_file=payload_file
        )

        if not upload_result.get("success"):
            raise RuntimeError(f"文件上传失败: {upload_result.get('message')}")

        results["success"] = True
        results["message"] = f"Payload文件 '{payload_file}' 已成功部署到 {host}:{port}/{directory}"
        results["data"] = {
            "host": host,
            "port": port,
            "directory": directory,
            "payload_file": payload_file,
            "upload_result": upload_result.get("data", {})
        }

    except FileNotFoundError as e:
        results["message"] = f"文件错误: {e}"
    except ValueError as e:
        results["message"] = f"Payload格式错误: {e}"
    except ConnectionError as e:
        results["message"] = str(e)
    except RuntimeError as e:
        results["message"] = str(e)
    except ImportError as e:
        results["message"] = f"依赖工具导入失败: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {type(e).__name__}: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="通过匿名FTP部署payload文件到远程主机")
    parser.add_argument("--host", required=True, help="FTP主机地址")
    parser.add_argument("--port", type=int, required=True, help="FTP端口")
    parser.add_argument("--directory", required=True, help="远程目录")
    parser.add_argument("--payload_file", required=True, help="本地payload文件路径")

    try:
        args = parser.parse_args()
        r = main(args.host, args.port, args.directory, args.payload_file)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    except SystemExit:
        # 当参数解析失败时，argparse会调用sys.exit()
        # 直接退出，不输出JSON，让argparse显示帮助信息
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "message": f"执行错误: {type(e).__name__}: {e}",
            "data": {}
        }, ensure_ascii=False, indent=2))
        sys.exit(1)