"""skill/connect_ftp_anon.py - Attempt anonymous FTP connection to a host and list directory contents if successful.

SKILL_META:
{
  "name": "connect_ftp_anon",
  "description": "Attempt anonymous FTP connection to a host and list directory contents if successful.",
  "category": "ftp",
  "test_target": "One of ftp.debian.org IPs to test anonymous FTP access",
  "test_args": "151.101.66.132 21",
  "version": "1.0"
}
"""
from __future__ import annotations

import ftplib
import json
import socket
import sys
from typing import Any

def main(host: str = "", port: int = 21) -> dict[str, Any]:
    """Attempt anonymous FTP connection and list directory contents."""
    result: dict[str, Any] = {"success": "error", "message": "", "files": []}

    if not host:
        result["message"] = "Host is required"
        return result

    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=10)
        try:
            ftp.login()  # anonymous login
            try:
                files = ftp.nlst()
                result["success"] = "success"
                result["message"] = "Anonymous FTP access granted"
                result["files"] = files
            except ftplib.error_perm as e:
                result["message"] = f"Connected but cannot list files: {e}"
            finally:
                try:
                    ftp.quit()
                except Exception:
                    pass
        except ftplib.error_perm as e:
            result["message"] = f"Login failed: {e}"
            try:
                ftp.quit()
            except Exception:
                pass
    except ftplib.error_temp as e:
        result["message"] = f"Temporary FTP error: {e}"
    except ftplib.error_perm as e:
        result["message"] = f"Permanent FTP error: {e}"
    except ftplib.error_proto as e:
        result["message"] = f"FTP protocol error: {e}"
    except socket.timeout as e:
        result["message"] = f"Connection timeout: {e}"
    except socket.error as e:
        result["message"] = f"Socket error: {e}"
    except ConnectionRefusedError as e:
        result["message"] = f"Connection refused: {e}"
    except OSError as e:
        result["message"] = f"Network error: {e}"

    return result

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else ""
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 21

    result = main(host, port)
    print(json.dumps(result, ensure_ascii=False, indent=2))