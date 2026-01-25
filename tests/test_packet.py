"""Tests for packet parsing, checksum calculation, and serialization."""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reliable_udp.packet import Header, PType, packet_to_binary, HEADER_SIZE
from reliable_udp.errors import TooSmallPacketError, TooBigPacketError, UnknownPTypeError


class TestChecksum(unittest.TestCase):
    def test_header_checksum_basic(self):
        # seq=0, ack=0, SYN -> should just be 1 (the ptype value)
        result = Header.calculate_header_checksum(0, 0, PType.SYN)
        self.assertEqual(result, 1)

    def test_full_checksum_with_data(self):
        hcs = Header.calculate_header_checksum(0, 0, PType.SYN)
        data = bytes([1, 2, 3, 4, 5])
        result = Header.calculate_checksum(0, 0, PType.SYN, hcs, data)
        self.assertEqual(result, 2312)

    def test_valid_checksums_pass_verification(self):
        hcs = Header.calculate_header_checksum(42, 99, PType.ACK)
        cs = Header.calculate_checksum(42, 99, PType.ACK, hcs, None)
        h = Header(42, 99, PType.ACK, hcs, cs)
        self.assertTrue(h.verify_header_checksum())
        self.assertTrue(h.verify_checksum(None))

    def test_bad_header_checksum_fails(self):
        h = Header(42, 99, PType.ACK, 0xBEEF, 0)
        self.assertFalse(h.verify_header_checksum())

    def test_bad_payload_checksum_fails(self):
        hcs = Header.calculate_header_checksum(42, 99, PType.PSH)
        h = Header(42, 99, PType.PSH, hcs, 0xDEAD)
        self.assertFalse(h.verify_checksum(b"data"))


class TestParsing(unittest.TestCase):
    def test_roundtrip(self):
        """Serialize a header, parse it back, check everything matches."""
        hcs = Header.calculate_header_checksum(100, 200, PType.PSH)
        cs = Header.calculate_checksum(100, 200, PType.PSH, hcs, b"hello")
        original = Header(100, 200, PType.PSH, hcs, cs)

        raw = packet_to_binary(original, b"hello")
        parsed = Header.parse(raw)

        self.assertEqual(parsed.seq, 100)
        self.assertEqual(parsed.ack, 200)
        self.assertEqual(parsed.ptype, PType.PSH)
        self.assertTrue(parsed.verify_header_checksum())
        self.assertTrue(parsed.verify_checksum(b"hello"))

    def test_too_small_raises(self):
        with self.assertRaises(TooSmallPacketError):
            Header.parse(b"\x00" * 10)

    def test_too_big_raises(self):
        with self.assertRaises(TooBigPacketError):
            Header.parse(b"\x00" * 70000)

    def test_unknown_ptype_raises(self):
        # 14 bytes with ptype byte (index 9) set to 99
        bad = b"\x00" * 9 + b"\x63" + b"\x00" * 4
        with self.assertRaises(UnknownPTypeError):
            Header.parse(bad)


class TestSerialization(unittest.TestCase):
    def test_header_only_length(self):
        hcs = Header.calculate_header_checksum(0, 0, PType.SYN)
        cs = Header.calculate_checksum(0, 0, PType.SYN, hcs, None)
        raw = packet_to_binary(Header(0, 0, PType.SYN, hcs, cs))
        self.assertEqual(len(raw), HEADER_SIZE)

    def test_with_payload_length(self):
        payload = b"test data"
        hcs = Header.calculate_header_checksum(1, 2, PType.PSH)
        cs = Header.calculate_checksum(1, 2, PType.PSH, hcs, payload)
        raw = packet_to_binary(Header(1, 2, PType.PSH, hcs, cs), payload)
        self.assertEqual(len(raw), HEADER_SIZE + len(payload))
        self.assertEqual(raw[HEADER_SIZE:], payload)


if __name__ == "__main__":
    unittest.main()
