import time
import random
import threading

from networking import Printer, Node
from block import Block


class Miner:
    def __init__(self, miner_id, virtual_link):
        self.id = miner_id
        self.name = "miner-%d" % self.id
        self.virtual_link = virtual_link
        self.mine_thread = threading.Thread(target=self.mine)
        self.mine_thread.setDaemon(True)

    def boot(self):
        self.miner_node = Node([self.virtual_link], self.name, Program=Printer)
        self.miner_node.start()
        self.mine_thread.start()

    def mine(self):
        while True:
            b = Block(self.name)
            self.miner_node.send(b)
            time.sleep(random.randint(5, 20))
