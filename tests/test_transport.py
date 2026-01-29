"""Tests for the transport layer — packet building and integration."""

import socket
import threading
import time
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.packet import Header, PType, HEADER_SIZE
from reliable_udp import transport


class TestMakePacket(unittest.TestCase):
    def test_syn_packet(self):
        pkt = transport.make_packet(0, 0, PType.SYN)
        header = Header.parse(pkt[:HEADER_SIZE])
        self.assertEqual(header.ptype, PType.SYN)
        self.assertTrue(header.verify_header_checksum())

    def test_psh_with_data(self):
        pkt = transport.make_packet(10, 20, PType.PSH, b"hello")
        header = Header.parse(pkt[:HEADER_SIZE])
        payload = pkt[HEADER_SIZE:]
        self.assertEqual(payload, b"hello")
        self.assertTrue(header.verify_checksum(payload))


class TestHandshakeAndEcho(unittest.TestCase):
    """Integration test — runs server and client in threads."""

    def test_echo_roundtrip(self):
        transport.VERBOSE = False
        result = {}

        def server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 8070))

            conn, addr = transport.server_accept(sock)
            payload, _ = transport.recv_reliable(sock, conn)
            transport.send_reliable(sock, conn, addr, payload)
            result["echoed"] = payload
            sock.close()

        def client():
            time.sleep(0.1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 8071))

            conn = transport.client_connect(sock, ("127.0.0.1", 8070))
            transport.send_reliable(sock, conn, ("127.0.0.1", 8070), b"test123")
            payload, _ = transport.recv_reliable(sock, conn)
            result["received"] = payload
            sock.close()

        t1 = threading.Thread(target=server)
        t2 = threading.Thread(target=client)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(result["echoed"], b"test123")
        self.assertEqual(result["received"], b"test123")


class TestSlidingWindow(unittest.TestCase):
    """Integration test for bulk window transfer."""

    def test_bulk_transfer(self):
        transport.VERBOSE = False
        result = {}

        def server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 8072))

            conn, addr = transport.server_accept(sock)
            data = transport.recv_windowed(sock, conn)
            result["received"] = data
            sock.close()

        def client():
            time.sleep(0.1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 8073))

            conn = transport.client_connect(sock, ("127.0.0.1", 8072))
            test_data = b"B" * 8192  # 8 KB
            transport.send_windowed(sock, conn, ("127.0.0.1", 8072), test_data)
            result["sent"] = test_data
            sock.close()

        t1 = threading.Thread(target=server)
        t2 = threading.Thread(target=client)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        self.assertEqual(result["received"], result["sent"])


if __name__ == "__main__":
    unittest.main()
