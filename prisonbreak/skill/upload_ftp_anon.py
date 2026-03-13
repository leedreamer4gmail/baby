"""skill/upload_ftp_anon.py - Attempt anonymous FTP login and upload a test file if possible.

SKILL_META:
{
  "name": "upload_ftp_anon",
  "description": "Attempt anonymous FTP login and upload a test file if possible.",
  "category": "ftp",
  "test_target": "Known Debian FTP IP to attempt upload after potential anon access.",
  "test_args": "151.101.2.132 21 /baby_test.txt 'hello from baby'",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import ftplib
import json
import os
import sys
from io import BytesIO
from typing import Any

def main(
    host: str,
    port: int = 21,
    remote_path: str = "/test.txt",
    content: str = "baby test",
    timeout: int = 30,
) -> dict[str, Any]:
    """Attempt anonymous FTP login and upload a test file."""
    result: dict[str, Any] = {"success": False, "message": "", "error": ""}
    ftp: ftplib.FTP | None = None

    try:
        # Input validation
        if not host or not isinstance(host, str):
            raise ValueError("Invalid host")
        if not (1 <= port <= 65535):
            raise ValueError(f"Invalid port: {port}")
        if not remote_path or not isinstance(remote_path, str):
            raise ValueError("Invalid remote_path")
        if not content and not os.path.isfile(content):
            raise ValueError("Invalid content or local file not found")

        # Determine content to upload
        upload_content: bytes
        if os.path.isfile(content):
            with open(content, "rb") as f:
                upload_content = f.read()
        elif isinstance(content, str):
            upload_content = content.encode("utf-8")
        else:
            raise ValueError("Content must be string or valid file path")

        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=timeout)
        # Anonymous login
        ftp.login()
        ftp.voidcmd("TYPE I")

        # Handle remote directory navigation
        remote_dir = "/".join(remote_path.split("/")[:-1])
        remote_file = remote_path.split("/")[-1]

        if remote_dir:
            try:
                ftp.cwd(remote_dir)
            except ftplib.error_perm:
                try:
                    ftp.mkd(remote_dir)
                    ftp.cwd(remote_dir)
                except ftplib.error_perm:
                    pass  # Try to store anyway

        # Upload file
        stor_cmd = f"STOR {remote_file}"
        bio = BytesIO(upload_content)
        ftp.storbinary(stor_cmd, bio)

        result["success"] = True
        result["message"] = f"Uploaded to {host}:{port}{remote_path}"

    except ValueError as e:
        result["error"] = f"Input error: {str(e)}"
    except ftplib.all_errors as e:
        result["error"] = f"FTP error: {str(e)}"
    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {str(e)}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {str(e)}"
    except OSError as e:
        result["error"] = f"OS error: {str(e)}"
    finally:
        if ftp:
            try:
                ftp.quit()
            except Exception:
                pass

    return result

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Attempt anonymous FTP login and upload a test file."
    )
    parser.add_argument("--host", type=str, default="151.101.2.132", help="FTP host")
    parser.add_argument("--port", type=int, default=21, help="FTP port")
    parser.add_argument(
        "--remote_path", type=str, default="/baby_test.txt", help="Remote file path"
    )
    parser.add_argument(
        "--content", type=str, default="hello from baby", help="Content or local file path"
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Connection timeout in seconds"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    result = main(
        host=args.host,
        port=args.port,
        remote_path=args.remote_path,
        content=args.content,
        timeout=args.timeout,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))