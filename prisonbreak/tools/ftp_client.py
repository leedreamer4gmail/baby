"""skill/ftp_client.py - 一个简单的FTP客户端工具，使用Python标准库的ftplib模块连接到指定FTP服务器，支持匿名登录、目录列出和基本文件上传/下载

TOOL_META:
{
  "name": "ftp_client",
  "description": "一个简单的FTP客户端工具，使用Python标准库的ftplib模块连接到指定FTP服务器，支持匿名登录、目录列出和基本文件上传/下载",
  "category": "FTP渗透",
  "test_target": "测试公共FTP服务，预期匿名登录成功并返回目录列表",
  "test_args": "--host ftp.gnu.org --port 21 --action list --timeout 10",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from typing import Any
from ftplib import FTP, FTP_TLS
from datetime import datetime

def main(
    host: str,
    port: int = 21,
    action: str = "list",
    file: str = "test.txt",
    file_path: str = "",
    timeout: int = 10,
    remote_path: str = ""
) -> dict[str, Any]:
    results: dict[str, Any] = {
        "success": False,
        "logged_in": False,
        "message": "",
        "data": {},
        "remote_path_used": remote_path
    }

    ftp: FTP | None = None

    try:
        ftp = FTP()
        ftp.connect(host, port, timeout=timeout)
        ftp.login()  # 匿名登录：anonymous + 空密码

        results["logged_in"] = True
        results["message"] = f"成功登录到 {host}"

        if action == "list":
            files: list[str] = []
            ftp.retrlines("LIST", files.append)
            results["data"]["directory_listing"] = files
            results["success"] = True

        elif action == "upload":
            local_file = file_path if file_path else file

            if not os.path.exists(local_file):
                results["message"] = f"文件不存在: {local_file}"
                results["upload_status"] = "failed"
                return results

            # 优先使用 remote_path，否则使用 file 参数作为远程文件名
            remote_name = remote_path if remote_path else os.path.basename(file)

            try:
                with open(local_file, "rb") as f:
                    resp = ftp.storbinary(f"STOR {remote_name}", f)

                if resp.startswith("226"):
                    results["data"]["upload_success"] = True
                    results["data"]["filename"] = remote_name
                    results["data"]["local_path"] = local_file
                    results["data"]["remote_path"] = remote_name
                    results["success"] = True
                    results["upload_status"] = "success"
                    results["message"] = f"文件上传成功: {local_file} -> {remote_name}"
                else:
                    results["upload_status"] = "failed"
                    results["message"] = f"上传失败，服务器响应: {resp}"
            except Exception as e:
                results["upload_status"] = "failed"
                results["message"] = f"上传错误: {e}"

        elif action == "download":
            local_path = f"downloaded_{os.path.basename(file)}"
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {file}", f.write)

            results["data"]["download_success"] = True
            results["data"]["local_path"] = local_path
            results["success"] = True
            results["message"] = f"文件下载成功: {local_path}"

        else:
            results["message"] = f"未知操作: {action}"

    except ConnectionRefusedError as e:
        results["message"] = f"连接被拒绝: {e}"
    except TimeoutError as e:
        results["message"] = f"连接超时: {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FTP客户端工具")
    parser.add_argument("--host", default="ftp.gnu.org", help="FTP服务器地址")
    parser.add_argument("--port", type=int, default=21, help="FTP端口，默认21")
    parser.add_argument("--action", choices=["list", "upload", "download"], 
                        default="list", help="操作类型")
    parser.add_argument("--file", default="test.txt", help="上传时的远程文件名/下载时的远程文件路径")
    parser.add_argument("--file_path", default="", help="上传时的本地文件路径")
    parser.add_argument("--remote_path", default="", help="上传时指定远程路径/文件名")
    parser.add_argument("--timeout", type=int, default=10, help="连接超时秒数")

    args = parser.parse_args()

    result = main(
        host=args.host,
        port=args.port,
        action=args.action,
        file=args.file,
        file_path=args.file_path,
        timeout=args.timeout,
        remote_path=args.remote_path
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))