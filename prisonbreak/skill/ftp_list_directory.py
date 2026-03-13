"""skill/ftp_list_directory.py - 匿名FTP连接并列出指定目录内容

SKILL_META:
{
  "name": "ftp_list_directory",
  "description": "匿名FTP连接并列出指定目录内容",
  "category": "ftp",
  "test_target": "209.51.188.20:21 /pub/ 目录内容",
  "test_args": "--host 209.51.188.20 --port 21 --path /pub/",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
from ftplib import FTP, error_perm, error_temp
from typing import Any

def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="列出FTP目录内容")
    parser.add_argument("--host", required=True, help="FTP服务器地址")
    parser.add_argument("--port", type=int, default=21, help="FTP服务器端口")
    parser.add_argument("--path", required=True, help="目录路径")
    return parser.parse_args(args)

def list_ftp_directory(host: str, port: int, path: str) -> list[str]:
    """连接FTP并列出目录内容（被动模式）"""
    ftp = FTP()
    ftp.set_pasv(True)  # 被动模式
    ftp.connect(host, port, timeout=30)
    ftp.login()  # 匿名登录
    ftp.cwd(path)
    files = ftp.nlst()
    ftp.quit()
    return files

def main(args: list[str] | None = None) -> dict[str, Any]:
    """主函数"""
    results: dict[str, Any] = {"success": False, "files": [], "message": ""}

    try:
        # 如果没有传入参数，使用命令行参数
        if args is None:
            args = sys.argv[1:]

        # 解析参数
        parsed = parse_args(args)

        # 执行FTP操作
        files: list[str] = list_ftp_directory(parsed.host, parsed.port, parsed.path)

        results["success"] = True
        results["files"] = files
        results["message"] = f"成功列出目录，共 {len(files)} 个文件"

    except SystemExit as e:
        # argparse 退出时返回错误码
        results["message"] = f"参数错误: {e.code}"
    except ConnectionRefusedError as e:
        results["message"] = f"连接被拒绝: {e}"
    except TimeoutError as e:
        results["message"] = f"连接超时: {e}"
    except error_perm as e:
        results["message"] = f"FTP权限错误: {e}"
    except error_temp as e:
        results["message"] = f"FTP临时错误: {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))