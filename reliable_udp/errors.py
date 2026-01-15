from .packet import MAX_PACKET_SIZE


class PacketParsingError(Exception):
    """Base class for packet parsing errors."""
    pass


class TooSmallPacketError(PacketParsingError):
    def __init__(self):
        super().__init__("Packet should be at least 14 bytes")


class TooBigPacketError(PacketParsingError):
    def __init__(self, size):
        self.size = size
        super().__init__(f"Too big packet: {size}, max is: {MAX_PACKET_SIZE}")


class UnknownPTypeError(PacketParsingError):
    def __init__(self, ptype):
        self.ptype = ptype
        super().__init__(f"Unknown packet type: {ptype}")
