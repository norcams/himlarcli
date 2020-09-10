from himlarcli.client import Client
from himlarcli import utils
import ldap
import inspect
import re

class LdapClient(Client):

    def __init__(self, config_path, ldap_config='config/ldap.yaml', debug=False, log=None):
        self.config = self.load_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: {}'.format(self.config_path))
        self.ldap_config = utils.load_config(ldap_config, self.logger)
        self.debug = debug
        self.dry_run = False
        self.org = None
        self.ldap = None

    def bind(self, org):
        server = self.get_ldap_config(org, 'server')
        self.org = org
        try:
            self.ldap = ldap.initialize(server)
            self.ldap.simple_bind()
            self.debug_log('LDAP: connected to server %s' % server)
        except ldap.LDAPError as e:
            self.log_error('failed to connect to %s with error: %s' % (server, e.message['desc']))

    def get_ldap_config(self, org, option):
        if org not in self.ldap_config:
            self.debug_log('ldap config: missing org %s' % org)
        if option not in self.ldap_config[org]:
            self.debug_log('ldap config: misssing value %s for org %s' % (option, org))
        return self.ldap_config.get(org).get(option)

    def get_client(self):
        return self.ldap

    def get_user(self, email, org=None, attr=None):
        if not self.ldap:
            raise ValueError('ldap server not configured. Run bind() first')
        base_dn = self.get_ldap_config(self.org, 'base_dn')
        try:
            if org and org == 'uio' and "@" in email:
                user = self.ldap.search_s(base_dn,
                                          ldap.SCOPE_SUBTREE,
                                          "(uid=%s)" % email.split("@")[0],
                                          attr)
            else:
                user = self.ldap.search_s(base_dn,
                                          ldap.SCOPE_SUBTREE,
                                          "(mail=%s)" % email,
                                          attr)
        except ldap.LDAPError as e:
            self.log_error('ldap server for %s failed: %s' % (self.org, e.message['desc']), 1)
        return user
