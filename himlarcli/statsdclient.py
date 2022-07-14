import statsd
from himlarcli.client import Client


class StatsdClient(Client):

    """ Client to interface statsd """

    def __init__(self, config_path, debug=False, log=None, prefix='uh-iaas'):
        super().__init__(config_path, debug, log)

        server = self.get_config('statsd', 'server')
        port = self.get_config('statsd', 'port')

        self.client = statsd.StatsClient(server, port, prefix=prefix)
        self.debug_log(f'connected to statsd server {server}:{port}')

    def gauge(self, metric, count, delta=False):
        """Set a gauge value."""
        self.debug_log(f'gauge: {metric}={count}')
        if not self.dry_run:
            if delta:
                self.client.gauge(metric, count, delta=True)
            else:
                self.client.gauge(metric, count)

    def get_client(self):
        return self.client

    def gauge_dict(self, name, data):
        """ Recursive function to create gauge data from a large dict """
        for k, value in data.items():
            metric = f'{name}.{k}'
            if isinstance(value, dict):
                self.gauge_dict(metric, value)
            else:
                self.gauge(metric, value)
