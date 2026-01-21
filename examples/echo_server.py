"""
Echo Server — listens on UDP port 9050, performs a 3-way handshake,
then receives a message and echoes it back to the client.

Run: python examples/echo_server.py
"""

import random
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.packet import Header, PType, packet_to_binary, HEADER_SIZE
from reliable_udp.manager import Connection


def build_packet(seq, ack, ptype, data=None):
    """Helper to build a packet with correct checksums."""
    hcs = Header.calculate_header_checksum(seq, ack, ptype)
    cs = Header.calculate_checksum(seq, ack, ptype, hcs, data)
    header = Header(seq, ack, ptype, hcs, cs)
    return packet_to_binary(header, data)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9050))
    print("Server listening on 0.0.0.0:9050 ...")

    # --- receive SYN ---
    data, addr = sock.recvfrom(1024)
    header = Header.parse(data[:HEADER_SIZE])

    if header.ptype != PType.SYN:
        print("Expected SYN packet, got something else")
        return
    if not header.verify_header_checksum() or not header.verify_checksum(None):
        print("Bad checksum on SYN")
        return

    seq = random.randint(0, 0xFFFFFFFF)
    conn = Connection(seq=seq, ack=header.seq + 1, previous_seq=seq)

    # --- send SYN-ACK ---
    pkt = build_packet(conn.seq, conn.ack, PType.SYN_ACK)
    sock.sendto(pkt, addr)
    conn.seq += 1

    # --- receive ACK ---
    data, addr = sock.recvfrom(1024)
    header = Header.parse(data[:HEADER_SIZE])

    if header.ptype != PType.ACK:
        print("Expected ACK packet")
        return
    if not header.verify_header_checksum() or not header.verify_checksum(None):
        print("Bad checksum on ACK")
        return
    if header.ack != conn.seq or header.seq != conn.ack:
        print("Seq/ack mismatch — packet needs to be resent")
        return

    conn.is_open = True
    print("Connection established")

    # --- receive PSH with data ---
    data, addr = sock.recvfrom(1024)
    header = Header.parse(data[:HEADER_SIZE])
    payload = data[HEADER_SIZE:]

    if header.ptype != PType.PSH:
        print("Expected PSH packet with data")
        return
    if not header.verify_header_checksum() or not header.verify_checksum(payload):
        print("Bad checksum on data packet")
        return
    if header.ack != conn.seq:
        print("Ack mismatch — packet needs to be resent")
        return

    conn.ack += len(payload)
    print(f"Received from the client: {payload.decode()!r}")

    # --- echo it back as PSH ---
    pkt = build_packet(conn.seq, conn.ack, PType.PSH, payload)
    sock.sendto(pkt, addr)
    conn.seq += len(payload)
    print("Message sent")


if __name__ == "__main__":
    main()
