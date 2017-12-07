try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

from collections import defaultdict

from program import BaseProgram


class VirtualLink:
    """A Link represents a network link between Nodes.
    Nodes.interfaces is a list of the [Link]s that it's connected to.
    Some links are BROADCAST (all connected nodes get a copy of all packets),
    others are UNICAST (you only see packets directed to you), or
    MULTICAST (you can send packets to several people at once).
    Give two nodes the same VirtualLink() object to simulate connecting them
    with a cable."""

    broadcast_addr = "00:00:00:00:00:00:00"

    def __init__(self, name="vlan1"):
        self.name = name
        self.keep_listening = True

        # buffer for receiving incoming packets
        self.inq = defaultdict(Queue)  # mac_addr: [packet1, packet2, ...]
        self.inq[self.broadcast_addr] = Queue()

    # Utilities

    def __repr__(self):
        return "<%s>" % self.name

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        """number of nodes listening for packets on this link"""
        return len(self.inq)

    def log(self, *args):
        """stdout and stderr for the link"""
        print("%s %s" % (str(self).ljust(8), " ".join([str(x) for x in args])))

    # Runloop

    def start(self):
        """all links need to have a start() method because threaded ones use it start their runloops"""
        return True

    def stop(self):
        """all links also need stop() to stop their runloops"""
        self.keep_listening = False
        # if threaded, kill threads before going down
        if hasattr(self, 'join'):
            self.join()
        self.log("Went down.")
        return True

    # IO

    def recv(self, mac_addr=broadcast_addr, timeout=0):
        """read packet off the recv queue for a given address, optional timeout
        to block and wait for packet"""

        # recv on the broadcast address "00:..:00" will give you all packets (for promiscuous mode)
        if self.keep_listening:
            try:
                return self.inq[str(mac_addr)].get(timeout=timeout)
            except Empty:
                return ""
        else:
            self.log("is down.")

    def send(self, packet, mac_addr=broadcast_addr):
        """place sent packets directly into the reciever's queues (as if they are connected by wire)"""
        if self.keep_listening:
            if mac_addr == self.broadcast_addr:
                for addr, recv_queue in self.inq.items():
                    recv_queue.put(packet)
            else:
                self.inq[mac_addr].put(packet)
                self.inq[self.broadcast_addr].put(packet)
        else:
            self.log("is down.")


class BaseFilter:
    """Filters work just like iptables filters, they are applied in order to all incoming and outgoing packets
       Filters can return a modified packet, or None to drop it
    """

    # stateless filters use classmethods, stateful filters should add an __init__
    @classmethod
    def tr(self, packet, interface):
        """tr is shorthand for receive filter method
            incoming node packets are filtered through this function before going in the inq
        """
        return packet
    @classmethod
    def tx(self, packet, interface):
        """tx is send filter method
            outgoing node packets are filtered through this function before being sent to the link
        """
        return packet


class LoopbackFilter(BaseFilter):
    """Filter recv copies of packets that the node just sent out.
        Needed whenever your node is connected to a BROADCAST link where all packets go to everyone.
    """
    def __init__(self):
        self.sent_hashes = defaultdict(int)  # defaults to 0
        # serves as a counter. each packet is hashed,
        # if we see that hash sent once we can ignore one received copy,
        # if we send it twice on two ifaces, we can ignore two received copies

    def tr(self, packet, interface):
        if not packet: return None
        elif self.sent_hashes[hash(packet)] > 0:
            self.sent_hashes[hash(packet)] -= 1
            return None
        else:
            return packet

    def tx(self, packet, interface):
        if not packet: return None
        else:
            self.sent_hashes[hash(packet)] += 1
            return packet


class Broadcast(BaseProgram):
    """Broadcast Switch that routes a packet coming in on any interface to all the other interfaces."""
    def recv(self, packet, interface):
        other_ifaces = set(self.node.interfaces) - {interface}
        if packet and other_ifaces:
            self.node.log("Broadcasted on the Blockchain: ", packet.decode())
            self.node.send(packet, interfaces=other_ifaces)
