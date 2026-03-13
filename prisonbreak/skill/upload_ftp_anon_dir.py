"""skill/upload_ftp_anon_dir.py - Attempt anonymous FTP upload to specified directory with binary file.

SKILL_META:
{
  "name": "upload_ftp_anon_dir",
  "description": "Attempt anonymous FTP upload to specified directory with binary file.",
  "category": "ftp",
  "test_target": "IP 209.51.188.20 with /pub directory for upload test.",
  "test_args": "209.51.188.20 /pub test.bin b'test content'",
  "version": "1.0"
}
"""
from __future__ import annotations

import io
import json
import sys
from ftplib import FTP, error_perm, all_errors
from typing import Any

def upload_ftp_file(host: str, directory: str, filename: str, content: bytes) -> dict[str, Any]:
    """Upload file to FTP server anonymously."""
    result: dict[str, Any] = {
        "success": False,
        "message": "",
        "host": host,
        "directory": directory,
        "filename": filename,
    }
    ftp: FTP | None = None
    try:
        ftp = FTP(host)
        ftp.login()
        try:
            ftp.cwd(directory)
        except error_perm as e:
            result["message"] = f"Directory permission error: {e}"
            return result
        except all_errors as e:
            result["message"] = f"Cannot access directory {directory}: {e}"
            return result
        try:
            bio = io.BytesIO(content)
            ftp.storbinary(f"STOR {filename}", bio)
            result["success"] = True
            result["message"] = "Upload successful"
        except error_perm as e:
            result["message"] = f"Upload permission denied: {e}"
        except all_errors as e:
            result["message"] = f"Upload failed: {e}"
    except all_errors as e:
        result["message"] = f"Connection failed: {e}"
    finally:
        if ftp:
            try:
                ftp.quit()
            except all_errors:
                try:
                    ftp.close()
                except all_errors:
                    pass
    return result

def main(host: str, directory: str, filename: str, file_content: bytes) -> dict[str, Any]:
    """Upload a binary file to FTP server anonymously."""
    return upload_ftp_file(host, directory, filename, file_content)

if __name__ == "__main__":
    if len(sys.argv) >= 5:
        h, d, f = sys.argv[1], sys.argv[2], sys.argv[3]
        c = sys.argv[4].encode("utf-8")
    else:
        h, d, f = "209.51.188.20", "/pub", "test.bin"
        c = b"test content"
    r = main(h, d, f, c)
    print(json.dumps(r, ensure_ascii=False, indent=2))