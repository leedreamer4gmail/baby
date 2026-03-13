"""skill/query_dns_server.py - Query a DNS server for domain resolution.

SKILL_META:
{
  "name": "query_dns_server",
  "description": "Query a DNS server for domain resolution.",
  "category": "scan",
  "test_target": "Query DNS for example.com using discovered server 8.8.8.8",
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
    # Header: ID, flags, counts
    header = struct.pack("!HHHHHH", 1, 0x0100, 1, 0, 0, 0)
    # Question: convert domain to DNS format
    qname = b"".join(bytes([len(label)]) + label.encode() for label in domain.split(".")) + b"\x00"
    # QTYPE A (1), QCLASS IN (1)
    question = qname + struct.pack("!HH", 1, 1)
    return header + question

def parse_dns_response(data: bytes) -> list[str]:
    """Parse DNS response and extract A record IPs."""
    ips: list[str] = []
    if len(data) < 12:
        return ips

    # Parse header to get answer count
    _, _, _, _, _, ancount = struct.unpack("!HHHHHH", data[:12])

    # Skip to answer section
    pos = 12
    # Skip question section
    while pos < len(data) and data[pos] != 0:
        pos += data[pos] + 1
    pos += 5  # skip null byte + QTYPE + QCLASS

    # Parse answer records
    for _ in range(ancount):
        if pos + 12 > len(data):
            break
        # Check for name pointer
        if data[pos] & 0xC0 == 0xC0:
            pos += 2
        else:
            while pos < len(data) and data[pos] != 0:
                pos += data[pos] + 1
            pos += 1

        # Read TYPE, CLASS, TTL, RDLENGTH
        if pos + 10 > len(data):
            break
        rtype, _, _, rdlength = struct.unpack("!HHIH", data[pos:pos + 10])
        pos += 10

        # Extract IP if A record (type 1)
        if rtype == 1 and rdlength == 4 and pos + 4 <= len(data):
            ip = ".".join(str(b) for b in data[pos:pos + 4])
            ips.append(ip)
        pos += rdlength

    return ips

def main(dns_server_ip: str, domain_to_query: str) -> dict[str, Any]:
    """Query DNS server for domain resolution."""
    result: dict[str, Any] = {"success": False, "resolved_ips": [], "error": ""}
    try:
        query = build_dns_query(domain_to_query)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        sock.sendto(query, (dns_server_ip, 53))
        response, _ = sock.recvfrom(4096)
        sock.close()
        resolved = parse_dns_response(response)
        result["success"] = True
        result["resolved_ips"] = resolved
    except socket.timeout:
        result["error"] = "DNS query timed out"
    except socket.gaierror as e:
        result["error"] = f"Address error: {e}"
    except OSError as e:
        result["error"] = f"Network error: {e}"
    return result

if __name__ == "__main__":
    dns_server = "8.8.8.8"
    domain = "example.com"
    if len(sys.argv) >= 3:
        dns_server = sys.argv[1]
        domain = sys.argv[2]
    print(json.dumps(main(dns_server, domain), ensure_ascii=False, indent=2))