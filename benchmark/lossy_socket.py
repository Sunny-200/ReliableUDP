"""Socket wrapper that randomly drops packets to simulate network loss."""

import random


class LossySocket:
    """Wraps a UDP socket and drops a percentage of outgoing packets."""

    def __init__(self, sock, loss_rate=0.1):
        self.sock = sock
        self.loss_rate = loss_rate
        self.enabled = True    # set to False to bypass loss temporarily
        self.sent = 0
        self.dropped = 0

    def sendto(self, data, addr):
        self.sent += 1
        if self.enabled and random.random() < self.loss_rate:
            self.dropped += 1
            return len(data)  # pretend we sent it
        return self.sock.sendto(data, addr)

    def recvfrom(self, bufsize):
        return self.sock.recvfrom(bufsize)

    def settimeout(self, t):
        self.sock.settimeout(t)

    def setsockopt(self, *args):
        self.sock.setsockopt(*args)

    def bind(self, addr):
        self.sock.bind(addr)

    def close(self):
        self.sock.close()

    def stats(self):
        pct = 100 * self.dropped / max(self.sent, 1)
        return f"sent={self.sent}, dropped={self.dropped} ({pct:.1f}%)"

