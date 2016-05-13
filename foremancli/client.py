import ConfigParser
import warnings
from foreman.client import Foreman

class Client(object):

    def __init__(self, config_path, version='1'):
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        self.config = config._sections['foreman']
        warnings.filterwarnings("ignore")
        self.foreman = Foreman(self.config['url'],
                               (self.config['user'], self.config['password']),
                               api_version=2,
                               version=version,
                               verify=False)

    def set_host_build(self, host, build=True):
        if len(self.foreman.show_hosts(id=host)) > 0:
            self.foreman.update_hosts(id=host, host={'build': bulid})

    def _print_attr():
        attr = self.foreman.__dict__
        for a in attr:
            print a
