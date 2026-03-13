"""skill/scan_remote_host.py - Scan a remote host for open common ports and basic services.

SKILL_META:
{
  "name": "scan_remote_host",
  "description": "Scan a remote host for open common ports and basic services.",
  "category": "scan",
  "test_target": "Scan home public IP for open ports to understand external exposure.",
  "test_args": "151.242.36.181 [80, 443, 21]",
  "version": "3.0"
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

def check_port(host: str, port: int, timeout: float = 2.0, retries: int = 1) -> bool:
    """Check if a port is open on the remote host with retry support."""
    for attempt in range(retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except (socket.timeout, socket.error, OSError):
            if attempt == retries:
                return False
    return False

def parse_ports(port_str: str) -> list[int] | None:
    """Parse port string into list of integers."""
    if not port_str:
        return None
    cleaned = port_str.strip("[]").strip()
    if not cleaned:
        return None
    try:
        return [int(p.strip()) for p in cleaned.split(",") if p.strip()]
    except ValueError:
        return None

def parse_args(args: list[str]) -> tuple[str, list[int] | None, float, int]:
    """Parse command line arguments manually."""
    host = ""
    ports = None
    timeout = 2.0
    retries = 1

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("-p", "--ports"):
            if i + 1 < len(args):
                ports = parse_ports(args[i + 1])
                i += 2
            else:
                i += 1
        elif arg in ("-t", "--timeout"):
            if i + 1 < len(args):
                timeout = float(args[i + 1])
                i += 2
            else:
                i += 1
        elif arg in ("-r", "--retries"):
            if i + 1 < len(args):
                retries = int(args[i + 1])
                i += 2
            else:
                i += 1
        elif not arg.startswith("-") and not host:
            host = arg
            i += 1
        else:
            i += 1

    return host, ports, timeout, retries

def main(target_ip: str = "", ports: list[int] | None = None, timeout: float = 2.0, retries: int = 1) -> dict[str, Any]:
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
            if check_port(target_ip, port, timeout=timeout, retries=retries):
                open_ports.append(port)
                services[port] = PORT_SERVICE_MAP.get(port, "unknown")

        results["success"] = True
        results["message"] = f"Scan completed: {len(open_ports)} open port(s) found"
        results["data"] = {
            "host": target_ip,
            "open_ports": open_ports,
            "services": services,
            "scanned_count": len(scan_ports)
        }
    except Exception as e:
        results["message"] = f"Error: {e}"

    return results

if __name__ == "__main__":
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    host, ports, timeout, retries = parse_args(args)
    output = main(host, ports, timeout, retries)
    print(json.dumps(output, ensure_ascii=False, indent=2))