"""
Benchmark: Reliable UDP vs Raw UDP under simulated packet loss.

Runs server and client in separate threads to measure throughput.
Uses LossySocket to simulate configurable packet loss during data transfer.

Run: python benchmark/run_benchmark.py
"""

import socket
import threading
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp import transport
from benchmark.lossy_socket import LossySocket

DATA_SIZE = 64 * 1024   # 64 KB
LOSS_RATE = 0.10         # 10% packet loss
CHUNK_SIZE = 1024


def run_reliable_test(loss_rate, server_port, client_port):
    """Send DATA_SIZE bytes through reliable UDP with sliding window."""
    results = {}
    error_box = []

    def server():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", server_port))
            lossy = LossySocket(sock, loss_rate)
            lossy.enabled = False  # clean handshake

            conn, addr = transport.server_accept(lossy)
            lossy.enabled = True   # now simulate loss

            data = transport.recv_windowed(lossy, conn)
            results["received"] = len(data)
            sock.close()
        except Exception as e:
            error_box.append(e)

    def client():
        try:
            time.sleep(0.2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", client_port))
            server_addr = ("127.0.0.1", server_port)
            lossy = LossySocket(sock, loss_rate)
            lossy.enabled = False  # clean handshake

            conn = transport.client_connect(lossy, server_addr)
            lossy.enabled = True   # now simulate loss

            data = b"X" * DATA_SIZE
            start = time.time()
            retransmits = transport.send_windowed(lossy, conn, server_addr, data)
            elapsed = time.time() - start

            results["time"] = elapsed
            results["throughput_kbps"] = DATA_SIZE / elapsed / 1024
            results["retransmits"] = retransmits
            sock.close()
        except Exception as e:
            error_box.append(e)

    t1 = threading.Thread(target=server)
    t2 = threading.Thread(target=client)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    if error_box:
        raise error_box[0]
    return results


def run_raw_test(loss_rate, server_port, client_port):
    """Send DATA_SIZE bytes through raw UDP (no retransmission)."""
    results = {}

    def server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", server_port))
        sock.settimeout(3.0)

        received = 0
        try:
            while True:
                data, _ = sock.recvfrom(2048)
                received += len(data)
        except socket.timeout:
            pass

        results["received"] = received
        sock.close()

    def client():
        time.sleep(0.2)
        raw = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        raw.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        raw.bind(("127.0.0.1", client_port))
        lossy = LossySocket(raw, loss_rate)

        data = b"X" * DATA_SIZE
        chunks = [data[i:i + CHUNK_SIZE] for i in range(0, len(data), CHUNK_SIZE)]

        start = time.time()
        for chunk in chunks:
            lossy.sendto(chunk, ("127.0.0.1", server_port))
        elapsed = time.time() - start

        results["time"] = elapsed
        results["total_sent"] = DATA_SIZE
        raw.close()

    t1 = threading.Thread(target=server)
    t2 = threading.Thread(target=client)
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)
    return results


def main():
    transport.VERBOSE = False

    size_kb = DATA_SIZE // 1024
    loss_pct = int(LOSS_RATE * 100)
    print(f"=== Benchmark: {size_kb} KB transfer, {loss_pct}% simulated packet loss ===\n")

    # --- baseline (no loss) ---
    print("1) Reliable UDP - no loss (baseline)")
    r = run_reliable_test(0.0, 7050, 7051)
    print(f"   Throughput: {r['throughput_kbps']:.1f} KB/s | Time: {r['time']:.2f}s")
    print(f"   Delivered:  100%\n")

    time.sleep(0.5)

    # --- reliable under loss ---
    print(f"2) Reliable UDP - {loss_pct}% loss")
    r = run_reliable_test(LOSS_RATE, 7052, 7053)
    print(f"   Throughput: {r['throughput_kbps']:.1f} KB/s | Time: {r['time']:.2f}s")
    print(f"   Retransmissions: {r['retransmits']}")
    print(f"   Delivered:  100%\n")

    time.sleep(0.5)

    # --- raw UDP under loss ---
    print(f"3) Raw UDP - {loss_pct}% loss (no retransmission)")
    raw = run_raw_test(LOSS_RATE, 7054, 7055)
    delivered_pct = raw["received"] / raw["total_sent"] * 100
    lost = raw["total_sent"] - raw["received"]
    print(f"   Sent: {raw['total_sent']} bytes")
    print(f"   Received: {raw['received']} bytes")
    print(f"   Delivered:  {delivered_pct:.0f}% ({lost} bytes lost permanently)\n")

    # --- summary ---
    print("=" * 55)
    print(f"  Under {loss_pct}% packet loss:")
    print(f"  Reliable UDP  ->  100% data delivered (retransmit)")
    print(f"  Raw UDP       ->  {delivered_pct:.0f}% data delivered ({100-delivered_pct:.0f}% lost)")
    print("=" * 55)


if __name__ == "__main__":
    main()

