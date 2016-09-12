#!/usr/bin/env python
""" Setup dataporten openid mapping """

import utils
from himlarcli.keystone import Keystone
from himlarcli import utils as himutils

options = utils.get_options('Setup dataporten openid mapping',
                             hosts=0, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)

# Domain should be create from hieradata
domain = ksclient.get_domain_id('dataporten')
rules = [{
    "local": [{
        "user": { "name": "{1}","id": "{0}" },
        "group": { "name": "{0}-group", "domain": { "id": domain } } }],
    "remote": [{ "type": "OIDC-email" }, { "type": "OIDC-sub" }]
}]

# Create provider, mapping and container to connect them
ksclient.set_identity_provider('dataporten', 'https://auth.dataporten.no')
ksclient.set_mapping('dataporten_personal', rules)
ksclient.set_protocol('oidc', 'dataporten', 'dataporten_personal')
