"""skill/manual_dns_query.py - Manually query DNS server using socket to resolve domain without getaddrinfo.

SKILL_META:
{
  "name": "manual_dns_query",
  "description": "Manually query DNS server using socket to resolve domain without getaddrinfo.",
  "category": "scan",
  "test_target": "解析ftp.apache.org的IP作为新FTP渗透点",
  "test_args": "8.8.8.8 ftp.apache.org",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import struct
import sys
from typing import Any, List

def build_dns_query(domain: str) -> bytes:
    """Build DNS query packet for A record."""
    header = struct.pack("!HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)
    qname = b"".join(struct.pack("B", len(label)) + label.encode() for label in domain.split("."))
    qname += b"\x00"
    question = qname + struct.pack("!HH", 1, 1)
    return header + question

def parse_dns_response(data: bytes) -> List[str]:
    """Parse DNS response and extract IP addresses from A records."""
    ips: List[str] = []
    try:
        if len(data) < 12:
            return ips
        ancount = struct.unpack("!H", data[6:8])[0]
        pos = 12
        # skip question section qname
        while pos < len(data) and data[pos] != 0:
            pos += data[pos] + 1
        pos += 5  # skip the terminating zero and qtype/qclass
        for _ in range(ancount):
            if pos >= len(data):
                break
            # handle name pointer
            if data[pos] & 0xC0 == 0xC0:
                pos += 2
            else:
                while pos < len(data) and data[pos] != 0:
                    pos += data[pos] + 1
                pos += 1
            if pos + 10 > len(data):
                break
            qtype = struct.unpack("!H", data[pos:pos+2])[0]
            pos += 10  # skip type, class, TTL, rdlength
            rdlen = struct.unpack("!H", data[pos:pos+2])[0]
            pos += 2
            if qtype == 1 and rdlen == 4:
                ip = ".".join(str(b) for b in data[pos:pos+4])
                ips.append(ip)
            pos += rdlen
    except (struct.error, IndexError):
        pass
    return ips

def main(dns_server_ip: str | None = None, domain: str | None = None) -> dict[str, Any]:
    """Query DNS server using raw socket to resolve domain."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}
    try:
        # If arguments not provided, try to get them from command line
        if dns_server_ip is None or domain is None:
            if len(sys.argv) >= 3:
                dns_server_ip = sys.argv[1]
                domain = sys.argv[2]
            else:
                results["message"] = "Missing required arguments: dns_server_ip and domain"
                return results
        if not dns_server_ip or not domain:
            results["message"] = "Missing required arguments"
            return results
        if "." not in domain:
            results["message"] = "Invalid domain format"
            return results

        query = build_dns_query(domain)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        try:
            sock.sendto(query, (dns_server_ip, 53))
            response, _ = sock.recvfrom(512)
        finally:
            sock.close()

        ips = parse_dns_response(response)
        if ips:
            results["success"] = True
            results["message"] = "DNS query successful"
            results["data"] = {"domain": domain, "dns_server": dns_server_ip, "ips": ips}
        else:
            results["message"] = "No A records found"
    except socket.timeout:
        results["message"] = "DNS query timed out"
    except socket.gaierror as e:
        results["message"] = f"DNS server error: {e}"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    return results

if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))