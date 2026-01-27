"""
Bulk Sender — sends 64 KB of data using the sliding window protocol.

Start bulk_receiver.py first, then run this.
"""

import socket
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.transport import client_connect, send_windowed

SERVER = ("127.0.0.1", 9050)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9040))

    conn = client_connect(sock, SERVER)
    print("Connected")

    # 64 KB of test data
    data = b"A" * (64 * 1024)
    print(f"Sending {len(data)} bytes with sliding window...")

    start = time.time()
    retransmits = send_windowed(sock, conn, SERVER, data)
    elapsed = time.time() - start

    throughput = len(data) / elapsed / 1024
    print(f"Done in {elapsed:.2f}s ({throughput:.1f} KB/s)")
    print(f"Retransmissions: {retransmits}")


if __name__ == "__main__":
    main()
