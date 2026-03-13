"""skill/upload_ftp_anon_fixed.py - Attempt anonymous FTP login and upload a binary test file if possible.

SKILL_META:
{
  "name": "upload_ftp_anon_fixed",
  "description": "Attempt anonymous FTP login and upload a binary test file if possible.",
  "category": "ftp",
  "test_target": "209.51.188.20",
  "test_args": "209.51.188.20 b'Hello, this is a test file.' /tmp/test.txt",
  "version": "1.0"
}
"""
from __future__ import annotations

import ftplib
import json
import sys
from io import BytesIO
from typing import Any

def main(host: str, file_content: bytes, remote_path: str) -> dict[str, Any]:
    """Upload a binary file to an anonymous FTP server.

    Args:
        host: Target host IP or domain.
        file_content: Binary content to upload.
        remote_path: Remote file path on FTP server.

    Returns:
        dict with success status, message and data.
    """
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        ftp = ftplib.FTP(host)
        ftp.login()

        # Use BytesIO to handle binary data, fixing TypeError
        bio = BytesIO(file_content)
        cmd = f"STOR {remote_path}"
        ftp.storbinary(cmd, bio)

        ftp.quit()

        results["success"] = True
        results["message"] = "File uploaded successfully"
        results["data"] = {"host": host, "remote_path": remote_path}

    except ftplib.error_perm as e:
        results["message"] = f"Permission denied: {e}"
    except ftplib.error_temp as e:
        results["message"] = f"Temporary error: {e}"
    except ConnectionRefusedError as e:
        results["message"] = f"Connection refused: {e}"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        host_arg = sys.argv[1]
        content_arg = sys.argv[2]
        path_arg = sys.argv[3]

        # Parse bytes content from string like "b'Hello'"
        if content_arg.startswith("b'") and content_arg.endswith("'"):
            content = content_arg[2:-1].encode('utf-8')
        else:
            content = content_arg.encode('utf-8')

        result = main(host_arg, content, path_arg)
    else:
        result = {
            "success": False,
            "message": "Usage: python upload_ftp_anon_fixed.py <host> <content> <remote_path>",
            "data": {}
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))