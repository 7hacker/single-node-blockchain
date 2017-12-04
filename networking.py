import threading
import random
import time

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

from collections import defaultdict


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
        self.log("ready.")
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


# Nodes connect to each other over links.  The node has a runloop that pulls packets off the link's incoming packet Queue,
# runs them through its list of filters, then places it in the nodes incoming packet queue for that interface node.inq.
# the Node's Program is has a seperate runloop in a different thread that is constantly calling node.inq.get().
# The program does something with the packet (like print it to the screen, or reply with "ACK"), and sends any outgoing responses
# by calling the Node's send() method directly.  The Node runs the packet through it's outgoing packet filters in order, then
# if it wasn't dropped, calls the network interface's .send() method to push it over the network.

#  --> incoming packet queue | -> pulls packets off link's inq -> filters -> node.inq |  -> pulls packets off the node's inq
#              [LINK]        |                         [NODE]                         |               [PROGRAM]
#  <-- outgoing Link.send()  |   <----  outgoing filters  <-----  Node.send()  <----- |  <- sends responses by calling Node.send()

class Node(threading.Thread):
    """a Node represents a computer.  node.interfaces contains the list of network links the node is connected to.
        Nodes process incoming traffic through their filters, then place packets in their inq for their Program to handle.
        Programs process packets off the node's incoming queue, then send responses out through node's outbound filters,
        and finally out to the right network interface.
    """
    def __init__(self, interfaces=None, name="n1", promiscuous=False, mac_addr=None, Filters=(), Program=None):
        threading.Thread.__init__(self)
        self.name = name
        self.interfaces = interfaces or []
        self.keep_listening = True
        self.promiscuous = promiscuous
        self.mac_addr = mac_addr or self._generate_MAC(6, 2)
        self.inq = defaultdict(Queue)
        self.filters = [LoopbackFilter()] + [F() for F in Filters]             # initialize the filters that shape incoming and outgoing traffic before it hits the program
        self.program = Program(node=self) if Program else None                  # init the program that will be processing incoming packets

    def __repr__(self):
        return "[{0}]".format(self.name)

    def __str__(self):
        return self.__repr__()

    @staticmethod
    def _generate_MAC(segments=6, segment_length=2, delimiter=":", charset="0123456789abcdef"):
        """generate a non-guaranteed-unique mac address"""
        addr = []
        for _ in range(segments):
            sub = ''.join(random.choice(charset) for _ in range(segment_length))
            addr.append(sub)
        return delimiter.join(addr)

    def log(self, *args):
        """stdout and stderr for the node"""
        print("%s %s" % (str(self).ljust(8), " ".join(str(x) for x in args)))

    def stop(self):
        self.keep_listening = False
        if self.program:
            self.program.stop()
        self.join()
        return True

    # Runloop

    def run(self):
        """runloop that gets triggered by node.start()
        reads new packets off the link and feeds them to recv()
        """
        if self.program:
            self.program.start()
        while self.keep_listening:
            for interface in self.interfaces:
                packet = interface.recv(self.mac_addr if not self.promiscuous else "00:00:00:00:00:00")
                if packet:
                    self.recv(packet, interface)
                time.sleep(0.01)
        self.log("Stopped listening.")

    # IO

    def recv(self, packet, interface):
        """run incoming packet through the filters, then place it in its inq"""
        # the packet is piped into the first filter, then the result of that into the second filter, etc.
        for f in self.filters:
            if not packet:
                break
            packet = f.tr(packet, interface)
        if packet:
            # if the packet wasn't dropped by a filter, log the recv and place it in the interface's inq
            # self.log("IN      ", str(interface).ljust(30), packet.decode())
            self.inq[interface].put(packet)

    def send(self, packet, interfaces=None):
        """write packet to given interfaces, default is broadcast to all interfaces"""
        interfaces = interfaces or self.interfaces  # default to all interfaces
        interfaces = interfaces if hasattr(interfaces, '__iter__') else [interfaces]

        for interface in interfaces:
            for f in self.filters:
                packet = f.tx(packet, interface)  # run outgoing packet through the filters
            if packet:
                # if not dropped, log the transmit and pass it to the interface's send method
                # self.log("OUT     ", ("<"+",".join(i.name for i in interfaces)+">").ljust(30), packet.decode())
                interface.send(packet)


class BaseProgram(threading.Thread):
    """Represents a program running on a Node that interprets and responds to incoming packets."""
    def __init__(self, node):
        threading.Thread.__init__(self)
        self.keep_listening = True
        self.node = node

    def run(self):
        """runloop that reads packets off the node's incoming packet buffer (node.inq)"""
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
        """overload this and put logic here to actually do something with the packet"""
        pass


class Printer(BaseProgram):
    """A simple program to just print incoming packets to the console."""
    def recv(self, packet, interface):
        time.sleep(0.2)  # nicety so that printers print after all the debug statements
        self.node.log(("PRINTER  %s" % interface).ljust(39), packet.decode())


class Switch(BaseProgram):
    """A switch that routes a packet coming in on any interface to all the other interfaces."""
    def recv(self, packet, interface):
        other_ifaces = set(self.node.interfaces) - {interface}
        if packet and other_ifaces:
            self.node.log("SWITCH  ", (str(interface)+" >>>> <"+','.join(i.name for i in other_ifaces)+">").ljust(30), packet.decode())
            self.node.send(packet, interfaces=other_ifaces)