import time
import random

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

from program import BaseProgram
from block import Block


class Miner(BaseProgram):
    """
    A miner is a program running on a Node
    """
    def recv(self, packet, interface):
        time.sleep(0.2)  # nicety so that printers print after all the debug statements
        self.node.log(("Miner recv:").ljust(39), packet.decode())

    def run(self):
        """
        Overloading the BaseProgram's run method to do mining
        """
        while self.keep_listening:
            for interface in self.node.interfaces:
                try:
                    self.recv(self.node.inq[interface].get(timeout=0), interface)
                except Empty:
                    time.sleep(0.01)
            b = Block(self.node.name)
            self.node.send(b)
            time.sleep(random.randint(5, 20))
