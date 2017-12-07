import threading
import time

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty


class BaseProgram(threading.Thread):
    """
    Represents a program running on a Node that interprets and responds to
    incoming packets
    """
    def __init__(self, node):
        threading.Thread.__init__(self)
        self.keep_listening = True
        self.node = node

    def run(self):
        """
        runloop that reads packets off the node's incoming packet buffer
        (node.inq)
        """
        while self.keep_listening:
            for interface in self.node.interfaces:
                try:
                    self.recv(self.node.inq[interface].get(timeout=0), interface)
                except Empty:
                    time.sleep(0.01)

    def stop(self):
        self.keep_listening = False
        self.join()

    def recv(self, packet, interface):
        """
        overload this and put logic here to actually do something with the packet
        """
        pass
