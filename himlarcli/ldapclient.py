import os
import sys
import ldap
import utils

class LdapClient(object):

    def __init__(self, config_path, debug, log=None):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        server = self.config.get('ldap','server')
        self.base_dn = self.config.get('ldap', 'base_dn')
        if not server or not self.base_dn:
            self.logger.critical('Missing config from secton [ldap]')
            sys.exit(1)
        else:
            self.logger.debug('LDAP: server = %s' % server)
            self.logger.debug('LDAP: base_dn = %s' % self.base_dn)
        try:
            self.ldap = ldap.open(server)
            self.ldap.simple_bind()
            self.logger.debug('LDAP: connected to server %s' % server)
        except ldap.LDAPError as e:
            print e

    def get_user(self, email, attr=None):
        return self.ldap.search_s(self.base_dn,
                                  ldap.SCOPE_SUBTREE,
                                  "(mail=%s)" % email,
                                  attr)
