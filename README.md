# ReliableUDP

Reliable UDP with TCP mechanisms — implemented in Python.

This protocol copies essential TCP functionality over UDP:
- **3-way handshake** (SYN → SYN-ACK → ACK)
- **Sequence & acknowledgment numbers** for ordered delivery
- **Header and payload checksums** for integrity verification

## Project Structure

```
reliable_udp/          # Core library
├── __init__.py
├── packet.py          # Header parsing, checksum, serialization
├── manager.py         # Connection state management
└── errors.py          # Custom exceptions

examples/              # Working demos
├── echo_server.py     # Listens on port 5050, echoes data back
└── echo_client.py     # Connects, sends "Echo me!", prints reply

tests/                 # Unit tests
└── test_packet.py     # Checksum, parsing, and serialization tests
```

## Packet Format (14-byte header)

| Bytes  | Field            | Type          |
|--------|------------------|---------------|
| 0–3    | Sequence number  | u32 big-endian|
| 4–7    | Ack number       | u32 big-endian|
| 8      | Padding          | u8 (0x00)     |
| 9      | Packet type      | u8            |
| 10–11  | Header checksum  | u16 big-endian|
| 12–13  | Full checksum    | u16 big-endian|
| 14+    | Payload data     | variable      |

## Running the Examples

```bash
# Terminal 1 — start the server
python examples/echo_server.py

# Terminal 2 — run the client
python examples/echo_client.py
```

## Running Tests

```bash
python -m pytest tests/
# or
python -m unittest discover tests/
```

## Requirements

- Python 3.10+ (uses `match` compatible enums and type unions)
- No external dependencies — stdlib only
