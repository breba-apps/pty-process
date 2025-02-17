from collections import deque


class MatchingTextBuffer():
    def __init__(self, match: str):
        self.match = match
        self.buffer = deque(maxlen=len(match))

    def append(self, text: str):
        self.buffer.extend(text)

    def text(self):
        return "".join(self.buffer)

    def find_match(self, text: str):
        self.append(text)
        return self.match in self.text()