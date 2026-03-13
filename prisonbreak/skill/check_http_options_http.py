"""skill/check_http_options_http.py - Send OPTIONS request to HTTP server and parse allowed methods with robust parameter handling.

SKILL_META:
{
  "name": "check_http_options_http",
  "description": "Send OPTIONS request to HTTP server and parse allowed methods with robust parameter handling.",
  "category": "http",
  "test_target": "209.51.188.20 HTTP server to check /pub for supported methods.",
  "test_args": "209.51.188.20:80/pub",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

def parse_target(target: str) -> tuple[str, int, str]:
    """Parse host:port/path into components."""
    if not target:
        raise ValueError("Target cannot be empty")

    if "/" in target:
        host_port, path = target.split("/", 1)
        path = "/" + path
    else:
        host_port = target
        path = "/"

    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port: {port_str}")
    else:
        host = host_port
        port = 80

    if not host:
        raise ValueError("Host cannot be empty")

    return host, port, path

def send_options_request(host: str, port: int, path: str) -> dict[str, Any]:
    """Send raw HTTP OPTIONS request using socket."""
    result: dict[str, Any] = {"raw": "", "headers": {}, "code": 0}

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))

        req = f"OPTIONS {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        sock.sendall(req.encode("utf-8"))

        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk

        sock.close()

        raw = data.decode("utf-8", errors="replace")
        result["raw"] = raw

        lines = raw.split("\r\n")
        if lines:
            parts = lines[0].split(" ", 2)
            if len(parts) >= 2:
                try:
                    result["code"] = int(parts[1])
                except ValueError:
                    pass

            for line in lines[1:]:
                if ":" in line:
                    k, v = line.split(":", 1)
                    result["headers"][k.strip()] = v.strip()

    except socket.timeout:
        result["error"] = "Connection timeout"
    except socket.error as e:
        result["error"] = f"Socket error: {e}"
    except Exception as e:
        result["error"] = f"Error: {e}"

    return result

def main(target: str = "example.com:80/pub") -> dict[str, Any]:
    """Send OPTIONS request to HTTP server and parse allowed methods."""
    results: dict[str, Any] = {"success": False, "message": "", "data": {}}

    try:
        host, port, path = parse_target(target)

        response = send_options_request(host, port, path)

        if "error" in response:
            results["message"] = response["error"]
            return results

        allow = response["headers"].get("Allow", "")
        code = response.get("code", 0)

        if allow:
            methods = [m.strip() for m in allow.split(",") if m.strip()]
            results["data"]["allowed_methods"] = methods
            results["data"]["status_code"] = code

            upload_set = {"PUT", "PATCH", "MKCOL", "PROPFIND"}
            found = [m for m in methods if m.upper() in upload_set]
            if found:
                results["data"]["upload_methods"] = found

            results["success"] = True
            results["message"] = "OPTIONS request completed"
        else:
            # When no Allow header, still consider success if we got a valid HTTP response
            results["data"]["status_code"] = code
            results["data"]["raw_response"] = response["raw"]
            if code > 0:
                results["success"] = True
                results["message"] = f"Received HTTP {code}, no Allow header"
            else:
                results["message"] = "No Allow header in response"

    except ValueError as e:
        results["message"] = f"Parameter error: {e}"
    except ConnectionError as e:
        results["message"] = f"Connection error: {e}"
    except OSError as e:
        results["message"] = f"Network error: {e}"
    except Exception as e:
        results["message"] = f"Unexpected error: {e}"

    return results

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "example.com:80/pub"
    print(json.dumps(main(target), ensure_ascii=False, indent=2))