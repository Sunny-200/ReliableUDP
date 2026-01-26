"""
Reliable transport layer — retransmission, handshake helpers, sliding window.
Built on top of our custom packet format.
"""

import socket
import random
from .packet import Header, PType, packet_to_binary, HEADER_SIZE
from .manager import Connection

# tunable defaults
TIMEOUT = 0.5
WINDOW_TIMEOUT = 0.1   # shorter timeout for window ACKs
MAX_RETRIES = 5
WINDOW_SIZE = 8
CHUNK_SIZE = 1024

VERBOSE = True


def _safe_recvfrom(sock, bufsize=65535):
    """
    Wrapper for recvfrom that handles Windows-specific 10054 errors.
    Treats them as a no-data event (raises timeout if timeout is set).
    """
    try:
        return sock.recvfrom(bufsize)
    except ConnectionResetError:
        # On Windows, this means an ICMP Port Unreachable was received.
        # We'll raise timeout so the retry logic kicks in naturally.
        raise socket.timeout()


def make_packet(seq, ack, ptype, data=None):
    """Build a packet with correct checksums."""
    hcs = Header.calculate_header_checksum(seq, ack, ptype)
    cs = Header.calculate_checksum(seq, ack, ptype, hcs, data)
    return packet_to_binary(Header(seq, ack, ptype, hcs, cs), data)


def send_with_retry(sock, pkt, addr, timeout=TIMEOUT, retries=MAX_RETRIES):
    """Send packet, wait for reply. Retransmit on timeout.
    Returns (response_bytes, sender_addr) or raises TimeoutError.
    """
    for attempt in range(retries):
        sock.sendto(pkt, addr)
        sock.settimeout(timeout)
        try:
            data, recv_addr = _safe_recvfrom(sock)
            sock.settimeout(None)
            return data, recv_addr
        except socket.timeout:
            if VERBOSE and attempt < retries - 1:
                print(f"  timeout/retry ({attempt + 2}/{retries})")

    sock.settimeout(None)
    raise TimeoutError(f"no response after {retries} attempts")


# ---- handshake ----

def client_connect(sock, server_addr):
    """Client-side 3-way handshake. SYN is retransmitted if lost."""
    seq = random.randint(0, 0xFFFFFFFF)
    conn = Connection(seq=seq, ack=0, previous_seq=seq)

    # SYN -> wait for SYN-ACK
    syn = make_packet(conn.seq, 0, PType.SYN)
    resp, _ = send_with_retry(sock, syn, server_addr)
    header = Header.parse(resp[:HEADER_SIZE])

    if header.ptype != PType.SYN_ACK:
        raise ConnectionError("expected SYN-ACK")
    if not header.verify_header_checksum():
        raise ConnectionError("bad checksum on SYN-ACK")

    conn.seq += 1
    conn.ack = header.seq + 1

    # send ACK
    ack_pkt = make_packet(conn.seq, conn.ack, PType.ACK)
    sock.sendto(ack_pkt, server_addr)
    conn.is_open = True
    return conn


def server_accept(sock):
    """Server-side: wait for a client, do the handshake. Returns (conn, addr)."""
    data, addr = _safe_recvfrom(sock)
    header = Header.parse(data[:HEADER_SIZE])

    if header.ptype != PType.SYN:
        raise ConnectionError("expected SYN")
    if not header.verify_header_checksum():
        raise ConnectionError("bad checksum on SYN")

    seq = random.randint(0, 0xFFFFFFFF)
    conn = Connection(seq=seq, ack=header.seq + 1, previous_seq=seq)

    # SYN-ACK
    synack = make_packet(conn.seq, conn.ack, PType.SYN_ACK)
    sock.sendto(synack, addr)
    conn.seq += 1

    # wait for ACK
    data, addr = _safe_recvfrom(sock)
    header = Header.parse(data[:HEADER_SIZE])

    if header.ptype != PType.ACK:
        raise ConnectionError("expected ACK")
    if header.ack != conn.seq or header.seq != conn.ack:
        raise ConnectionError("seq/ack mismatch in ACK")

    conn.is_open = True
    return conn, addr


# ---- reliable send/recv (stop-and-wait ARQ) ----

def send_reliable(sock, conn, addr, data):
    """Send data and wait for ACK. Retransmits automatically."""
    pkt = make_packet(conn.seq, conn.ack, PType.PSH, data)
    resp, _ = send_with_retry(sock, pkt, addr)

    header = Header.parse(resp[:HEADER_SIZE])
    if header.ptype != PType.ACK:
        raise ConnectionError("expected ACK for data")

    conn.seq += len(data)


def recv_reliable(sock, conn):
    """Receive data and auto-send ACK. Returns (payload, addr)."""
    data, addr = _safe_recvfrom(sock)
    header = Header.parse(data[:HEADER_SIZE])
    payload = data[HEADER_SIZE:]

    if header.ptype != PType.PSH:
        raise ConnectionError(f"expected PSH, got {header.ptype.name}")
    if not header.verify_header_checksum() or not header.verify_checksum(payload):
        raise ConnectionError("bad checksum on data")

    conn.ack += len(payload)

    ack_pkt = make_packet(conn.seq, conn.ack, PType.ACK)
    sock.sendto(ack_pkt, addr)
    return payload, addr


# ---- sliding window (Go-Back-N) ----

def send_windowed(sock, conn, addr, data, chunk_size=CHUNK_SIZE, window_size=WINDOW_SIZE):
    """Send bulk data using Go-Back-N sliding window.

    First sends the chunk count so the receiver knows what to expect,
    then pipelines chunks using seq field as the chunk index.
    Returns the number of retransmissions that happened.
    """
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    total = len(chunks)

    # tell receiver how many chunks are coming
    count_bytes = total.to_bytes(4, "big")
    send_reliable(sock, conn, addr, count_bytes)

    base = 0           # oldest un-ACKed chunk
    next_to_send = 0   # next chunk to put on the wire
    retransmits = 0

    while base < total:
        # fill the window
        while next_to_send < min(base + window_size, total):
            pkt = make_packet(next_to_send, conn.ack, PType.PSH, chunks[next_to_send])
            sock.sendto(pkt, addr)
            next_to_send += 1

        # collect ACKs until timeout
        sock.settimeout(WINDOW_TIMEOUT)
        try:
            while base < next_to_send:
                resp, _ = _safe_recvfrom(sock)
                header = Header.parse(resp[:HEADER_SIZE])
                if header.ptype == PType.ACK and header.ack > base:
                    base = header.ack
        except socket.timeout:
            if base < next_to_send:
                # Go-Back-N: retransmit from base
                next_to_send = base
                retransmits += 1

    sock.settimeout(None)
    conn.seq += len(data)
    return retransmits


def recv_windowed(sock, conn):
    """Receive bulk data from a sliding window sender. Returns the full bytes."""
    # first get chunk count
    count_data, addr = recv_reliable(sock, conn)
    total = int.from_bytes(count_data, "big")

    expected = 0    # next chunk we need
    received = {}   # buffer for chunks that arrive

    while expected < total:
        sock.settimeout(2.0)
        try:
            data, addr = _safe_recvfrom(sock)
            header = Header.parse(data[:HEADER_SIZE])
            payload = data[HEADER_SIZE:]

            if header.ptype == PType.PSH and header.verify_checksum(payload):
                chunk_idx = header.seq

                if chunk_idx == expected:
                    received[chunk_idx] = payload
                    expected += 1
                    # advance past any consecutive buffered chunks
                    while expected in received:
                        expected += 1
                elif chunk_idx > expected:
                    received[chunk_idx] = payload  # buffer it

            # cumulative ACK — "I need chunk #expected next"
            ack_pkt = make_packet(conn.seq, expected, PType.ACK)
            sock.sendto(ack_pkt, addr)

        except socket.timeout:
            ack_pkt = make_packet(conn.seq, expected, PType.ACK)
            sock.sendto(ack_pkt, addr)

    sock.settimeout(None)

    result = b"".join(received[i] for i in range(total))
    conn.ack += len(result)
    return result
