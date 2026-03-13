"""skill/manual_dns_resolve.py - Manually resolve domain via UDP DNS query to given server IP without getaddrinfo.

SKILL_META:
{
  "name": "manual_dns_resolve",
  "description": "Manually resolve domain via UDP DNS query to given server IP without getaddrinfo.",
  "category": "scan",
  "test_target": "解析ftp.apache.org的IP作为新FTP目标。",
  "test_args": "ftp.apache.org 8.8.8.8",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import struct
import sys
from typing import Any

def _encode_domain(domain: str) -> bytes:
    """Encode domain name into DNS format (labels)."""
    parts = domain.strip(".").split(".")
    return b"".join(len(p).to_bytes(1, "big") + p.encode() for p in parts) + b"\x00"

def _decode_domain(data: bytes, offset: int) -> tuple[str, int]:
    """Decode domain name from DNS response, return (domain, new_offset)."""
    parts: list[str] = []
    pos = offset
    while True:
        length = data[pos]
        if length == 0:
            return (".".join(parts) if parts else ".", pos + 1)
        if length >= 0xC0:
            pointer = struct.unpack("!H", data[pos:pos + 2])[0] & 0x3FFF
            suffix, _ = _decode_domain(data, pointer)
            return (".".join(parts) + "." + suffix if parts else suffix, pos + 2)
        parts.append(data[pos + 1:pos + 1 + length].decode())
        pos += 1 + length

def build_query(domain: str, tx_id: int = 0x1234) -> bytes:
    """Build DNS A query packet."""
    header = struct.pack(
        "!HHHHHH",
        tx_id,
        0x0100,
        1,
        0,
        0,
        0,
    )
    qname = _encode_domain(domain)
    qtype = struct.pack("!HH", 1, 1)
    return header + qname + qtype

def parse_response(data: bytes) -> list[str]:
    """Parse DNS response, return list of IPv4 addresses."""
    if len(data) < 12:
        raise ValueError("Response too short")

    ancount = struct.unpack("!H", data[6:8])[0]
    if ancount == 0:
        return []

    qname, pos = _decode_domain(data, 12)
    pos += 4

    ips: list[str] = []
    for _ in range(ancount):
        if pos + 10 > len(data):
            break
        atype, alen = struct.unpack("!HH", data[pos:pos + 4])
        pos += 4
        if atype == 1 and alen == 4:
            ip = ".".join(str(b) for b in data[pos:pos + 4])
            ips.append(ip)
        pos += alen

    return ips

def main(domain: str, dns_server_ip: str) -> dict[str, Any]:
    """Manually resolve domain via UDP DNS query to given server IP."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        if not domain or not dns_server_ip:
            results["message"] = "Usage: main(domain, dns_server_ip)"
            return results

        query = build_query(domain)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)

        try:
            sock.sendto(query, (dns_server_ip, 53))
            response, _ = sock.recvfrom(4096)
        finally:
            sock.close()

        ips = parse_response(response)

        if ips:
            results["success"] = True
            results["message"] = f"Resolved {domain} to {len(ips)} address(es)"
            results["data"] = {"domain": domain, "dns_server": dns_server_ip, "ips": ips}
        else:
            results["message"] = f"No A records found for {domain}"

    except socket.timeout:
        results["message"] = "DNS query timeout"
    except socket.gaierror as e:
        results["message"] = f"DNS server error: {e}"
    except struct.error as e:
        results["message"] = f"Packet parse error: {e}"
    except ValueError as e:
        results["message"] = f"Response error: {e}"
    except Exception as e:
        results["message"] = f"Unexpected error: {e}"

    return results

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        domain_arg = sys.argv[1]
        dns_arg = sys.argv[2]
    else:
        domain_arg = "ftp.apache.org"
        dns_arg = "8.8.8.8"

    result = main(domain_arg, dns_arg)
    print(json.dumps(result, ensure_ascii=False, indent=2))