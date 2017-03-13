from client import Client
from nova import Nova
from keystoneclient.v3 import client as keystoneclient
import keystoneauth1.exceptions as exceptions
from novaclient import client as novaclient

class Keystone(Client):
    version = 3

    def __init__(self, config_path, debug=False):
        super(Keystone,self).__init__(config_path, debug)
        self.client = keystoneclient.Client(session=self.sess,
                                            region_name=self.region)

    def get_domain_id(self, domain):
        return self.__get_domain(domain)

    def get_client(self):
        return self.client

    def get_user_by_id(self, user_id):
        return self.client.users.get(user_id)

    """ Return all users, groups and project for this email """
    def get_user_objects(self, email, domain):
        domain_id = self.__get_domain(domain)
        obj = dict()
        user_id = None
        api = self.__get_user_by_email(email=email.lower(), domain_id=domain_id)
        if len(api) == 1:
            obj['api'] = api[0]
            user_id = api[0].id
        elif len(api) > 1:
            self.logger.warning('=> More than one api user found for %s' % email)
        dp =  self.__get_user_by_email(email=email, domain_id=None)
        if len(dp) == 1:
            obj['dataporten'] = dp[0]
        elif len(dp) > 1:
            self.logger.warning('=> More than one dataporten user found for %s' % email)
        group = self.__get_group(group='%s-group' % email, domain=domain_id)
        obj['group'] = group
        if user_id:
            projects = self.client.projects.list(domain=domain_id, user=user_id)
        else:
            projects = []
        obj['projects'] = projects

        return obj

    def get_region(self):
        return self.config._sections['openstack']['region']

    def get_project_count(self, domain=False):
        projects = self.__get_projects(domain)
        return len(projects)

    def get_user_count(self, domain=False):
        users = self.__get_users(domain)
        return len(users)

    def get_project(self, project, domain=None):
        domain = self.__get_domain(domain)
        project = self.__get_project(project, domain=domain)
        return project

    def get_projects(self, domain=False, **kwargs):
        project_list = self.__get_projects(domain, **kwargs)
        return project_list

    """ Check if a user has registered with access """
    def is_valid_user(self, user, domain=None):
        domain_id = self.__get_domain(domain)
        group = self.__get_group(group='%s-group' % user, domain=domain_id)
        if group:
            return True
        else:
            return False

    def list_users(self, domain=False, **kwargs):
        user_list = self.__get_users(domain, **kwargs)
        users = list()
        for i in user_list:
            users.append(i.name)
        return users

    def list_projects(self, domain=False, **kwargs):
        project_list = self.__get_projects(domain, **kwargs)
        projects = list()
        for i in project_list:
            projects.append(i.name)
        return projects

    def list_quota(self, project, domain=None):
        domain = self.__get_domain(domain)
        project = self.__get_project(project, domain=domain)
        compute = self.__list_compute_quota(project)
        return dict({'compute':compute})

    """ Delete project and all instances """
    def delete_project(self, project, domain=None):
        # Map str to objects
        domain = self.__get_domain(domain)
        project_obj = self.__get_project(project, domain=domain)
        self.logger.debug('=> delete project %s' % project)
        # TODO FIXME!!!!!!!
        #self.__delete_instances(project_obj)
        self.client.projects.delete(project_obj)

    """ Delete both users, the users group and personal project. """
    def delete_user(self, email, domain=None, dry_run=False):
        obj = self.get_user_objects(email=email, domain=domain)
        # Delete api user
        if not dry_run and 'api' in obj:
            self.logger.debug('=> delete  api user %s' % obj['api'].name)
            self.client.users.delete(obj['api'])
        elif dry_run:
            self.logger.debug('=> DRY-RUN: delete api user %s' % obj['api'].name)
        # Delete dataporten user
        if not dry_run and 'dataporten' in obj:
            self.logger.debug('=> delete dataporten user %s' % obj['dataporten'].name)
            self.client.users.delete(obj['dataporten'])
        elif dry_run and 'dataporten' in obj:
            self.logger.debug('=> DRY-RUN: delete dataporten user %s' % obj['dataporten'].name)
        # Delete group
        if not dry_run and 'group' in obj:
            self.logger.debug('=> delete group %s' % obj['group'].name)
            self.client.groups.delete(obj['group'])
        elif dry_run:
            self.logger.debug('=> DRY-RUN: delete group %s' % obj['group'].name)
        # Delete personal project and instances
        if not dry_run and 'projects' in obj:
            self.logger.debug('=> delete project %s' % email)
            self.delete_project(project=email.lower(), domain=domain)
        else:
            self.logger.debug('=> DRY-RUN: delete project %s' % email)
        if 'projects' in obj:
            for project in obj['projects']:
                if hasattr(project, 'admin') and email == project.admin:
                    print "This user is also admin for %s" % project.name
                    print "Make sure to update admin to valid user!"

    """ Grant a role to a project for a user """
    def grant_role(self, user, project, role, domain=None):
        self.logger.debug('=> grant role %s for %s to %s' % (role, user, project))
        # Map str to objects
        domain = self.__get_domain(domain)
        group = self.__get_group(group='%s-group' % user, domain=domain)
        if not group:
            print 'Group %s-group not found!'  % user
            print 'Remember email for users is case sensitive.'
            return None
        project = self.__get_project(project, domain=domain)
        role = self.__get_role(role)
        try:
            exists = self.client.roles.list(project=project,
                                            group=group)
        except exceptions.http.NotFound as e:
            exists = None
        if exists:
            print 'Access exist for %s in project %s' % (user, project.name)
        else:
           self.client.roles.grant(role=role,
                                   project=project,
                                   group=group)

    """ Create new project """
    def create_project(self, domain, project, quota, description=None, **kwargs):
        parent_id = self.__get_domain(domain)
        project_found = self.__get_project(project, domain=parent_id)
        if project_found:
            print 'Project %s exists!' % project_found.name
            self.logger.debug('=> updating quota for project %s' % project_found.name)
            self.__set_compute_quota(project_found, quota)
            return project_found
        project = self.client.projects.create(name=project,
                                              domain=parent_id,
                                              parent=parent_id,
                                              enabled=True,
                                              description=description,
                                              **kwargs)
        self.logger.debug('=> create new project %s' % project)
        self.__set_compute_quota(project, quota)
        return project

    """ Federation settings for identity provider """
    def set_identity_provider(self, name, remote_id):
        providers = self.client.federation.identity_providers.list()
        for i in providers:
            if name == i.id:
                self.logger.debug('=> identity provider %s exists' % name)
                return
        self.client.federation.identity_providers.create(id=name,
                                                         enabled=True,
                                                         remote_ids=[remote_id])

    """ Federation settings for identity mappping """
    def set_mapping(self, id, rules):
        mappings = self.client.federation.mappings.list()
        for i in mappings:
            if id == i.id:
                self.logger.debug('=> mapping %s exists' % id)
                return
        self.client.federation.mappings.create(mapping_id=id, rules=rules)

    """ Federation settings for protocol container """
    def set_protocol(self, id, provider, mapping):
        protocols = self.client.federation.protocols.list(provider)
        for i in protocols:
            if id == i.id:
                self.logger.debug('=> protocol %s exists' % id)
                return
        self.client.federation.protocols.create(id,
                                                identity_provider=provider,
                                                mapping=mapping)

    def create_group(self, name, description, domain):
        self.logger.debug('=> create group %s' % (name))
        # Map str to objects
        domain = self.__get_domain(domain)
        if not self.__get_group(group=name, domain=domain):
            project = self.client.groups.create(name=name,
                                                domain=domain,
                                                description=description)

    def __get_project(self, project, domain=None, user=None):
        projects = self.client.projects.list(domain=domain, user=user)
        for p in projects:
            if p.name == project:
                self.logger.debug('=> project %s found' % project)
                return p
        self.logger.debug('=> project %s NOT found' % project)
        return None

    """ Return all users where name matches email.
        Note that domain_id=None will search for user without domain."""
    def __get_user_by_email(self, email, domain_id):
        users = self.client.users.list(domain=domain_id)
        match = list()
        for user in users:
            # list(domain=None) will return all domains so domain check must
            # be here. For other domains this is will just verify the domain
            if user.name == email and user.domain_id == domain_id:
                self.logger.debug('=> user %s found by email' % email)
                match.append(user)
        if not match:
            self.logger.debug('=> no user found for email %s' % email)
        return match

    def __get_role(self, role, domain=None):
        roles = self.client.roles.list(domain=domain)
        for r in roles:
            if r.name == role:
                self.logger.debug('=> role %s found' % role)
                return r
        self.logger.debug('=> role %s NOT found' % role)
        return None

    """ Return group object """
    def __get_group(self, group, domain=None, user=None):
        groups = self.client.groups.list(domain=domain, user=user)
        for g in groups:
            if g.name == group:
                self.logger.debug('=> group %s found' % group)
                return g
        self.logger.debug('=> group %s NOT found' % group)
        return None

    """ Return domain ID """
    def __get_domain(self, domain):
        domain = self.client.domains.list(name=domain)
        if len(domain) > 0:
            return domain[0].id
        else:
            return False

    def __get_projects(self, domain=False, **kwargs):
        domain_id = self.__get_domain(domain) if domain else None
        projects = self.client.projects.list(domain=domain_id, user=user_id)
        self.logger.debug('=> get projects (domain=%s,user=%s)' % (domain, user))
        # Filter projects
        if kwargs:
            self.logger.debug('=> filter project %s' % kwargs)
            project_list = list()
            for p in projects:
                for k,v in kwargs.iteritems():
                    if hasattr(p, k) and getattr(p, k) == v:
                        project_list.append(p)
            return project_list
        else:
            return projects

    def __get_users(self, domain=False, **kwargs):
        if domain:
            domain_id = self.__get_domain(domain)
            users = self.client.users.list(domain=domain_id, **kwargs)
            self.logger.debug('=> fetch users from domain %s' % domain)
        else:
            users = self.client.users.list(**kwargs)
        return users

    def __delete_instances(self, project):
        self.novaclient = Nova(config_path=self.config_path,
                               debug=self.debug,
                               log=self.logger,
                               region=self.region)
        self.novaclient.delete_project_instances(project.id)

    def __list_compute_quota(self, project):
        self.novaclient = Nova(config_path=self.config_path,
                               debug=self.debug,
                               log=self.logger,
                               region=self.region)
        return self.novaclient.list_quota(project.id)

    def __set_compute_quota(self, project, quota):
        self.novaclient = Nova(config_path=self.config_path,
                               debug=self.debug,
                               log=self.logger,
                               region=self.region)
        return self.novaclient.set_quota(project.id, quota)
