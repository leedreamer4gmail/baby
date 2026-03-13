"""skill/http_enum_writable_dirs.py - 枚举HTTP服务器潜在writable目录，通过尝试PUT上传测试文件

SKILL_META:
{
  "name": "http_enum_writable_dirs",
  "description": "枚举HTTP服务器潜在writable目录，通过尝试PUT上传测试文件",
  "category": "http",
  "test_target": "209.51.188.20:80",
  "test_args": "--host 209.51.188.20 --port 80 --scheme http --paths /upload,/uploads,/files,/tmp,/pub,/admin,/api/upload,/upload.php,/upload.php,/fileupload,/webdav,/dav,/dav/upload,/uploads/files,/data,/storage,/app,/www,/htdocs,/var/www,/content,/media,/static,/assets,/images,/img,/pics,/photo,/uploads/images,/uploads/img,/pub/upload,/var/upload,/tmp/upload,/www/upload,/html/upload,/web/uploads,/site/uploads",
  "version": "4.0"
}
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import ssl
import sys
from typing import Any

from test_http_put import main as test_http_put_run

TEST_FILE = "._test_put_.txt"
TEST_CONTENT = b"test write"
DEFAULT_TIMEOUT = 10
DEFAULT_SCHEME = "http"

DEFAULT_PATHS = "/upload,/uploads,/files,/tmp,/pub,/admin,/api/upload,/upload.php,/upload.php,/fileupload,/webdav,/dav,/dav/upload,/uploads/files,/data,/storage,/app,/www,/htdocs,/var/www,/content,/media,/static,/assets,/images,/img,/pics,/photo,/uploads/images,/uploads/img,/pub/upload,/var/upload,/tmp/upload,/www/upload,/html/upload,/web/uploads,/site/uploads"

def check_webdav_support(host: str, port: int, path: str, use_ssl: bool) -> bool:
    """通过PROPFIND检查WebDAV支持"""
    try:
        if use_ssl:
            conn = http.client.HTTPSConnection(host, port, timeout=DEFAULT_TIMEOUT)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=DEFAULT_TIMEOUT)
        conn.request("PROPFIND", path, headers={"Depth": "0"})
        resp = conn.getresponse()
        conn.close()
        return resp.status in (207, 405)
    except (ssl.SSLError, ssl.CertificateError, socket.timeout, OSError):
        return False

def check_path(host: str, port: int, path: str, use_ssl: bool) -> dict[str, Any]:
    """检查单个路径"""
    result: dict[str, Any] = {"path": path, "writable": False, "clue": None}
    try:
        clean_path = path if path.startswith("/") else f"/{path}"
        if not clean_path.endswith("/"):
            clean_path += "/"
        test_url = clean_path + TEST_FILE

        if "webdav" in path.lower() or "dav" in path.lower():
            if not check_webdav_support(host, port, clean_path, use_ssl):
                result["clue"] = "WebDAV not supported"
                return result

        res = test_http_put_run(host=host, port=port, path=test_url, content=TEST_CONTENT)

        if res.get("success"):
            result["writable"] = res.get("data", {}).get("writable", False)
        elif not res.get("success"):
            status = res.get("status", 0)
            if status in (301, 302, 303, 307, 308):
                result["clue"] = f"Redirect ({status})"
            elif status == 403:
                result["clue"] = "Forbidden (403) - 可能可写"
            elif status == 404:
                result["clue"] = "Not Found"
    except socket.timeout:
        result["clue"] = "Timeout"
    except (ssl.SSLError, ssl.CertificateError) as e:
        result["clue"] = f"SSL Error: {e}"
    except OSError as e:
        result["clue"] = f"Network Error: {e}"
    except Exception as e:
        result["clue"] = f"Error: {e}"
    return result

def main(host: str | None = None, port: int | None = None, paths: str | None = None, scheme: str | None = None) -> dict[str, Any]:
    """枚举HTTP服务器潜在writable目录"""
    results: dict[str, Any] = {"success": False, "writable_dirs": [], "potential_dirs": [], "message": ""}

    # 只有当以脚本方式运行时才解析命令行参数
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="枚举HTTP服务器潜在writable目录")
        parser.add_argument("--host", required=True, help="目标主机IP")
        parser.add_argument("--port", type=int, default=None, help="目标端口")
        parser.add_argument("--scheme", default=DEFAULT_SCHEME, choices=["http", "https"], help="协议类型")
        parser.add_argument("--paths", default=DEFAULT_PATHS, help="逗号分隔的路径列表")
        args = parser.parse_args()
        host = args.host if host is None else host
        port = args.port if port is None else port
        scheme = args.scheme if scheme is None else scheme
        paths = args.paths if paths is None else paths

    if host is None:
        results["message"] = "参数错误: 需要 --host 参数"
        return results

    if port is None:
        port = 80

    if scheme is None:
        scheme = DEFAULT_SCHEME

    use_ssl = scheme.lower() == "https"
    if use_ssl and port == 80:
        port = 443

    try:
        if paths is None:
            paths = DEFAULT_PATHS
        path_list = [p.strip() for p in paths.split(",") if p.strip()]
        if not path_list:
            results["message"] = "paths不能为空"
            return results

        writable_dirs: list[str] = []
        potential_dirs: list[str] = []

        for path in path_list:
            check_result = check_path(host, port, path, use_ssl)
            if check_result.get("writable"):
                writable_dirs.append(path)
            elif check_result.get("clue") and ("403" in str(check_result.get("clue")) or "Redirect" in str(check_result.get("clue"))):
                potential_dirs.append(path)

        results["success"] = True
        results["writable_dirs"] = writable_dirs
        results["potential_dirs"] = potential_dirs
        results["message"] = f"扫描完成，发现 {len(writable_dirs)} 个可写目录，{len(potential_dirs)} 个潜在目录"
    except Exception as e:
        results["message"] = f"错误: {e}"
    return results

if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))