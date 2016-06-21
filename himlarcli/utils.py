import sys
import os
import ConfigParser
import logging
import netifaces
import ipaddress
import logger

def get_config(config_path):
    if not os.path.isfile(config_path):
        logging.critical("Could not find config file: %s" %config_path)
        sys.exit(1)
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    return config

def get_logger(name, config, debug, log):
    log_path = config.get('log', 'path')
    if not log_path:
        log_path = '/opt/himlarcli/'
        logging.debug('could not find [log] section in config file')
    if log:
        mylog = log
    else:
        mylog = logger.setup_logger(name, debug, log_path)
    return mylog

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
