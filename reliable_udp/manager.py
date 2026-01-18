"""Connection state and buffer size constants."""

MAX_RECEIVE_BUFFER_SIZE = 523944
MAX_SEND_BUFFER_SIZE = 523944


class Connection:
    """Keeps track of a single reliable-UDP connection."""

    def __init__(self, seq=0, ack=0, previous_seq=0, is_open=False, last_response=0):
        self.seq = seq
        self.ack = ack
        self.previous_seq = previous_seq
        self.is_open = is_open
        self.last_response = last_response
