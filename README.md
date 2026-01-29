# ReliableUDP

Reliable UDP with TCP mechanisms — implemented in Python.

This protocol implements reliable data transfer over UDP:
- **3-way handshake** (SYN → SYN-ACK → ACK)
- **Sequence & acknowledgment numbers** for ordered delivery
- **Checksums** for header and payload integrity
- **Retransmission** with configurable timeout and retry count
- **Go-Back-N sliding window** for pipelined bulk transfer

## Project Structure

```
reliable_udp/            # Core library
├── __init__.py
├── packet.py            # Header parsing, checksum, serialization
├── manager.py           # Connection state
├── errors.py            # Custom exceptions
└── transport.py         # Retransmission, handshake, sliding window

examples/                # Working demos
├── echo_server.py       # Simple echo with retransmission
├── echo_client.py       # Sends "Echo me!", prints reply
├── bulk_receiver.py     # Sliding window receiver (64 KB)
└── bulk_sender.py       # Sliding window sender

benchmark/               # Performance testing
├── lossy_socket.py      # Simulates packet loss
└── run_benchmark.py     # Throughput comparison: reliable vs raw UDP

tests/                   # Unit + integration tests
├── test_packet.py       # Checksum and parsing tests
└── test_transport.py    # Retransmission and window tests
```

## Running the Examples

```bash
# Echo (two terminals)
python examples/echo_server.py       # Terminal 1
python examples/echo_client.py       # Terminal 2

# Bulk transfer with sliding window (two terminals)
python examples/bulk_receiver.py     # Terminal 1
python examples/bulk_sender.py       # Terminal 2
```

## Running the Benchmark

```bash
python benchmark/run_benchmark.py
```

Compares Reliable UDP against Raw UDP under **10% simulated packet loss**:

- **Reliable UDP:** 100% data delivered (via sliding window + retransmission)
- **Raw UDP:** ~85-95% delivered (data lost permanently)

This confirms the protocol's reliability under a degraded network.

## Running Tests


```bash
python -m pytest tests/ -v
# or
python -m unittest discover tests/
```

## Requirements

- Python 3.10+
- No external dependencies — stdlib only
