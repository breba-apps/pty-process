from collections import deque


class MatchingTextBuffer():
    def __init__(self, match: str):
        self.match = match
        self.buffer = deque(maxlen=200)  # we are expecting at the end, but sometimes pick up extra chars

    def append(self, text: str):
        self.buffer.extend(text)

    def text(self):
        return "".join(self.buffer)

    def find_match(self, text: str):
        self.append(text)
        return self.match in self.text()