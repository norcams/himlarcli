from himlarcli.client import Client
import statsd
import types

class StatsdClient(Client):

    def __init__(self, config_path, debug=False, log=None, prefix='uh-iaas'):
        super(StatsdClient, self).__init__(config_path, debug, log)

        server = self.get_config('statsd', 'server')
        port = self.get_config('statsd', 'port')

        self.client = statsd.StatsClient(server, port, prefix=prefix)
        self.debug_log('connected to statsd server %s:%s' % (server, port))

    def gauge(self, metric, count, delta=False):
        self.debug_log('gauge: %s = %s' % (metric, count))
        if not self.dry_run:
            if delta:
                self.client.gauge(metric, count, delta=True)
            else:
                self.client.gauge(metric, count)

    def get_client(self):
        return self.client

    def gauge_dict(self, name, data):
        for k,v in data.iteritems():
            metric = '%s.%s' % (name, k)
            if isinstance(v, dict):
                self.gauge_dict(metric, v)
            else:
                self.gauge(metric, v)
