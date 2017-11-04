from himlarcli.client import Client
from himlarcli.nova import Nova
from keystoneclient.v3 import client as keystoneclient
import keystoneauth1.exceptions as exceptions
import random
import string


class Keystone(Client):

    #version = 3

    def __init__(self, config_path, debug=False, log=None):
        super(Keystone, self).__init__(config_path, debug, log)
        self.client = keystoneclient.Client(session=self.sess,
                                            region_name=self.region)

    def get_client(self):
        return self.client

################################### DOMAIN #####################################

    def get_domain_id(self, domain):
        return self.__get_domain(domain)

################################## REGIONS #####################################

    def get_regions(self):
        return self.client.regions.list()

    def find_regions(self, region_name=None):
        region_list = list()
        regions = self.client.regions.list()
        for region in regions:
            if region_name and region_name == region.id:
                region_list.append(region.id)
                self.logger.debug('=> filter region: only use %s' % region_name)
                break
            elif not region_name:
                region_list.append(region.id)
        return region_list

#################################### OBJECTS ###################################

    def get_by_id(self, obj_type, obj_id):
        """ Get valid openstack object by type and id.
            version: 2 """
        valid_objects = ['project', 'group', 'user']
        if obj_type not in valid_objects:
            self.logger.debug('=> %s is not a valid object type' % obj_type)
            return dict()
        try:
            result = getattr(self.client, '%ss' % obj_type).get(obj_id)
        except exceptions.http.NotFound:
            self.logger.debug('=> %s with id %s not found' % (obj_type, obj_id))
            result = dict()
        return result

    def get_project_by_name(self, project_name, domain=None):
        domain_id = self.get_domain_id(domain)
        try:
            project = self.client.projects.list(domain=domain_id, name=project_name)
        except exceptions.http.NotFound:
            project = dict()
        if project:
            return project[0]
        return None

    def get_user_projects(self, email, domain=None, **kwargs):
        """
            Get project based on user group (based on email) and domain.
            Version: 2
            :param email: user email address (str)
            :param domain: domain name (str)
            :param kwargs: extra project fields to match for
            :return: a list of project objects
        """
        domain_id = self.get_domain_id(domain)
        user = self.get_user_by_email(email=email, user_type='api', domain=domain)
        projects = list()
        if user:
            try:
                projects = self.client.projects.list(domain=domain_id, user=user)
            except exceptions.http.NotFound:
                pass
        if not projects:
            self.logger.debug('=> no projects found for email %s' % email)
        project_list = list()
        for project in projects:
            for k, v in kwargs.iteritems():
                if hasattr(project, k) and getattr(project, k) == v:
                    project_list.append(project)
                elif not hasattr(project, k):
                    self.logger.debug('=> project %s do not have %s to filter' % (project.name, k))
            if not kwargs:
                project_list.append(project)
        return project_list

    def get_user_by_email(self, email, user_type, domain=None):
        """ Get dataporten (dp) or api user from email.
            version: 2 """
        domain_id = self.get_domain_id(domain)
        email = self.__get_uib_email(email)
        user = dict()
        if user_type == 'api':
            try:
                user = self.client.users.list(domain=domain_id, name=email)
            except exceptions.http.NotFound:
                user = dict()
        elif user_type == 'dp':
            users = self.client.users.list(domain=None)
            user_found = list()
            for user in users:
                # To find dataporten user we need to match email and domain = None
                if user.name == email and user.domain_id is None:
                    self.logger.debug('=> user %s found by email' % email)
                    user_found.append(user)
                    break
            if not user_found:
                self.logger.debug('=> no dataporten user found for email %s' % email)
            user = user_found
        if user:
            return user[0]
        return dict()

    def get_group_by_email(self, email, domain=None):
        """ Return group object based on email for user.
            version: 2 """
        domain_id = self.get_domain_id(domain)
        email = self.__get_uib_email(email)
        self.logger.debug('=> email used to find group %s' % email)
        group_name = self.__get_group_name(email)
        try:
            group = self.client.groups.list(domain=domain_id, name=group_name)
        except exceptions.http.NotFound:
            self.logger.debug('=> group %s not found' % group_name)
            group = dict()
        if group:
            return group[0]
        return None

    """
    Return all users, groups and project for this email """
    def get_user_objects(self, email, domain):
        domain_id = self.__get_domain(domain)
        obj = dict()
        api = self.get_user_by_email(email=email, user_type='api', domain=domain)
        if not api:
            self.logger.warning('=> could not find api user for email %s' % email)
        dp = self.get_user_by_email(email=email, user_type='dp', domain=None)
        if not dp:
            self.logger.warning('=> could not find dataporten user for email %s' % email)
        group = self.get_group_by_email(email, domain)
        obj['api'] = api
        obj['dataporten'] = dp
        obj['group'] = group
        if api:
            projects = self.client.projects.list(domain=domain_id, user=api)
        else:
            projects = []
        obj['projects'] = projects
        return obj

    def get_project_count(self, domain=False):
        projects = self.__get_projects(domain)
        return len(projects)

    def get_user_count(self, domain=False):
        users = self.__get_users(domain)
        return len(users)

    def get_users(self, domain=False, **kwargs):
        """ Safe way to get users. Use limit or filter to
            avoid running out of memory! """
        users = self.__get_users(domain, **kwargs)
        return users

    def get_project(self, project, domain=None):
        self.logger.debug('=> DEPRICATED: get_project() use get_project_by_name()')
        domain = self.__get_domain(domain)
        project = self.__get_project(project, domain=domain)
        return project

    def get_projects(self, domain=False, **kwargs):
        project_list = self.__get_projects(domain, **kwargs)
        return project_list

    """
    Check if a user has registered with access """
    def is_valid_user(self, email, domain=None):
        email = self.__get_uib_email(email)
        group = self.get_group_by_email(email, domain)
        return bool(group)

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

    def delete_project(self, project_name, domain=None):
        """
            Delete project based on name and all instances
            Version: 2
            :param project_name: name of project to delete
        """
        project = self.get_project_by_name(project_name=project_name, domain=domain)
        if not project:
            self.log_error('Project %s not found. Unable to delete project!' % project_name)
            return None
        self.__delete_instances(project, self.dry_run)
        if not self.dry_run:
            self.logger.debug('=> delete project %s' % project_name)
            return self.client.projects.delete(project)
        elif self.dry_run:
            self.logger.debug('=> DRY-RUN: delete project %s' % project_name)
            return None

    def remove_user(self, email, domain=None, dry_run=False):
        """ Remove all object related to this email """
        if not self.is_valid_user(email, domain):
            self.logger.debug('=> user %s is not valid. Dropping delete' % email)
            return False
        obj = self.get_user_objects(email=email, domain=domain)
        # Delete api user
        if not dry_run and 'api' in obj and obj['api']:
            self.logger.debug('=> delete api user %s' % obj['api'].name)
            self.client.users.delete(obj['api'])
        elif dry_run:
            self.logger.debug('=> DRY-RUN: delete api user %s' % obj['api'].name)
        # Delete dataporten user
        if not dry_run and 'dataporten' in obj and obj['dataporten']:
            self.logger.debug('=> delete dataporten user %s' % obj['dataporten'].name)
            self.client.users.delete(obj['dataporten'])
        elif dry_run and 'dataporten' in obj:
            self.logger.debug('=> DRY-RUN: delete dataporten user %s' % obj['dataporten'].name)
        # Delete group
        if not dry_run and 'group' in obj and obj['group']:
            self.logger.debug('=> delete group %s' % obj['group'].name)
            self.client.groups.delete(obj['group'])
        elif dry_run:
            self.logger.debug('=> DRY-RUN: delete group %s' % obj['group'].name)
        # Delete demo/personal projects and instances
        if 'projects' in obj:
            for project in obj['projects']:
                if not hasattr(project, 'type'):
                    self.logger.debug('=> unknown project type %s' % project.name)
                elif project.type == 'demo' or project.type == 'peronal':
                    self.logger.debug('=> delete instances from %s' % project.name)
                    self.__delete_instances(project, dry_run)
                    if not dry_run:
                        self.logger.debug('=> delete project %s' % project.name)
                        self.client.projects.delete(project)
                    else:
                        self.logger.debug('=> DRY-RUN: delete project %s' % project.name)
                else:
                    self.logger.debug('=> project type not demo or personal %s' % project.name)

        return True

    def rename_user(self, new_email, old_email, domain=None, dry_run=False):
        obj = self.get_user_objects(email=old_email, domain=domain)
        # Rename api user
        if not dry_run and 'api' in obj and obj['api']:
            self.logger.debug('=> rename api user to %s' % new_email.lower())
            self.client.users.update(user=obj['api'], name=new_email.lower())
        elif dry_run:
            self.logger.debug('=> DRY-RUN: rename api user to %s' % new_email.lower())
        # Delete dataporten user
        if not dry_run and 'dataporten' in obj and obj['dataporten']:
            self.logger.debug('=> delete old dataporten user %s' % old_email)
            self.client.users.delete(user=obj['dataporten'])
        elif dry_run and 'dataporten' in obj:
            self.logger.debug('=> DRY-RUN: delete old dataporten user %s' % old_email)
        # Rename group
        if not dry_run and 'group' in obj and obj['group']:
            new_group_mail = self.__get_group_name(self.__get_uib_email(new_email))
            self.logger.debug('=> rename group to %s' % new_group_mail)
            self.client.groups.update(group=obj['group'], name='%s' % new_group_mail)
        elif dry_run:
            self.logger.debug('=> DRY-RUN: rename group to %s-group' % new_email)
        if not dry_run:
            # Rename old peronal project
            old_project_name = self.get_project_name(old_email, 'PRIVATE')
            new_project_name = self.get_project_name(new_email, 'PRIVATE')
            self.logger.debug('=> rename %s to %s', old_project_name, new_project_name)
            project = self.get_project_by_name(project_name=old_project_name,
                                               domain=domain)
            if project:
                self.client.projects.update(project=project, name=new_project_name)
        elif dry_run:
            self.logger.debug('=> DRY-RUN: rename project to %s' % new_email)

    def reset_password(self, email, domain=None, dry_run=False):
        obj = self.get_user_objects(email=email, domain=domain)
        password = self.generate_password()
        if not dry_run and 'api' in obj and obj['api']:
            self.logger.debug('=> reset password for user %s' % email)
            self.client.users.update(obj['api'], password=password)
        elif dry_run:
            self.logger.debug('=> DRY-RUN: reset password for user %s' % email)
        else:
            print 'Reset password failed! User %s not found.' % email
            return
        print "New password: %s" % password


    def grant_role(self, email, project_name, role='user', domain=None):
        """ Grant a role to a project for a user.
            version: 2 """
        if not self.dry_run:
            project = self.get_project_by_name(project_name=project_name, domain=domain)
        if not self.dry_run and not project:
            self.log_error("could not find project %s" % project_name, 1)
        group = self.get_group_by_email(email=email, domain=domain)
        if not group:
            self.log_error('Group %s-group not found!'  % email)
            return
        role = self.__get_role(role)
        try:
            if not self.dry_run:
                exists = self.client.roles.list(project=project, group=group)
            else:
                exists = None
        except exceptions.http.NotFound:
            exists = None
        self.logger.debug('=> grant role %s to %s for %s' % (role.name, email, project_name))
        if exists:
            self.log_error('Access exist for %s in project %s' % (email, project_name))
        elif self.dry_run:
            data = {'user':group.name, 'project': project_name, 'role':role.name}
            self.log_dry_run(function='grant_role', **data)
        else:
            self.client.roles.grant(role=role,
                                    project=project,
                                    group=group)

    def list_roles(self, project_name, domain=None):
        """ List all roles for a project based on project name.
            version: 2 """
        project = self.get_project_by_name(project_name=project_name, domain=domain)
        roles = self.client.role_assignments.list(project=project)
        role_list = list()
        for role in roles:
            group = self.get_by_id('group', role.group['id']) if hasattr(role, 'group') else None
            role = self.client.roles.get(role.role['id']) if hasattr(role, 'role') else None
            if hasattr(group, 'name'):
                role_list.append(dict({'group': group.name, 'role': role.name}))
            else:
                self.logger.debug('=> could not find group %s' % (role.group['id']))
        return role_list

    def update_project(self, project_id, project_name=None, description=None, **kwargs):
        if self.dry_run:
            data = kwargs.copy()
            data.update({'id': project_id})
            if project_name:
                data['name'] = project_name
            if description:
                data['description'] = description
            self.log_dry_run('update_project', **data)
            return
        try:
            project = self.client.projects.update(project=project_id,
                                                  name=project_name,
                                                  description=description,
                                                  **kwargs)
            self.logger.debug('=> updated project %s' % project.name)
        except exceptions.http.BadRequest as e:
            self.log_error(e)
            self.log_error('Project %s not updated' % project_id)

    def create_project(self, domain, project_name, admin=None, description=None, **kwargs):
        """
        Create new project in domain and grant user role to admin if valid user.
        Works with dry_run
        version: 2

        :return: dictionary with project data
        """
        parent_id = self.__get_domain(domain)
        project_found = self.get_project_by_name(project_name=project_name, domain=domain)
        grant_role = True if admin and self.is_valid_user(admin, domain) else False
        if project_found:
            #self.logger.debug('=> project %s exists' % project)
            self.log_error("WARNING: project %s exists!" % project_name)
            return None
        if self.dry_run:
            data = kwargs.copy()
            data.update({'domain': domain, 'name': project_name, 'description': description})
            self.log_dry_run('create_project', **data)
        else:
            try:
                project = self.client.projects.create(name=project_name,
                                                      domain=parent_id,
                                                      parent=parent_id,
                                                      enabled=True,
                                                      description=description,
                                                      admin=admin,
                                                      **kwargs)
                self.logger.debug('=> create new project %s' % project_name)
            except exceptions.http.BadRequest as e:
                self.log_error(e)
                self.log_error('Project %s not created' % project_name)
        if grant_role:
            self.grant_role(project_name=project_name, email=admin, domain=domain)
        if self.dry_run:
            return data
        return project

    """
    Federation settings for identity provider """
    def set_identity_provider(self, name, remote_id):
        providers = self.client.federation.identity_providers.list()
        for i in providers:
            if name == i.id:
                self.logger.debug('=> identity provider %s exists' % name)
                return
        self.client.federation.identity_providers.create(id=name,
                                                         enabled=True,
                                                         remote_ids=[remote_id])

    """
    Federation settings for identity mappping """
    def set_mapping(self, id, rules):
        mappings = self.client.federation.mappings.list()
        for i in mappings:
            if id == i.id:
                self.logger.debug('=> mapping %s exists' % id)
                return
        self.client.federation.mappings.create(mapping_id=id, rules=rules)

    """
    Federation settings for protocol container """
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
        project = None
        if not self.__get_group(group=name, domain=domain):
            project = self.client.groups.create(name=name,
                                                domain=domain,
                                                description=description)
        return project

    @staticmethod
    def generate_password(size=16, chars=None):
        if not chars:
            chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(size))

    @staticmethod
    def get_project_name(email, prefix='DEMO'):
        project_name = email.lower().replace('@', '.')
        project_name = '%s-%s' % (prefix, project_name)
        return project_name

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

    def __get_group(self, group, domain=None, user=None):
        """ Return FIRST group that maches group name """
        groups = self.client.groups.list(domain=domain, user=user)
        for g in groups:
            if g.name == group:
                self.logger.debug('=> group %s found' % group)
                return g
        self.logger.debug('=> group %s NOT found' % group)
        return None

    """ Return domain ID
    """
    def __get_domain(self, domain):
        domain = self.client.domains.list(name=domain)
        if len(domain) > 0:
            return domain[0].id
        else:
            return False

    def __get_projects(self, domain=False, **kwargs):
        domain_id = self.__get_domain(domain) if domain else None
        projects = self.client.projects.list(domain=domain_id)
        self.logger.debug('=> get projects (domain=%s)' % (domain))
        # Filter projects
        if kwargs:
            self.logger.debug('=> filter project %s' % kwargs)
            project_list = list()
            for p in projects:
                for k, v in kwargs.iteritems():
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

    def __delete_instances(self, project, dry_run=False):
        """ Use novaclient to delete all instances for a project """
        novaclient = Nova(config_path=self.config_path,
                          debug=self.debug,
                          log=self.logger,
                          region=self.region)
        novaclient.delete_project_instances(project, dry_run)

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

    @staticmethod
    def __get_group_name(email):
        """ Map email for user to group name.
            The groups are created in himlar-dp_prep. """
        return '%s-group' % email

    @staticmethod
    def __get_uib_email(email):
        if not email or 'uib.no' not in email or '@' not in email:
            return email
        (user, domain) = email.split('@')
        return '%s@%s' % (user.title(), domain)
