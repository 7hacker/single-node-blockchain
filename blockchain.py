from mesh.links import VirtualLink
from mesh.programs import Switch
from mesh.node import Node

from miner import Miner

NUM_MINING_NODES = 5


class Blockchain:
    def __init__(self):
        self.all_nodes = []
        self.all_links = []
        self.hub = None
        self._create_nodes_and_links()

    def _create_nodes_and_links(self):
        for n in range(NUM_MINING_NODES):
            virtual_link = VirtualLink('vl-%d' % n)
            miner = Miner(n, virtual_link)
            self.all_links.append(virtual_link)
            self.all_nodes.append(miner)

        self.hub = Node(self.all_links, 'Hub', Program=Switch)
        self.hub.start()

        [l.start() for l in self.all_links]

    def build_genesis_block(self):
        self.hub.send(bytes("Hub: Made a genesis block", 'UTF-8'))

    def launch_mining_nodes(self):
        for miner in self.all_nodes:
            miner.boot()
        self.build_genesis_block()


snb = Blockchain()
snb.launch_mining_nodes()
