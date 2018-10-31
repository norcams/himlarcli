from himlarcli.client import Client
from himlarcli import utils
import ldap

class LdapClient(Client):

    def __init__(self, config_path, ldap_config='config/ldap.yaml', debug=False, log=None):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.ldap_config = utils.load_config(ldap_config, self.logger)
        self.debug = debug
        self.dry_run = False
        self.org = None
        self.ldap = None

    def bind(self, org):
        server = self.get_ldap_config(org, 'server')
        self.org = org
        try:
            self.ldap = ldap.open(server)
            self.ldap.simple_bind()
            self.debug_log('LDAP: connected to server %s' % server)
        except ldap.LDAPError as e:
            print e

    def get_ldap_config(self, org, option):
        if org not in self.ldap_config:
            self.debug_log('ldap config: missing org %s' % org)
        if option not in self.ldap_config[org]:
            self.debug_log('ldap config: misssing value %s for org %s' % (option, org))
        return self.ldap_config.get(org).get(option)

    def get_client(self):
        return self.ldap

    def get_user(self, email, attr=None):
        base_dn = self.get_ldap_config(self.org, 'base_dn')
        return self.ldap.search_s(base_dn,
                                  ldap.SCOPE_SUBTREE,
                                  "(mail=%s)" % email,
                                  attr)
