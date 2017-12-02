import time
import random


class Miner:
    def __init__(self, miner_id):
        self.id = miner_id
        self._miner_log("I am born!")

    def _miner_log(self, log_str):
        print("Miner-%d: %s" % (self.id, log_str))

    def mine(self):
        while True:
            time.sleep(random.randint(1,10))
            self._miner_log("Waking up to mine!")
