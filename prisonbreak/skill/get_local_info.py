"""skill/get_local_info.py - Gather local system and network information.

SKILL_META:
{
  "name": "get_local_info",
  "description": "Gather local system and network information.",
  "category": "local",
  "test_target": "localhost",
  "test_args": "无",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
import platform
import http.client
from typing import Any

def get_local_ip() -> str:
    """Get local IP address by connecting to external host."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(3)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_public_ip() -> str:
    """Get public IP address via HTTP request."""
    hosts = ["icanhazip.com", "ifconfig.me", "ipinfo.io/ip"]
    for host in hosts:
        try:
            conn = http.client.HTTPConnection(host, timeout=5)
            conn.request("GET", "/")
            response = conn.getresponse()
            if response.status == 200:
                public_ip = response.read().decode().strip()
                conn.close()
                return public_ip
            conn.close()
        except Exception:
            continue
    return "unavailable"

def get_os_info() -> str:
    """Get operating system information."""
    try:
        return platform.platform()
    except Exception:
        return "unknown"

def get_python_version() -> str:
    """Get Python version."""
    return platform.python_version()

def main(无=None) -> dict[str, Any]:
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        results["data"] = {
            "ip": get_local_ip(),
            "public_ip": get_public_ip(),
            "os": get_os_info(),
            "python_version": get_python_version(),
        }
        results["success"] = True
        results["message"] = "完成"
    except socket.error as e:
        results["message"] = f"Socket error: {e}"
    except OSError as e:
        results["message"] = f"OS error: {e}"
    except Exception as e:
        results["message"] = f"Error: {e}"
    return results

if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))