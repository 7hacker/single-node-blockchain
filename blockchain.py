from networking import VirtualLink, Broadcast
from node import Node
from miner import Miner
import config as cfg


class Blockchain:
    def __init__(self):
        self.internet = None
        self.all_nodes = []
        self.all_links = []
        self._create_nodes_and_links()

    def _create_nodes_and_links(self):
        for n in range(0, cfg.NUM_FULL_NODES):
            # Build a virtual link
            virtual_link = VirtualLink('vl-%d' % n)
            # A full node is a node with a virtual link and runs a Miner program
            full_node = Node([virtual_link], name=("Node-%d" % n), Program=Miner)

            self.all_links.append(virtual_link)
            self.all_nodes.append(full_node)

        # Setup the Broadcast: Simulate the Internet
        self.internet = Node(self.all_links, 'Internet', Program=Broadcast)
        self.internet.start()

        # Start all links attached to the internet
        [l.start() for l in self.all_links]

        # Start all full nodes
        [fn.start() for fn in self.all_nodes]

        self.internet.send(bytes("Internet: Made a genesis block", 'UTF-8'))


def main():
    Blockchain()


if __name__ == "__main__":
    main()
