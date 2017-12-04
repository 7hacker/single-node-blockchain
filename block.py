import time
import json


class Block:
    def __init__(self, name):
        self.block = {
            "name": name,
            "timestamp": int(time.time())
        }

    def decode(self):
        return json.dumps(self.block)
