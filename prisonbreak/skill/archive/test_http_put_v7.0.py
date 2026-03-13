"""skill/test_http_put.py - Test if HTTP server allows PUT method and attempt to upload a test file.

SKILL_META:
{
  "name": "test_http_put",
  "description": "Test if HTTP server allows PUT method and attempt to upload a test file.",
  "category": "http",
  "test_target": "已发现的HTTP服务器104.18.27.120:80",
  "test_args": "104.18.27.120 80 /test.txt 'baby test'",
  "version": "7.0"
}
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
import http.client
from typing import Any, Optional

def main(host: str, port: int = 80, path: str = '/test.txt', data: str = 'test',
         filename: str = None, retry: int = 3, timeout: float = 10.0,
         proxy: Optional[str] = None) -> dict[str, Any]:
    """Test if HTTP server allows PUT method and attempt to upload a test file."""
    result: dict[str, Any] = {"allowed": False, "response": "", "error": "", "success": False}

    content = data
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            result["error"] = f"File not found: {filename}, using command line data instead"
            content = data
        except PermissionError:
            result["error"] = f"Permission denied: {filename}, using command line data instead"
            content = data
        except Exception as e:
            result["error"] = f"Failed to read file: {e}, using command line data instead"
            content = data

    proxy = proxy or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")

    def attempt_upload() -> tuple[bool, str]:
        """Attempt a single PUT request, returns (success, response)."""
        try:
            if proxy:
                proxy_host, proxy_port = proxy.split(':')
                proxy_port = int(proxy_port)
                conn = http.client.HTTPConnection(proxy_host, proxy_port, timeout=timeout)
                conn.request("CONNECT", f"{host}:{port}")
                resp = conn.getresponse()
                if resp.status != 200:
                    return False, f"Proxy error: {resp.status} {resp.reason}"
                conn.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.sock.connect((proxy_host, proxy_port))
                conn.sock.sendall(f"CONNECT {host}:{port} HTTP/1.1\r\n\r\n".encode())
                tunnel_resp = b""
                while b"\r\n\r\n" not in tunnel_resp:
                    tunnel_resp += conn.sock.recv(1024)
            else:
                conn = http.client.HTTPConnection(host, port, timeout=timeout)

            headers = {"Content-Type": "text/plain", "Content-Length": str(len(content))}
            conn.request("PUT", path, content, headers)
            response = conn.getresponse()
            resp_text = f"{response.status} {response.reason}"
            response.read()
            conn.close()
            return (200 <= response.status < 300), resp_text
        except socket.timeout:
            return False, f"Connection timeout (no response within {timeout}s)"
        except ConnectionRefusedError:
            return False, "Connection refused"
        except OSError as e:
            err_lower = str(e).lower()
            if "timed out" in err_lower or "timeout" in err_lower:
                return False, f"Connection timeout: {str(e)}"
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, str(e)

    last_error = ""
    for attempt in range(retry):
        if attempt > 0:
            time.sleep(5)

        success, resp_text = attempt_upload()

        if success:
            result["allowed"] = True
            result["success"] = True
            result["response"] = resp_text
            return result
        else:
            last_error = resp_text
            if "Connection refused" in resp_text:
                result["error"] = f"Connection refused: {last_error}"
                break
            elif "timeout" in resp_text.lower():
                result["error"] = f"Timeout: {last_error}"
            else:
                result["error"] = f"Attempt {attempt + 1} failed: {last_error}"

    if not result["error"]:
        result["error"] = f"All {retry} attempts failed: {last_error}"

    return result

def parse_port(port_str: str) -> int:
    """Parse port string to int, handling ValueError."""
    try:
        port = int(port_str)
        if port <= 0 or port > 65535:
            raise argparse.ArgumentTypeError(f"Port must be between 1 and 65535, got {port}")
        return port
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port: {port_str}. Must be an integer.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test HTTP PUT method")
    parser.add_argument("host", nargs="?", default="104.18.27.120", help="HTTP server hostname or IP")
    parser.add_argument("port", type=parse_port, nargs="?", default=80, help="HTTP server port (default: 80)")
    parser.add_argument("path", nargs="?", default="/test.txt", help="Upload path (default: /test.txt)")
    parser.add_argument("data", nargs="?", default="baby test", help="Content to upload (default: baby test)")
    parser.add_argument("-f", "--filename", dest="filename", nargs="?", default=None,
                        const="", help="Read content from file instead of data argument")
    parser.add_argument("-r", "--retry", type=int, default=3, help="Number of retry attempts (default: 3)")
    parser.add_argument("-t", "--timeout", type=float, default=10.0, help="Request timeout in seconds (default: 10)")
    parser.add_argument("-p", "--proxy", dest="proxy", default=None, help="Proxy server (format: host:port)")

    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(1)

    filename = args.filename if args.filename else None

    result = main(args.host, args.port, args.path, args.data, filename,
                  args.retry, args.timeout, args.proxy)
    print(json.dumps(result, ensure_ascii=False, indent=2))