"""
Bulk Receiver — receives large data using the sliding window protocol.

Run this FIRST, then run bulk_sender.py in another terminal.
"""

import socket
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.transport import server_accept, recv_windowed


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9050))
    print("Receiver listening on 0.0.0.0:9050 ...")

    conn, addr = server_accept(sock)
    print("Connected")

    start = time.time()
    data = recv_windowed(sock, conn)
    elapsed = time.time() - start

    throughput = len(data) / elapsed / 1024
    print(f"Received {len(data)} bytes in {elapsed:.2f}s ({throughput:.1f} KB/s)")


if __name__ == "__main__":
    main()
