"""
Echo Server — now uses the reliable transport layer.
Handles retransmission automatically.

Run: python examples/echo_server.py
"""

import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.transport import server_accept, send_reliable, recv_reliable


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9050))
    print("Server listening on 0.0.0.0:9050 ...")

    conn, addr = server_accept(sock)
    print("Connection established")

    payload, _ = recv_reliable(sock, conn)
    print(f"Received from client: {payload.decode()!r}")

    send_reliable(sock, conn, addr, payload)
    print("Echoed back")


if __name__ == "__main__":
    main()
