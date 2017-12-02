import multiprocessing

from miner import Miner

NUM_MINING_NODES = 5

class Blockchain:
    def __init__(self):
        pass

    def build_genesis_block(self):
        print("Made a genesis block")

    def launch_mining_nodes(self, num_nodes):
        for i in range(num_nodes):
            miner = Miner(i)
            miner_process = multiprocessing.Process(target=miner.mine)
            miner.daemon = True
            miner_process.start()

snb = Blockchain()
snb.build_genesis_block()
snb.launch_mining_nodes(NUM_MINING_NODES)