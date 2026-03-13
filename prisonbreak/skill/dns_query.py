"""skill/dns_query.py - Query a DNS server to resolve a domain to IP addresses.

SKILL_META:
{
  "name": "dns_query",
  "description": "Query a DNS server to resolve a domain to IP addresses.",
  "category": "scan",
  "test_target": "Resolve example.com using Google's DNS to get IPs like 93.184.216.34",
  "test_args": "8.8.8.8 example.com",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import struct
import sys
from typing import Any

def build_dns_query(domain: str) -> bytes:
    """Build a DNS query packet for A record."""
    transaction_id = struct.pack("!H", 0x1234)
    flags = struct.pack("!H", 0x0100)
    counts = struct.pack("!HHHH", 1, 0, 0, 0)
    labels = b""
    for part in domain.split("."):
        labels += struct.pack("!B", len(part)) + part.encode("ascii")
    labels += b"\x00"
    query_type_class = struct.pack("!HH", 1, 1)
    return transaction_id + flags + counts + labels + query_type_class

def parse_dns_response(data: bytes) -> list[str]:
    """Parse DNS response to extract IP addresses."""
    ips: list[str] = []
    if len(data) < 12:
        return ips
    qd_count = struct.unpack("!H", data[4:6])[0]
    an_count = struct.unpack("!H", data[6:8])[0]
    offset = 12
    for _ in range(qd_count):
        while data[offset] != 0:
            offset += 1 + data[offset]
        offset += 5
    for _ in range(an_count):
        if data[offset] >= 0xC0:
            offset += 2
        else:
            while data[offset] != 0:
                offset += 1 + data[offset]
            offset += 1
        if offset + 10 > len(data):
            break
        rtype, rclass, ttl, rdlength = struct.unpack("!HHIH", data[offset:offset+10])
        offset += 10
        if rtype == 1 and rdlength == 4:
            ip = socket.inet_ntoa(data[offset:offset+4])
            ips.append(ip)
        offset += rdlength
    return ips

def main(dns_server: str, domain: str) -> dict[str, Any]:
    """Query a DNS server to resolve a domain to IP addresses."""
    result: dict[str, Any] = {"success": False, "resolved_ips": [], "error": ""}
    try:
        query = build_dns_query(domain)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        try:
            sock.sendto(query, (dns_server, 53))
            response, _ = sock.recvfrom(4096)
            ips = parse_dns_response(response)
            result["success"] = True
            result["resolved_ips"] = ips
        finally:
            sock.close()
    except socket.timeout:
        result["error"] = "DNS query timed out"
    except socket.gaierror as e:
        result["error"] = f"DNS server error: {e}"
    except OSError as e:
        result["error"] = f"Network error: {e}"
    return result

if __name__ == "__main__":
    if len(sys.argv) == 3:
        r = main(sys.argv[1], sys.argv[2])
    else:
        r = main("8.8.8.8", "example.com")
    print(json.dumps(r, ensure_ascii=False, indent=2))