"""skill/enhanced_port_scanner.py - 一个简单的远程端口扫描工具，使用Python标准库（如socket模块）检查指定远程IP的端口是否开放，并尝试获取基本banner或响应信息，如果端口开放

SKILL_META:
{
  "name": "enhanced_port_scanner",
  "description": "一个简单的远程端口扫描工具，使用Python标准库（如socket模块）检查指定远程IP的端口是否开放，并尝试获取基本banner或响应信息，如果端口开放",
  "category": "网络侦察",
  "test_target": "知名DNS服务器8.8.8.8的80和443端口，预期可能无开放端口但工具应返回结构化输出而不报错",
  "test_args": "--target_ip 8.8.8.8 --ports 80,443 --timeout 5",
  "version": "1.0"
}
"""
from __future__ import annotations

import argparse
import json
import socket
from typing import Any

def scan_single_port(target_ip: str, port: int, timeout: float) -> dict[str, Any]:
    result: dict[str, Any] = {"port": port, "open": False, "banner": None}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        conn_result = sock.connect_ex((target_ip, port))
        if conn_result == 0:
            result["open"] = True
            try:
                sock.settimeout(2)
                banner = sock.recv(1024)
                if banner:
                    result["banner"] = banner.decode("utf-8", errors="ignore").strip()
            except socket.timeout:
                pass
    except socket.timeout:
        pass
    except ConnectionRefusedError:
        pass
    except OSError:
        pass
    finally:
        sock.close()
    return result

def main(target_ip: str, ports: str, timeout: float) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "open_ports": [], "error": ""}
    try:
        port_list = [int(p.strip()) for p in ports.split(",")]
        for port in port_list:
            scan_result = scan_single_port(target_ip, port, timeout)
            if scan_result["open"]:
                result["open_ports"].append({
                    "port": scan_result["port"],
                    "banner": scan_result["banner"]
                })
        result["success"] = True
    except ValueError as e:
        result["error"] = f"端口格式错误: {e}"
    except socket.gaierror as e:
        result["error"] = f"DNS解析错误: {e}"
    except Exception as e:
        result["error"] = f"扫描异常: {e}"
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="增强端口扫描器")
    parser.add_argument("--target_ip", default="8.8.8.8", help="目标IP地址")
    parser.add_argument("--ports", default="80,443", help="端口列表，逗号分隔")
    parser.add_argument("--timeout", type=float, default=5.0, help="连接超时时间(秒)")
    args = parser.parse_args()
    r = main(args.target_ip, args.ports, args.timeout)
    print(json.dumps(r, ensure_ascii=False, indent=2))