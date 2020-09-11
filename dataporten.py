#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli import utils

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)

# Domain should be create from hieradata
domain = ksclient.get_domain_id()

rules = [{
    "local": [{
        "user": {"name": "{0}", "id": "{0}"},
        "group": {"name": "{0}-group", "domain": {"id": domain}}}],
    "remote": [{"type": "OIDC-email"}, {"type": "OIDC-name"}]
}, {
    "local": [{
        "group": {"name": "nologin", "domain":{"id": domain}}}],
    "remote": [{"type": "OIDC-email"}, {"type": "OIDC-name"}]
}]

# Crate nologin group

def action_update():

    desc = 'All authenticated users are mapped to nologin which has no role grants'
    ksclient.create_group('nologin', desc, 'dataporten')

    # Create provider, mapping and container to connect them
    ksclient.set_identity_provider('dataporten',
                                   'https://auth.dataporten.no',
                                   'Federated user from Dataporten')
    ksclient.set_mapping('dataporten_personal', rules)
    ksclient.set_protocol('openid', 'dataporten', 'dataporten_personal')

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
