"""
Packet header format (14 bytes):
  [0:4]   seq             - u32 big-endian
  [4:8]   ack             - u32 big-endian
  [8]     padding         - always 0
  [9]     ptype           - packet type
  [10:12] header_checksum - u16 big-endian
  [12:14] checksum        - u16 big-endian
  [14:]   payload data
"""

import struct
from enum import IntEnum

HEADER_SIZE = 14
MAX_PACKET_SIZE = 65507

# format: big-endian, 2x uint32, 2x uint8, 2x uint16
HEADER_FORMAT = struct.Struct(">IIBBHH")


class PType(IntEnum):
    SYN = 1
    SYN_ACK = 2
    ACK = 3
    PSH = 4
    FIN = 5


class Header:
    def __init__(self, seq, ack, ptype, header_checksum, checksum):
        self.seq = seq
        self.ack = ack
        self.ptype = ptype
        self.header_checksum = header_checksum
        self.checksum = checksum

    @classmethod
    def parse(cls, data):
        """Parse raw bytes into a Header object."""
        from .errors import TooSmallPacketError, TooBigPacketError, UnknownPTypeError

        if len(data) < HEADER_SIZE:
            raise TooSmallPacketError()
        if len(data) > MAX_PACKET_SIZE:
            raise TooBigPacketError(len(data))

        seq, ack, _, ptype_val, hcs, cs = HEADER_FORMAT.unpack_from(data)

        try:
            ptype = PType(ptype_val)
        except ValueError:
            raise UnknownPTypeError(ptype_val)

        return cls(seq, ack, ptype, hcs, cs)

    @staticmethod
    def calculate_header_checksum(seq, ack, ptype):
        """
        Checksum over just the header fields.
        Uses wrapping u16 addition (mask with 0xFFFF).
        """
        cs = 0
        cs = (cs + (seq >> 16)) & 0xFFFF
        cs = (cs + (seq & 0xFFFF)) & 0xFFFF
        cs = (cs + (ack >> 16)) & 0xFFFF
        cs = (cs + (ack & 0xFFFF)) & 0xFFFF
        cs = (cs + int(ptype)) & 0xFFFF
        return cs

    @staticmethod
    def calculate_checksum(seq, ack, ptype, header_checksum, data=None):
        """
        Full checksum including payload.
        Processes payload as 16-bit words, pads odd byte at the end.
        """
        cs = header_checksum

        cs = (cs + (seq >> 16)) & 0xFFFF
        cs = (cs + (seq & 0xFFFF)) & 0xFFFF
        cs = (cs + (ack >> 16)) & 0xFFFF
        cs = (cs + (ack & 0xFFFF)) & 0xFFFF
        cs = (cs + int(ptype)) & 0xFFFF

        if data is not None:
            n = len(data)
            # process pairs of bytes as 16-bit words
            even_end = n if n % 2 == 0 else n - 1
            for i in range(0, even_end, 2):
                cs = (cs + (data[i] << 8)) & 0xFFFF
                cs = (cs + data[i + 1]) & 0xFFFF
            # if odd number of bytes, pad the last one
            if n % 2 != 0:
                cs = (cs + (data[-1] << 8)) & 0xFFFF

        return cs

    def verify_header_checksum(self):
        expected = Header.calculate_header_checksum(self.seq, self.ack, self.ptype)
        return self.header_checksum == expected

    def verify_checksum(self, data=None):
        expected = Header.calculate_checksum(
            self.seq, self.ack, self.ptype, self.header_checksum, data
        )
        return self.checksum == expected

    def __repr__(self):
        return f"Header(seq={self.seq}, ack={self.ack}, type={self.ptype.name})"


def packet_to_binary(header, data=None):
    """Pack a Header and optional payload into raw bytes."""
    raw = HEADER_FORMAT.pack(
        header.seq,
        header.ack,
        0,  # padding
        int(header.ptype),
        header.header_checksum,
        header.checksum,
    )
    if data is not None:
        return raw + bytes(data)
    return raw
