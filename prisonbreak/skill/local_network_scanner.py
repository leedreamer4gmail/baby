"""skill/local_network_scanner.py - 一个简单的本地网络扫描工具，使用Python标准库（如socket和ipaddress模块）扫描指定本地子网范围内的IP，检查常见端口是否开放，并返回发现的开放端口和主机信息

SKILL_META:
{
  "name": "local_network_scanner",
  "description": "一个简单的本地网络扫描工具，使用Python标准库（如socket和ipaddress模块）扫描指定本地子网范围内的IP，检查常见端口是否开放，并返回发现的开放端口和主机信息。subnet留空则自动探测本机所在子网",
  "category": "网络侦察",
  "test_target": "自动探测本机所在子网并扫描80和443端口，预期可能发现局域网内设备的开放端口，无发现则返回空open_hosts",
  "test_args": "--ports 80,443 --timeout 1",
  "version": "2.1"
}
"""
from __future__ import annotations

import argparse
import json
import socket
import ipaddress
import threading
from typing import Any
from queue import Queue


def get_local_subnet() -> str:
    """探测本机所在局域网子网（/24），用于云服务器等 192.168 以外的网络环境。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        parts = local_ip.rsplit(".", 1)
        return f"{parts[0]}.0/24"
    except OSError:
        return "192.168.1.0/24"

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

def worker(ip_queue: Queue, results: dict, ports: list[int], timeout: float, lock: threading.Lock):
    """工作线程函数"""
    while True:
        try:
            ip = ip_queue.get_nowait()
        except:
            break
        _, open_ports = scan_host(ip, ports, timeout)
        if open_ports:
            with lock:
                results[ip] = sorted(open_ports)
        ip_queue.task_done()

def main(subnet: str | None = None, ports: str = "21,22,80,443,3389",
         timeout: float = 3, start_ip: str = None, end_ip: str = None,
         workers: int = 20) -> dict[str, Any]:
    """扫描本地子网内的主机开放端口

    Args:
        subnet: CIDR格式子网 (如 192.168.1.0/24)，留空则自动探测本机所在子网
        ports: 逗号分隔的端口列表
        timeout: 连接超时秒数
        start_ip: 起始IP (可选，优先级高于subnet)
        end_ip: 结束IP (可选)
        workers: 并行工作线程数
    """
    if subnet is None:
        subnet = get_local_subnet()
    results: dict[str, Any] = {"success": False, "scanned_subnet": subnet, "open_hosts": {}}
    try:
        port_list = [int(p.strip()) for p in ports.split(",")]

        # 确定扫描的IP列表
        if start_ip and end_ip:
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            ips = [str(ipaddress.ip_address(i)) for i in range(int(start), int(end) + 1)]
        else:
            network = ipaddress.ip_network(subnet, strict=False)
            ips = [str(ip) for ip in network.hosts()]

        # 多线程扫描
        ip_queue = Queue()
        for ip in ips:
            ip_queue.put(ip)

        results_dict: dict = {}
        lock = threading.Lock()
        threads = []

        for _ in range(min(workers, len(ips))):
            t = threading.Thread(target=worker, args=(ip_queue, results_dict, port_list, timeout, lock))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        results["open_hosts"] = results_dict
        results["success"] = True
    except ValueError as e:
        results["message"] = f"参数错误: {e}"
    except OSError as e:
        results["message"] = f"网络错误: {e}"
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="本地网络扫描工具")
    parser.add_argument("--subnet", default=None, help="子网 CIDR 格式（留空则自动探测本机所在子网）")
    parser.add_argument("--ports", default="21,22,80,443,3389", help="端口列表逗号分隔")
    parser.add_argument("--timeout", type=float, default=3, help="连接超时秒数")
    parser.add_argument("--start-ip", help="起始IP (可选)")
    parser.add_argument("--end-ip", help="结束IP (可选)")
    parser.add_argument("--workers", type=int, default=20, help="并行工作线程数")
    args = parser.parse_args()
    result = main(subnet=args.subnet, ports=args.ports, timeout=args.timeout,
                  start_ip=args.start_ip, end_ip=args.end_ip, workers=args.workers)
    print(json.dumps(result, ensure_ascii=False, indent=2))