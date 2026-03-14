"""skill/remote_port_scanner.py - 一个简单的远程端口扫描工具，使用Python标准库（如socket模块）检查指定远程IP的端口是否开放，并返回端口状态和基本响应信息

SKILL_META:
{
  "name": "remote_port_scanner",
  "description": "一个简单的远程端口扫描工具，支持域名解析，检查指定远程IP的端口是否开放，并返回端口状态和基本响应信息",
  "category": "网络侦察",
  "test_target": "知名DNS服务器8.8.8.8的80和443端口，预期可能无开放端口，但工具应正确执行而不报TypeError；测试域名解析如example.com",
  "test_args": "--target example.com --ports 80,443",
  "version": "2.0"
}
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Any

def scan_port(target_ip: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    """扫描单个端口是否开放"""
    result: dict[str, Any] = {"port": port, "status": "closed", "banner": ""}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        connect_result = sock.connect_ex((target_ip, port))

        if connect_result == 0:
            result["status"] = "open"
            try:
                sock.settimeout(2.0)
                banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
                if banner:
                    result["banner"] = banner[:100]
            except Exception:
                pass
        sock.close()
    except socket.timeout:
        result["status"] = "timeout"
    except ConnectionRefusedError:
        result["status"] = "closed"
    except OSError as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result

def resolve_target(target: str) -> str:
    """解析域名或IP地址为IP"""
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as e:
        raise ValueError(f"域名解析失败: {target} - {e}")

def main(target: str, ports: str) -> dict[str, Any]:
    """扫描指定目标(IP或域名)的多个端口"""
    results: dict[str, Any] = {
        "success": False,
        "target": target,
        "resolved_ip": "",
        "open_ports": [],
        "error": None
    }
    try:
        resolved_ip = resolve_target(target)
        results["resolved_ip"] = resolved_ip
        print(f"Resolved {target} -> {resolved_ip}", file=sys.stderr)

        port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
        if not port_list:
            raise ValueError("端口列表为空或格式无效")

        for port in port_list:
            port_result = scan_port(resolved_ip, port)
            if port_result["status"] == "open":
                results["open_ports"].append(port_result)

        results["success"] = True
    except ValueError as e:
        results["error"] = f"参数错误: {e}"
    except socket.gaierror as e:
        results["error"] = f"域名解析失败: {e}"
    except Exception as e:
        results["error"] = f"扫描异常: {e}"
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="远程端口扫描工具")
    parser.add_argument(
        "--target",
        type=str,
        default="8.8.8.8",
        help="目标IP地址或域名"
    )
    parser.add_argument(
        "--ports",
        type=str,
        default="80,443",
        help="要扫描的端口，逗号分隔，如: 80,443,8080"
    )

    args = parser.parse_args()
    result = main(args.target, args.ports)
    print(json.dumps(result, ensure_ascii=False, indent=2))