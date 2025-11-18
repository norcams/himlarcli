import sensu_go
from himlarcli.client import Client
from himlarcli.slack import Slack
from himlarcli import utils
import requests

# pylint: disable=C0115
class SensuGo(Client):

    def __init__(self, config_path, debug=False, log=None):
        super().__init__(config_path, debug, log)
        self.client = sensu_go.Client(address=self.get_config('sensugo', 'url'),
                                      username=self.get_config('sensugo', 'username'),
                                      password=self.get_config('sensugo', 'password'),
                                      #verify=False,
                                      ca_path=self.get_config('sensugo', 'ca_path'))
        self.debug_log(f'connect to {self.get_config("sensugo", "url")}')

    def get_client(self):
        return self.client

    def get_events(self):
        events = self.client.events.list()
        return events

    def get_silenced(self, host, check):
        return self.client.silences.get(f'entity:{host}:{check}')

    def list_silenced(self):
        hosts = self.client.silences.list()
        return hosts

    def clear_silenced(self, host, check):
        try:
            self.debug_log(f'unsilence {check} for {host}')
            self.client.silences.delete(f'entity:{host}:{check}')
        except sensu_go.errors.ResponseError as e:
            message = e.text
            self.debug_log(f'{check} for {host}: {message}')

    def silence_check(self, host, check, expire='-1', reason='himlarcli', slack=False, expire_on_resolve=True):
        spec = {
            'subscription': f'entity:{host}',
            'check': check,
            'expire': int(expire),
            'expire_on_resolve': expire_on_resolve,
            'reason': reason}
        metadata = { 'name': f'entity:{host}:{check}' }
        try:
            self.debug_log(f'silence {check} for {host}')
            self.client.silences.create(spec=spec, metadata=metadata)
        except ValueError as e:
            utils.improved_sys_error(e, 'error')
        if slack:
            msg = f'Silence {check} for {host}: {reason}'
            slack_client = self._get_client(Slack)
            try:
                slack_client.publish_slack(msg)
            except requests.exceptions.MissingSchema as e:
                utils.improved_sys_error(f'slack problem: {e}', 'error')

    def delete_client(self, host):
        try:
            self.client.entities.delete(host)
        except sensu_go.errors.ResponseError as e:
            message = e.text
            self.debug_log(f'{check} for {host}: {message}')

    @staticmethod
    def get_host_from_subscription(sub):
        return sub.split(':')[-1]
