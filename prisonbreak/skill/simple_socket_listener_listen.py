"""skill/simple_socket_listener_listen.py - Listen on a local port for incoming socket connections and receive data.

SKILL_META:
{
  "name": "simple_socket_listener_listen",
  "description": "Listen on a local port for incoming socket connections and receive data.",
  "category": "listen",
  "test_target": "Localhost for initial test, simulate remote callback.",
  "test_args": "8080",
  "version": "1.0"
}
"""
from __future__ import annotations

import json
import socket
import sys
from typing import Any

BUFFER_SIZE = 4096
TIMEOUT_SECONDS = 5.0

def main(port: int) -> dict[str, Any]:
    """Listen on a local port for incoming socket connections and receive data.

    Args:
        port: Local port to listen on.

    Returns:
        Dictionary with success status, received data, and error message.
    """
    result: dict[str, Any] = {
        "success": False,
        "received_data": None,
        "error": None
    }

    server_socket: socket.socket | None = None
    client_socket: socket.socket | None = None

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', port))
        server_socket.listen(1)
        server_socket.settimeout(TIMEOUT_SECONDS)

        try:
            client_socket, client_address = server_socket.accept()
            data = client_socket.recv(BUFFER_SIZE)

            if data:
                result["received_data"] = data.decode('utf-8', errors='replace')
                result["success"] = True
            else:
                result["error"] = "No data received from client"

        except socket.timeout:
            result["error"] = f"Connection timeout after {TIMEOUT_SECONDS} seconds"
        except ConnectionResetError as e:
            result["error"] = f"Connection reset by peer: {e}"
        finally:
            if client_socket:
                client_socket.close()

    except OSError as e:
        result["error"] = f"Socket error: {e}"
    except ValueError as e:
        result["error"] = f"Invalid port: {e}"
    finally:
        if server_socket:
            server_socket.close()

    return result

if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8080

    result = main(port)
    print(json.dumps(result, ensure_ascii=False, indent=2))