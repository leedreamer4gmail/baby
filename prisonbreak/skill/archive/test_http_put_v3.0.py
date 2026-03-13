"""skill/test_http_put.py - Test if HTTP server allows PUT method and attempt to upload a test file.

SKILL_META:
{
  "name": "test_http_put",
  "description": "Test if HTTP server allows PUT method and attempt to upload a test file.",
  "category": "http",
  "test_target": "已发现的HTTP服务器104.18.27.120:80",
  "test_args": "104.18.27.120 80 /test.txt 'baby test'",
  "version": "3.0"
}
"""
from __future__ import annotations

import argparse
import json
import sys
import http.client
from typing import Any

def main(host: str, port: int = 80, path: str = '/test.txt', data: str = 'test', filename: str = None) -> dict[str, Any]:
    """Test if HTTP server allows PUT method and attempt to upload a test file."""
    result: dict[str, Any] = {"allowed": False, "response": "", "error": "", "success": False}

    content = data
    if filename:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            result["error"] = f"Failed to read file: {e}"
            return result

    try:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        headers = {"Content-Type": "text/plain", "Content-Length": str(len(content))}
        conn.request("PUT", path, content, headers)
        response = conn.getresponse()
        result["response"] = f"{response.status} {response.reason}"

        if 200 <= response.status < 300:
            result["allowed"] = True
            result["success"] = True

        response.read()
        conn.close()

    except ConnectionRefusedError as e:
        result["error"] = f"Connection refused: {e}"
    except TimeoutError as e:
        result["error"] = f"Connection timeout: {e}"
    except Exception as e:
        result["error"] = f"Error: {e}"

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

    try:
        args = parser.parse_args()
    except SystemExit:
        sys.exit(1)

    # Handle -f with no value (const="") vs not provided (None)
    filename = args.filename if args.filename else None

    result = main(args.host, args.port, args.path, args.data, filename)
    print(json.dumps(result, ensure_ascii=False, indent=2))