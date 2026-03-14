"""skill/local_perceptor.py - 一个简单的感知工具，使用Python标准库获取本机公网IP（通过外部服务查询）、远程端口扫描（针对指定IP）和基本系统信息，支持banner抓取

SKILL_META:
{
  "name": "local_perceptor",
  "description": "一个简单的感知工具，使用Python标准库获取本机公网IP（通过外部服务查询）、远程端口扫描（针对指定IP）和基本系统信息，支持banner抓取",
  "category": "perception",
  "test_target": "运行后输出字典，自动探测并扫描本机公网IP的指定端口，确认public_ip字段非空、remote_scan字段存在",
  "test_args": "--ports 80,443,22",
  "version": "5.1"
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

def grab_banner(target_ip: str, port: int, timeout: float = TIMEOUT) -> str:
    """尝试抓取远程端口的banner信息"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((target_ip, port))
        try:
            sock.send(b"")  # 尝试触发响应
        except socket.error:
            pass
        banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
        return banner if banner else ""
    except Exception:
        return ""
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass

def scan_remote_port(target_ip: str, port: int, timeout: float = TIMEOUT) -> dict[str, Any]:
    """扫描远程指定IP的单个端口，返回详细状态（含banner抓取）"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        is_open = result == 0

        banner = ""
        if is_open:
            banner = grab_banner(target_ip, port, timeout)

        return {"port": port, "ip": target_ip, "open": is_open, "state": "open" if is_open else "closed", "banner": banner}
    except socket.timeout:
        return {"port": port, "ip": target_ip, "open": False, "state": "filtered", "error": "timeout", "banner": ""}
    except socket.error as e:
        return {"port": port, "ip": target_ip, "open": False, "state": "filtered", "error": str(e), "banner": ""}
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

def main(target_ip: str | None = None, ports: list[int] | None = None) -> dict[str, Any]:
    """主函数：优先输出远程端口扫描结果（含banner），保留本地感知功能。
    target_ip 为 None 时自动探测本机公网 IP，迁移到新服务器后无需更改参数。"""
    if ports is None:
        ports = [21, 22, 80, 443, 3389]

    # target_ip 未指定时自动使用本机公网 IP
    if target_ip is None:
        target_ip = get_public_ip()

    # 远程端口扫描（优先）
    remote_scan = scan_remote_ports(target_ip, ports)
    open_ports = [p["port"] for p in remote_scan if p["open"]]
    banners = {p["port"]: p["banner"] for p in remote_scan if p["open"] and p.get("banner")}

    # 本机公网IP
    public_ip = get_public_ip()

    # 本地系统信息
    local_info = get_local_info()

    return {
        "success": True,
        "remote_target": target_ip,
        "remote_scan": remote_scan,
        "open_ports": open_ports,
        "banners": banners,
        "public_ip": public_ip,
        "ip_confirmed": public_ip == target_ip,
        "local_info": local_info
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="本地感知工具")
    parser.add_argument("--target_ip", type=str, default=None, help="远程目标IP（留空则自动探测本机公网IP）")
    parser.add_argument("--ports", type=str, default="21,22,80,443,3389", help="要扫描的端口列表，用逗号分隔")
    args = parser.parse_args()

    port_list = [int(p.strip()) for p in args.ports.split(",")]
    result = main(args.target_ip, port_list)
    print(json.dumps(result, ensure_ascii=False, indent=2))