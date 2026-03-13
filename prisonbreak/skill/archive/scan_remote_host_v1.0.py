"""skill/scan_remote_host.py - Scan a remote host for open common ports and basic services.

SKILL_META:
{
  "name": "scan_remote_host",
  "description": "Scan a remote host for open common ports and basic services.",
  "category": "scan",
  "test_target": "Scan home public IP for open ports to understand external exposure.",
  "test_args": "151.242.36.181 [80, 443, 21]",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

PORT_SERVICE_MAP: dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns",
    80: "http", 110: "pop3", 143: "imap", 443: "https", 445: "smb",
    993: "imaps", 995: "pop3s", 3306: "mysql", 3389: "rdp",
    5432: "postgres", 8080: "http-proxy", 8443: "https-alt"
}

DEFAULT_PORTS: list[int] = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 993, 995, 3306, 3389, 5432, 8080, 8443]

def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open on the remote host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except socket.timeout:
        return False
    except socket.error:
        return False

def main(target_ip: str = "", ports: list[int] | None = None) -> dict[str, Any]:
    """Scan a remote host for open common ports and basic services."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    if not target_ip:
        results["message"] = "No target IP provided"
        return results

    scan_ports = ports if ports is not None else DEFAULT_PORTS
    open_ports: list[int] = []
    services: dict[int, str] = {}

    try:
        for port in scan_ports:
            if check_port(target_ip, port):
                open_ports.append(port)
                services[port] = PORT_SERVICE_MAP.get(port, "unknown")

        results["success"] = True
        results["message"] = "Scan completed"
        results["data"] = {
            "host": target_ip,
            "open_ports": open_ports,
            "services": services
        }
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

def parse_args(args: list[str]) -> tuple[str, list[int] | None]:
    """Parse command line arguments."""
    if not args:
        return "", None

    ip = args[0]
    port_list: list[int] | None = None

    if len(args) > 1:
        try:
            port_str = args[1].strip("[]")
            port_list = [int(p.strip()) for p in port_str.split(",")]
        except ValueError:
            port_list = None

    return ip, port_list

if __name__ == "__main__":
    ip, ports = parse_args(sys.argv[1:])
    output = main(ip, ports)
    print(json.dumps(output, ensure_ascii=False, indent=2))