"""skill/upload_ftp_anon.py - Attempt anonymous FTP login and upload a test file if possible.

SKILL_META:
{
  "name": "upload_ftp_anon",
  "description": "Attempt anonymous FTP login and upload a test file if possible.",
  "category": "ftp",
  "test_target": "Known Debian FTP IP to attempt upload after potential anon access.",
  "test_args": "151.101.2.132 21 /baby_test.txt 'hello from baby'",
  "version": "1.0"
}
"""
from __future__ import annotations

import ftplib
import json
import sys
from io import StringIO
from typing import Any

def main(
    host: str,
    port: int = 21,
    remote_path: str = "/test.txt",
    content: str = "baby test"
) -> dict[str, Any]:
    """Attempt anonymous FTP login and upload a test file."""
    result: dict[str, Any] = {"success": False, "message": "", "error": ""}
    ftp: ftplib.FTP | None = None

    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=10)
        ftp.login()
        ftp.voidcmd("TYPE I")

        stor_cmd = f"STOR {remote_path}"
        bio = StringIO(content.encode("utf-8"))
        ftp.storbinary(stor_cmd, bio)

        result["success"] = True
        result["message"] = f"Uploaded to {host}:{port}{remote_path}"

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

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 1:
        h = args[0]
        p = int(args[1]) if len(args) > 1 else 21
        r = args[2] if len(args) > 2 else "/test.txt"
        c = args[3] if len(args) > 3 else "baby test"
        print(json.dumps(main(h, p, r, c), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(main("151.101.2.132", 21, "/baby_test.txt", "hello from baby"), ensure_ascii=False, indent=2))