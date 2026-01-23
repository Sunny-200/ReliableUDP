"""
Echo Client — connects to the echo server on port 9050, sends "Echo me!",
and prints the server's response.

Run: python examples/echo_client.py
"""

import random
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.packet import Header, PType, packet_to_binary, HEADER_SIZE
from reliable_udp.manager import Connection

SERVER = ("127.0.0.1", 9050)


def build_packet(seq, ack, ptype, data=None):
    """Helper to build a packet with correct checksums."""
    hcs = Header.calculate_header_checksum(seq, ack, ptype)
    cs = Header.calculate_checksum(seq, ack, ptype, hcs, data)
    header = Header(seq, ack, ptype, hcs, cs)
    return packet_to_binary(header, data)


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 9040))

    # --- send SYN ---
    seq = random.randint(0, 0xFFFFFFFF)
    conn = Connection(seq=seq, ack=0, previous_seq=seq)

    pkt = build_packet(conn.seq, 0, PType.SYN)
    sock.sendto(pkt, SERVER)
    conn.seq += 1

    # --- receive SYN-ACK ---
    data, addr = sock.recvfrom(1024)
    header = Header.parse(data[:HEADER_SIZE])

    if header.ptype != PType.SYN_ACK:
        print("Expected SYN-ACK from server")
        return
    if not header.verify_header_checksum() or not header.verify_checksum(None):
        print("Bad checksum on SYN-ACK")
        return
    if header.ack != conn.seq:
        print("Ack mismatch — packet needs to be resent")
        return

    conn.ack = header.seq + 1
    conn.is_open = True

    # --- send ACK ---
    pkt = build_packet(conn.seq, conn.ack, PType.ACK)
    sock.sendto(pkt, SERVER)
    print("Connection established")

    # --- send PSH with data ---
    message = b"Echo me!"
    pkt = build_packet(conn.seq, conn.ack, PType.PSH, message)
    sock.sendto(pkt, SERVER)
    conn.seq += len(message)
    print("Message sent")

    # --- receive echoed PSH ---
    data, addr = sock.recvfrom(1024)
    header = Header.parse(data[:HEADER_SIZE])
    payload = data[HEADER_SIZE:]

    if header.ptype != PType.PSH:
        print("Expected PSH packet from server")
        return
    if not header.verify_header_checksum() or not header.verify_checksum(payload):
        print("Bad checksum on data packet")
        return
    if header.ack != conn.seq:
        print("Ack mismatch — packet needs to be resent")
        return

    print(f"Received from the server: {payload.decode()!r}")


if __name__ == "__main__":
    main()
