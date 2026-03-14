"""skill/local_perceptor.py - 一个简单的感知工具，使用Python标准库获取本机公网IP（通过外部服务查询）、远程端口扫描（针对指定IP）和基本系统信息

SKILL_META:
{
  "name": "local_perceptor",
  "description": "一个简单的感知工具，使用Python标准库获取本机公网IP（通过外部服务查询）、远程端口扫描（针对指定IP）和基本系统信息",
  "category": "perception",
  "test_target": "运行后输出字典，确认IP匹配、列出远程开放端口，并显示系统信息",
  "test_args": "--target_ip 213.210.5.226 --ports 21,22,80,443,3389",
  "version": "4.0"
}
"""
from __future__ import annotations

import argparse
import json
import platform
import socket
import urllib.error
import urllib.request
from typing import Any

TIMEOUT = 2.0

def get_public_ip() -> str:
    """通过外部服务获取本机公网IP"""
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as response:
            return response.read().decode("utf-8")
    except (urllib.error.URLError, socket.error):
        return "Unknown"

def scan_remote_port(target_ip: str, port: int, timeout: float = TIMEOUT) -> dict[str, Any]:
    """扫描远程指定IP的单个端口，返回详细状态"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        return {"port": port, "ip": target_ip, "open": result == 0, "state": "open" if result == 0 else "closed"}
    except socket.timeout:
        return {"port": port, "ip": target_ip, "open": False, "state": "filtered", "error": "timeout"}
    except socket.error as e:
        return {"port": port, "ip": target_ip, "open": False, "state": "filtered", "error": str(e)}
    finally:
        if sock:
            sock.close()

def scan_remote_ports(target_ip: str, ports: list[int]) -> list[dict[str, Any]]:
    """扫描远程指定IP的多个端口，返回端口状态字典列表"""
    return [scan_remote_port(target_ip, port) for port in ports]

def get_local_info() -> dict[str, str]:
    """获取本地系统信息"""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python_version": platform.python_version(),
        "hostname": socket.gethostname()
    }

def main(target_ip: str, ports: list[int] | None = None) -> dict[str, Any]:
    """主函数：优先输出远程端口扫描结果，保留本地感知功能"""
    if ports is None:
        ports = [21, 22, 80, 443, 3389]

    # 远程端口扫描（优先）
    remote_scan = scan_remote_ports(target_ip, ports)
    open_ports = [p["port"] for p in remote_scan if p["open"]]

    # 本机公网IP
    public_ip = get_public_ip()

    # 本地系统信息
    local_info = get_local_info()

    return {
        "success": True,
        "remote_target": target_ip,
        "remote_scan": remote_scan,
        "open_ports": open_ports,
        "public_ip": public_ip,
        "ip_confirmed": public_ip == target_ip,
        "local_info": local_info
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="本地感知工具")
    parser.add_argument("--target_ip", type=str, default="8.8.8.8", help="远程目标IP")
    parser.add_argument("--ports", type=str, default="21,22,80,443,3389", help="要扫描的端口列表，用逗号分隔")
    args = parser.parse_args()

    port_list = [int(p.strip()) for p in args.ports.split(",")]
    result = main(args.target_ip, port_list)
    print(json.dumps(result, ensure_ascii=False, indent=2))