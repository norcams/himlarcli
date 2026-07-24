
import re
import requests
import urllib3

class Placement():

    def __init__(self, keystone_client, region):
        # We talk to the placement API over https with an internal CA, so we
        # skip verification and silence the resulting warning once.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Reuse a single session so the auth token/headers are set once and the
        # TLS connection is kept alive across the many requests we make.
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'X-Auth-Token': keystone_client.sess.get_auth_headers()['X-Auth-Token'],
            'OpenStack-API-Version': 'placement 1.36'  # FIXME: get from config
        })

        # Get Placement service endpoint (FIXME: there has to be a better way)
        for x in keystone_client.client.endpoints.list(interface='admin', region_id=region):
            url = getattr(x, 'url')
            if re.match(r'.+placement.+', url):
                break
        self.ENDPOINT = url

    # https://docs.openstack.org/api-ref/placement/#list-resource-provider-usages
    def get_resource_provider_usages(self, uuid):
        result = self.session.get(
            self.ENDPOINT + f'resource_providers/{uuid}/usages'
        )
        return result.json()

    # https://docs.openstack.org/api-ref/placement/#list-resource-providers
    def get_resource_provider_tree(self, uuid):
        result = self.session.get(
            self.ENDPOINT + 'resource_providers',
            params = { "in_tree": uuid }
        )
        return result.json()

    # https://docs.openstack.org/api-ref/placement/#show-resource-provider-inventory
    def get_resource_provider_inventory(self, uuid, resource_class):
        result = self.session.get(
            self.ENDPOINT + f'resource_providers/{uuid}/inventories/{resource_class}'
        )
        return result.json()

    # https://docs.openstack.org/api-ref/placement/#list-resource-provider-inventories
    # Return all inventory classes for a provider in a single request. The
    # returned dict is keyed by resource class, e.g.
    # {'VCPU': {...}, 'MEMORY_MB': {...}, 'DISK_GB': {...}}
    def get_resource_provider_inventories(self, uuid):
        result = self.session.get(
            self.ENDPOINT + f'resource_providers/{uuid}/inventories'
        )
        return result.json().get('inventories', {})

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
