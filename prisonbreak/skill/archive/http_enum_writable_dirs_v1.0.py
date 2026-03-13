"""skill/http_enum_writable_dirs.py - 枚举HTTP服务器潜在writable目录，通过尝试PUT上传测试文件

SKILL_META:
{
  "name": "http_enum_writable_dirs",
  "description": "枚举HTTP服务器潜在writable目录，通过尝试PUT上传测试文件",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "--host 209.51.188.20 --port 80 --paths /upload,/uploads,/files,/tmp,/pub,/admin,/api/upload.php,/upload.php,/fileupload,/webdav",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from test_http_put import main as test_http_put_run

TEST_FILE = "._test_put_.txt"
TEST_CONTENT = b"test write"

def main(host: str | None = None, port: int | None = None, paths: str | None = None) -> dict[str, Any]:
    """枚举HTTP服务器潜在writable目录

    Args:
        host: 目标主机IP
        port: 目标端口
        paths: 逗号分隔的路径列表

    Returns:
        包含success、writable_dirs和message的字典
    """
    results: dict[str, Any] = {"success": False, "writable_dirs": [], "message": ""}

    # 如果没有传入参数，尝试从命令行解析
    if host is None or port is None or paths is None:
        parser = argparse.ArgumentParser(description="枚举HTTP服务器潜在writable目录")
        parser.add_argument("--host", required=True, help="目标主机IP")
        parser.add_argument("--port", type=int, default=80, help="目标端口")
        parser.add_argument("--paths", required=True, help="逗号分隔的路径列表")

        try:
            args = parser.parse_args()
            host = args.host
            port = args.port
            paths = args.paths
        except SystemExit as e:
            results["message"] = f"参数错误: {e}"
            return results

    try:
        path_list = [p.strip() for p in paths.split(",") if p.strip()]
        if not path_list:
            results["message"] = "paths不能为空"
            return results

        writable_dirs: list[str] = []

        for path in path_list:
            try:
                test_path = f"{path}/{TEST_FILE}" if not path.endswith("/") else f"{path}{TEST_FILE}"
                res = test_http_put_run(host=host, port=port, path=test_path, content=TEST_CONTENT)
                if res.get("success") and res.get("data", {}).get("writable"):
                    writable_dirs.append(path)
            except Exception:
                continue

        results["success"] = True
        results["writable_dirs"] = writable_dirs
        results["message"] = f"扫描完成，发现 {len(writable_dirs)} 个可写目录"
    except Exception as e:
        results["message"] = f"错误: {e}"
    return results

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))