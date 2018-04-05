#!/usr/bin/env python
""" Setup dataporten openid mapping """

import utils
from himlarcli.keystone import Keystone
from himlarcli import utils as himutils

options = utils.get_options('Setup dataporten openid mapping',
                             hosts=0, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_domain('dataporten')
# Domain should be create from hieradata
domain = ksclient.get_domain_id()
rules = [{
    "local": [{
        "user": { "name": "{0}", "id": "{0}" },
        "group": { "name": "{0}-group", "domain": { "id": domain } } }],
    "remote": [{ "type": "OIDC-email" }, { "type": "OIDC-name" }]
}, {
    "local": [{
        "group": { "name": "nologin", "domain": { "id": domain } } }],
        "remote": [{ "type": "OIDC-email" }, { "type": "OIDC-name" }]
}]

# Crate nologin group
desc = 'All authenticated users are mapped to nologin which has no role grants'
ksclient.create_group('nologin', desc, 'dataporten')

# Create provider, mapping and container to connect them
ksclient.set_mapping('dataporten_personal', rules)
ksclient.set_protocol('openidc', 'dataporten', 'dataporten_personal')
