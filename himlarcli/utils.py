import sys
import netifaces
import ipaddress

def has_network_access(network, log=None):
    net = ipaddress.ip_network(network)
    if log:
        log.debug("Testing access to %s" % net)
        log.debug("Interfaces: " + ", ".join(netifaces.interfaces()))
    inf = netifaces.interfaces()
    for i in inf:
        addrs = netifaces.ifaddresses(i)
        try:
            for addr in addrs[netifaces.AF_INET]:
                ip_addr = ipaddress.ip_address(addr['addr'])
                if ip_addr.is_loopback:
                    continue
                if ip_addr in net:
                    if log:
                        log.debug("Interface %s has access to %s" % (i, net))
                    return True
        except KeyError as e:
            pass
    return False
