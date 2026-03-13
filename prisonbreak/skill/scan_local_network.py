"""skill/scan_local_network.py - Scan local subnet for active hosts and common open ports.

SKILL_META:
{
  "name": "scan_local_network",
  "description": "Scan local subnet for active hosts and common open ports.",
  "category": "scan",
  "test_target": "Local subnet from get_local_info",
  "test_args": "192.168.1.0/24",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from ipaddress import ip_network
from typing import Any

COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3389, 8080, 8443]
TIMEOUT = 0.5

def ping_host(ip: str) -> bool:
    """Check if host is reachable via ping."""
    try:
        param = "-n" if sys.platform == "win32" else "-c"
        result = subprocess.run(
            ["ping", param, "1", "-W", "1", ip],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False

def scan_port(ip: str, port: int) -> bool:
    """Scan a single port on a host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except socket.error:
        return False

def check_host(ip: str) -> list[int]:
    """Check common ports on a host, return list of open ports."""
    open_ports: list[int] = []
    for port in COMMON_PORTS:
        if scan_port(ip, port):
            open_ports.append(port)
    return open_ports

def main(subnet: str) -> dict[str, Any]:
    """Scan local subnet for active hosts and open ports."""
    results: dict[str, Any] = {"success": False, "hosts": {}}
    try:
        network = ip_network(subnet, strict=False)
        for ip in network.hosts():
            ip_str = str(ip)
            if ping_host(ip_str):
                ports = check_host(ip_str)
                results["hosts"][ip_str] = {"ports": ports}
        results["success"] = True
    except ValueError as e:
        print(f"Invalid subnet: {e}", file=sys.stderr)
    except PermissionError as e:
        print(f"Permission denied: {e}", file=sys.stderr)
    except OSError as e:
        print(f"OS error: {e}", file=sys.stderr)
    return results

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.0/24"
    print(json.dumps(main(target), ensure_ascii=False, indent=2))