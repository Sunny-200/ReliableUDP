"""
Echo Client — uses the reliable transport layer.
SYN and data packets are retransmitted if lost.

Run: python examples/echo_client.py
"""

import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.transport import client_connect, send_reliable, recv_reliable

SERVER = ("127.0.0.1", 9050)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9040))

    conn = client_connect(sock, SERVER)
    print("Connection established")

    send_reliable(sock, conn, SERVER, b"Echo me!")
    print("Message sent")

    payload, _ = recv_reliable(sock, conn)
    print(f"Received from server: {payload.decode()!r}")


if __name__ == "__main__":
    main()
