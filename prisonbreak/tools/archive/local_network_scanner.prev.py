"""skill/local_network_scanner.py - 一个简单的本地网络扫描工具，使用Python标准库（如socket和ipaddress模块）扫描指定本地子网范围内的IP，检查常见端口是否开放，并返回发现的开放端口和主机信息

SKILL_META:
{
  "name": "local_network_scanner",
  "description": "一个简单的本地网络扫描工具，使用Python标准库（如socket和ipaddress模块）扫描指定本地子网范围内的IP，检查常见端口是否开放，并返回发现的开放端口和主机信息",
  "category": "网络侦察",
  "test_target": "本地网络子网192.168.1.0/24的80和443端口，预期可能发现路由器或其他设备的开放端口，但如果无则返回空open_hosts",
  "test_args": "--subnet 192.168.1.0/24 --ports 80,443 --timeout 1",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import socket
import ipaddress
from typing import Any

def check_port(ip: str, port: int, timeout: float) -> int | None:
    """检查单个端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return port if result == 0 else None
    except socket.error:
        return None

def scan_host(ip: str, ports: list[int], timeout: float) -> tuple[str, list[int]]:
    """扫描单个主机的多个端口"""
    open_ports = []
    for port in ports:
        if check_port(ip, port, timeout):
            open_ports.append(port)
    return ip, open_ports

def main(subnet: str = "192.168.1.0/24", ports: str = "21,22,80,443,3389", timeout: float = 1) -> dict[str, Any]:
    """扫描本地子网内的主机开放端口"""
    results: dict[str, Any] = {"success": False, "scanned_subnet": subnet, "open_hosts": {}}
    try:
        port_list = [int(p.strip()) for p in ports.split(",")]
        network = ipaddress.ip_network(subnet, strict=False)
        hosts = [str(ip) for ip in network.hosts()]
        for ip in hosts:
            _, open_ports = scan_host(ip, port_list, timeout)
            if open_ports:
                results["open_hosts"][ip] = sorted(open_ports)
        results["success"] = True
    except ValueError as e:
        results["message"] = f"参数错误: {e}"
    except OSError as e:
        results["message"] = f"网络错误: {e}"
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="本地网络扫描工具")
    parser.add_argument("--subnet", default="192.168.1.0/24", help="子网 CIDR 格式")
    parser.add_argument("--ports", default="21,22,80,443,3389", help="端口列表逗号分隔")
    parser.add_argument("--timeout", type=float, default=1, help="连接超时秒数")
    args = parser.parse_args()
    result = main(subnet=args.subnet, ports=args.ports, timeout=args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))