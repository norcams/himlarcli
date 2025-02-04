
import requests
import re

class Placement():

    def __init__(self, keystone_client, region):
        # Set REST API headers
        self.HEADERS = {
            'X-Auth-Token': keystone_client.sess.get_auth_headers()['X-Auth-Token'],
            'OpenStack-API-Version': 'placement 1.36'  # FIXME: get from config
        }
        # Get Placement service endpoint (FIXME: there has to be a better way)
        for x in keystone_client.client.endpoints.list(interface='admin', region_id=region):
            url = getattr(x, 'url')
            if re.match(r'.+placement.+', url):
                break
        self.ENDPOINT = url

    # https://docs.openstack.org/api-ref/placement/#list-resource-provider-usages
    def get_resource_provider_usages(self, uuid):
        result = requests.get(
            self.ENDPOINT + f'resource_providers/{uuid}/usages',
            headers = self.HEADERS,
            verify  = False
        )
        return result.json()

    # https://docs.openstack.org/api-ref/placement/#list-resource-providers
    def get_resource_provider_tree(self, uuid):
        result = requests.get(
            self.ENDPOINT + 'resource_providers',
            headers = self.HEADERS,
            params  = { "in_tree": uuid },
            verify  = False
        )
        return result.json()

    # https://docs.openstack.org/api-ref/placement/#show-resource-provider-inventory
    def get_resource_provider_inventory(self, uuid, resource_class):
        result = requests.get(
            self.ENDPOINT + f'resource_providers/{uuid}/inventories/{resource_class}',
            headers = self.HEADERS,
            verify  = False
        )
        return result.json()

    # Count the number of vGPUs total and in use on a hypervisor
    # FIXME: Do not use, is very slow
    def get_vgpu_usage(self, uuid):
        result = self.get_resource_provider_tree(uuid)
        vgpu = {
            'used':  0,
            'total': 0,
        }
        for rp in result['resource_providers']:
            if not re.match(r'.*pci.*', rp['name']):
                continue
            inv = self.get_resource_provider_inventory(rp['uuid'], 'VGPU')
            #print(f"DEBUG: {rp['name']} {rp['uuid']} total: {inv['total']}")
            usg = self.get_resource_provider_usages(rp['uuid'])
            vgpu['used']  += usg['usages']['VGPU']
            vgpu['total'] += inv['total']
        return vgpu
