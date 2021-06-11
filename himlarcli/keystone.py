from himlarcli.client import Client
from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.glance import Glance
from himlarcli.designate import Designate
from keystoneclient.v3 import client as keystoneclient
import keystoneauth1.exceptions as exceptions
import random
import string
import re

# pylint: disable=R0904
class Keystone(Client):

    #version = 3

    def __init__(self, config_path, debug=False, log=None):
        super(Keystone, self).__init__(config_path, debug, log)
        self.client = keystoneclient.Client(session=self.sess,
                                            region_name=self.region)
        self.domain_id = None

    def get_client(self):
        return self.client

################################### DOMAIN #####################################

    def get_domain_id(self):
        if not self.domain_id:
            self.logger.warning('=> domain id not set in script')
        return self.domain_id

    def set_domain(self, domain):
        self.domain_id = self.__get_domain(domain)

    def get_dataporten_domain(self):
        """
        This will find the auto generated dataporten domain used federated users
        version: 2019-8
        """
        domain_desc = ('Auto generated federated domain for '
                       'Identity Provider: dataporten')
        domains = self.client.domains.list()
        for domain in domains:
            if domain.description == domain_desc:
                return domain
        return None

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
        """
            Get valid openstack object by type and id.
            version: 2
            :rtype: object (?)
        """
        valid_objects = ['project', 'group', 'user']
        if obj_type not in valid_objects:
            self.logger.debug('=> %s is not a valid object type' % obj_type)
            return None
        try:
            result = getattr(self.client, '%ss' % obj_type).get(obj_id)
        except exceptions.http.NotFound:
            self.logger.debug('=> %s with id %s not found' % (obj_type, obj_id))
            result = None
        return result

    def get_project_by_name(self, project_name):
        domain_id = self.get_domain_id()
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
        domain_id = self.get_domain_id()
        user = self.get_user_by_email(email=email, user_type='api')
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

    def get_user_by_email(self, email, user_type):
        """ Get dataporten (dp) or api user from email.
            version: 2019-8
            :return: user object
            :rtype: keystoneclient.v3.users.User
        """
        email = self.__get_uib_email(email)
        if user_type == 'api':
            domain = self.domain_id
        elif user_type == 'dp':
            domain = self.get_dataporten_domain()
        else:
            domain = None
        user = None
        try:
            users = self.client.users.list(domain=domain, name=email)
            if len(users) > 0:
                user = users[0]
        except exceptions.http.NotFound as e:
            #self.debug_log(e)
            user = None
        if not user:
            self.debug_log('no %s user found for email %s' % (user_type, email))
        return user

    def get_group_by_email(self, email):
        """ Return group object based on email for user.
            version: 2 """
        domain_id = self.get_domain_id()
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
        api = self.get_user_by_email(email=email, user_type='api')
        if not api:
            self.logger.warning('=> could not find api user for email %s' % email)
        dp = self.get_user_by_email(email=email, user_type='dp')
        if not dp:
            self.logger.warning('=> could not find dataporten user for email %s' % email)
        group = self.get_group_by_email(email)
        obj['api'] = api
        obj['dataporten'] = dp
        obj['group'] = group
        if api:
            projects = self.client.projects.list(domain=domain_id, user=api)
        else:
            projects = []
        obj['projects'] = projects
        return obj

    def update_user(self, user_id, **kwargs):
        """ Update user
            version: 2018-12 """
        self.debug_log('update user: %s' % kwargs)
        if not self.dry_run:
            self.client.users.update(user=user_id, **kwargs)

    def get_project_count(self, domain=False):
        projects = self.__get_projects(self.domain_id)
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

    def get_all_projects(self):
        """ Return all project in current domain
            version: 2019-09
        """
        projects = self.client.projects.list(domain=self.domain_id)
        self.debug_log('get all project from domain %s' % self.domain_id)
        return projects

    def get_projects(self, **kwargs):
        """ Get projects with filter. E.G. type=demo, or test=1
            version: 2019-09 """
        project_list = self.__get_projects(domain_id=self.domain_id, **kwargs)
        return project_list

    """
    Check if a user has registered with access """
    def is_valid_user(self, email, domain=None):
        email = self.__get_uib_email(email)
        group = self.get_group_by_email(email)
        return bool(group)

    def list_users(self, domain=False, **kwargs):
        user_list = self.__get_users(domain, **kwargs)
        users = list()
        for i in user_list:
            users.append(i.name)
        return users

    def list_projects(self, domain=False, **kwargs):
        domain_id = self.get_domain_id(domain)
        project_list = self.__get_projects(domain_id, **kwargs)
        projects = list()
        for i in project_list:
            projects.append(i.name)
        return projects

    def list_quota(self, project, domain=None):
        domain = self.__get_domain(domain)
        project = self.__get_project(project, domain=domain)
        compute = self.__list_compute_quota(project)
        return dict({'compute':compute})

############################# DELETE FUNCTIONS ################################

    def delete_project(self, project_name, region=None):
        """
            Delete project based on name and all instances
            Version: 2019-11
            :param project_name: name of project to delete
            :param region: region name to delete project resources (None = all)
        """
        project = self.get_project_by_name(project_name=project_name)
        if not project:
            self.logger.debug('=> could not delete project %s: not found',
                              project_name)
            return None
        if not region:
            region = self.find_regions()

        # Delete DNS zones
        deleted_zones = self.__delete_zones(project)

        # Delete instances
        self.__delete_instances(project, region)

        # Revoke shared image memberships
        revoked_images = self.__revoke_image_shares(project, region)

        # Delete images
        self.__delete_images(project, region)

        # Delete security groups
        self.__delete_security_groups(project, region)

        # Delete volume
        self.__delete_volumes(project, region)

        self.debug_log('delete project %s' % project_name)
        if not self.dry_run:
            return self.client.projects.delete(project)
        return None

    def delete_user(self, email, user_type):
        """
            Delete user by email if found
            Version: 2018-1
            :param email: user email or username if fake email
        """
        user = self.get_user_by_email(email, user_type)
        if not user:
            self.logger.debug('=> could not find user %s of type %s',
                              email, user_type)
            return
        self.debug_log('delete user %s of type %s' % (email, user_type))
        if not self.dry_run:
            self.client.users.delete(user)

    def delete_group(self, email):
        """
            Delete group by email if found
            Version: 2018-1
            :param email: user email or username if fake email
        """
        group = self.get_group_by_email(email)
        if not group:
            self.logger.debug('=> could not find group for email %s ', email)
            return
        self.debug_log('delete group %s' % group.name)
        if not self.dry_run:
            self.client.groups.delete(group)

    def user_cleanup(self, email):
        """
            Remove user objects.
            Version: 2018-1
            :param email: user email or username if fake email
        """
        self.delete_user(email, 'api')
        self.delete_user(email, 'dp')
        self.delete_group(email)

        # Delete demo project
        self.delete_project(self.get_project_name(email, prefix='DEMO'))
        # Delete personal project
        self.delete_project(self.get_project_name(email, prefix='PRIVATE'))

    def rename_user(self, new_email, old_email):
        """
            Rename user objects:
            * rename api user
            * rename group (will keep project membership)
            * delete dataporten user (autocreates on new login)
            * rename demo project
            * rename personal project
            Version: 2018-1
        """
        changes = {'api': {}, 'group': {}, 'projects': {}}
        # Rename api user
        api = self.get_user_by_email(old_email, 'api')
        if not api:
            self.log_error('Could not find api user for %s!', old_email)
        self.debug_log('rename api user from %s to %s' % (old_email, new_email))
        if not self.dry_run:
            self.client.users.update(user=api,
                                     name=new_email.lower(),
                                     email=new_email.lower())
        changes['api'][api.name] = new_email.lower()
        # Rename group
        group = self.get_group_by_email(old_email)
        if not group:
            self.log_error('Could not find group for user %s!', old_email)
        new_group_name = self.__get_group_name(self.__get_uib_email(new_email))
        self.debug_log('rename group from %s to %s' % (group.name, new_group_name))
        if not self.dry_run:
            self.client.groups.update(group=group, name='%s' % new_group_name)
        changes['group'][group.name] = new_group_name
        # Delete dataporten user
        self.delete_user(old_email, 'dp')
        # Rename old peronal project
        personal = self.get_project_by_name(
            self.get_project_name(old_email, prefix='PRIVATE'))
        new_personal_name = self.get_project_name(new_email, prefix='PRIVATE')
        if personal:
            self.debug_log('rename personal project from %s to %s'
                           % (personal.name, new_personal_name))
            if not self.dry_run:
                self.client.projects.update(project=personal,
                                            admin=new_email,
                                            name=new_personal_name)
            changes['projects'][personal.name] = new_personal_name
        # Rename old demo project
        new_demo_name = self.get_project_name(new_email, prefix='DEMO')
        demo = self.get_project_by_name(
            self.get_project_name(old_email, prefix='DEMO'))
        if demo:
            self.debug_log('rename demo project from %s to %s'
                           % (demo.name, new_demo_name))
            if not self.dry_run:
                self.client.projects.update(project=demo,
                                            admin=new_email,
                                            name=new_demo_name)
            changes['projects'][demo.name] = new_demo_name
        return changes

    def reset_password(self, email, password=None):
        """
            Change password for api user
            Version: 2018-7
        """
        dry_run_txt = 'DRY-RUN: ' if self.dry_run else ''
        user = self.get_user_by_email(email=email, user_type='api')
        if password == None:
            password = self.generate_password()
        if not user:
            self.logger.warning('Reset password failed! User %s not found.', email)

        self.logger.debug('=> %sreset password for user %s', dry_run_txt, email)
        if not self.dry_run:
            self.client.users.update(user, password=password)

        return "New password: %s" % password

    def revoke_role(self, emails, project_name, role_name='user'):
        """
            Revoke role for user in project
            version: 2019-3
            :param email: list of user email address (str)
        """
        project = self.get_project_by_name(project_name=project_name)
        if not project:
            self.log_error("could not find project %s" % project_name, 1)
        role = self.__get_role(role_name)
        if not role:
            self.log_error('Role %s not found!'  % role_name)
            return
        assignments = self.__get_role_assignments(project_id=project.id, role_id=role.id)
        for email in emails:
            group = self.get_group_by_email(email=email)
            if not group:
                self.log_error('Group %s-group not found!'  % email)
                continue
            if group.name not in assignments:
                self.debug_log('%s not found in assignments. dropping revoke' % group.name)
                continue
            self.debug_log('revoke role %s to %s for %s' % (role.name, email, project_name))
            if not self.dry_run:
                try:
                    self.client.roles.revoke(role=role,
                                             project=project,
                                             group=group)
                except exceptions.base.ClientException as e:
                    self.log_error(e)

    def grant_role(self, email, project_name, role_name='user'):
        """ Grant a role to a project for a user.
            version: 2 """
        if not self.dry_run:
            project = self.get_project_by_name(project_name=project_name)
        if not self.dry_run and not project:
            self.log_error("could not find project %s" % project_name, 1)
        if '-group' in email:
            group = self.__get_group(email)
        else:
            group = self.get_group_by_email(email=email)
        if not group:
            self.log_error('Group %s-group not found!'  % email)
            return
        role = self.__get_role(role_name)
        if not role:
            self.log_error('Role %s not found!'  % role_name)
            return
        exists = None
        try:
            if not self.dry_run:
                roles = self.client.roles.list(project=project, group=group)
                for r in roles:
                    if r.name == role.name:
                        exists = True
                        continue
        except exceptions.http.NotFound as e:
            self.log_error(e)
        self.logger.debug('=> grant role %s to %s for %s', role.name, email, project_name)
        if exists:
            self.log_error('Role %s exist for %s in project %s' % (role.name, email, project_name))
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
        project = self.get_project_by_name(project_name=project_name)
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

    def create_project(self, project_name, admin=None, description=None, **kwargs):
        """
        Create new project in domain and grant user role to admin if valid user.
        Works with dry_run and domain
        version: 2018-1

        :return: dictionary with project data
        """
        if description:
            description = self.convert_ascii(description)
        parent_id = self.domain_id
        project_found = self.get_project_by_name(project_name=project_name)
        grant_role = True if admin and self.is_valid_user(admin, parent_id) else False
        if project_found:
            #self.logger.debug('=> project %s exists' % project)
            self.log_error("WARNING: project %s exists!" % project_name)
            return None
        if self.dry_run:
            data = kwargs.copy()
            data.update({'domain': parent_id, 'name': project_name, 'description': description})
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
                return None
        if grant_role:
            self.grant_role(project_name=project_name, email=admin)
        if self.dry_run:
            return data
        return project

    def create_user(self, name, email, password=None, user_type='api', **kwargs):
        """
        Create a new group and a new local user for the group.
        version: 2

        :return: clear text password for the new user
        """
        if not self.__validate_email(email.lower()):
            self.log_error('%s is not a valid email address' % email)
            return
        domain = self.domain_id
        group_name = self.__get_group_name(name)
        username = name.lower()
        if not password:
            password = self.generate_password()
        group = user = None

        # Create group
        try:
            if not self.dry_run:
                group = self.client.groups.create(name=group_name, domain=domain)
                self.logger.debug('=> create group %s', group.to_dict())
            else:
                self.log_dry_run('create group', **{'name': group_name})
        except exceptions.http.BadRequest as e:
            self.log_error(e)
            return
        except exceptions.http.Conflict as e:
            self.logger.debug('=> create group %s already exists', group_name)

        # Create user
        try:
            if not self.dry_run:
                user = self.client.users.create(name=username,
                                                domain=domain,
                                                email=email.lower(),
                                                type=user_type,
                                                password=password,
                                                **kwargs)
                self.logger.debug('=> create user %s', user.to_dict())
            else:
                data = kwargs.copy()
                data.update({
                    'name': username,
                    'email': email.lower(),
                    'type': user_type})
                self.log_dry_run('create user', **data)
        except exceptions.http.BadRequest as e:
            self.log_error(e)
            return
        except exceptions.http.Conflict as e:
            self.logger.debug('=> user %s already exists', name)
            password = None
        # Add to group
        try:
            if not self.dry_run and user and group:
                self.client.users.add_to_group(user=user, group=group)
        except exceptions.http.BadRequest as e:
            self.log_error(e)
            return
        if password:
            print "New password: %s" % password

    def provision_dataporten(self, email, password):
        """
        Create a api user and demo project for a dataporten user.
        Version: 2018-6
        """
        self.logger.debug('=> provsion new dataporten user %s', email)
        self.create_user(name=email, email=email, password=password)
        project_name = self.get_project_name(email)
        desc = "Personal demo project for %s. Resources might be terminated at any time" % email.lower()
        project = self.create_project(project_name=project_name,
                                      admin=email.lower(),
                                      type='demo',
                                      description=desc)

    def set_identity_provider(self, name, remote_id, description):
        """
            Create identity provider
            version: 2020-01
        """
        try:
            self.client.federation.identity_providers.find(id=name)
            self.debug_log('identity provider {} exists'.format(name))
            return
        except exceptions.http.NotFound:
            pass
        self.debug_log('create identity_provider {}'.format(name))
        if self.dry_run:
            return
        self.client.federation.identity_providers.create(id=name,
                                                         enabled=True,
                                                         remote_ids=[remote_id],
                                                         description=description)

    def set_mapping(self, mapping_id, rules):
        """
            Create federated identity mapping
            version: 2020-01
        """
        try:
            self.client.federation.mappings.find(id=mapping_id)
            self.debug_log('mapping {} exists'.format(mapping_id))
            return
        except exceptions.http.NotFound:
            pass
        self.debug_log('create identity mapping {}'.format(mapping_id))
        if not self.dry_run:
            self.client.federation.mappings.create(mapping_id=mapping_id,
                                                   rules=rules)

    def set_protocol(self, protocol_id, provider, mapping):
        """
            Create federation protocol for identity provider
            version: 2020-01
        """
        try:
            self.client.federation.protocols.find(id=protocol_id)
            self.debug_log('federation protocol {} exists'.format(protocol_id))
            return
        except exceptions.http.NotFound:
            pass
        self.debug_log('create federation protocol {} for provider {}'
                       .format(protocol_id, provider))
        if not self.dry_run:
            self.client.federation.protocols.create(protocol_id,
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

    def __get_role_assignments(self, project_id, role_id=None, rvalue = 'group', vtype = 'name'):
        """
            Return a list of groups assigned to a project with a role
            version: 2019-3
            :param rvalue: return value, user or group (str)
            :param vtype: retrun value type, id or name (str)
        """
        include_names = True if vtype == 'name' else False
        assignments = self.client.role_assignments.list(project=project_id,
                                                        role=role_id,
                                                        include_names=include_names)
        rlist = list()
        for a in assignments:
            if hasattr(a, rvalue):
                value = getattr(a, rvalue)
                if vtype in value:
                    rlist.append(value[vtype])
        return rlist

    def __get_role(self, role_name):
        """
        Get the role object based on the role name and domain.
        Version: 2018-6
        :return the role object or None if not found
        :rtype: keystoneclient.v3.roles.Role
        """
        try:
            role = self.client.roles.find(name=role_name, domain=self.domain_id)
        except exceptions.http.NotFound as e:
            self.logger.debug('=> role %s NOT found' % role_name)
            role = None
        return role

    def __get_group(self, group, domain=None, user=None):
        """ Return FIRST group that maches group name """
        groups = self.client.groups.list(domain=domain, user=user)
        for g in groups:
            if g.name == group:
                self.logger.debug('=> group %s found' % group)
                return g
        self.logger.debug('=> group %s NOT found' % group)
        return None

    def __get_domain(self, domain):
        """ Get domain id from name """
        try:
            domain_obj = self.client.domains.find(name=domain)
        except exceptions.http.NotFound:
            self.debug_log('could not find domain {}'.format(domain))
            domain_obj = None
        except exceptions.connection.ConnectFailure as e:
            self.log_error('connection failure: {}'.format(e), 1)
        return domain_obj.id if domain_obj else None

    def __get_projects(self, domain_id, **kwargs):
        projects = self.client.projects.list(domain=domain_id)
        self.logger.debug('=> get projects (domain=%s)' % (domain_id))
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

    def __delete_instances(self, project, region):
        """ Use novaclient to delete all instances for a project in
            one or more regions
            version: 2019-10 """
        regions = [region] if not isinstance(region, list) else region
        for region in regions:
            nc = self._get_client(Nova, region)
            nc.delete_project_instances(project, self.dry_run)

    def __delete_zones(self, project):
        """ Use designateclient to delete all zones belonging to a project
            version: 2021-06 """

        # Initiate Designate object
        dc = self._get_client(Designate)

        # Get a list of zones belonging to project
        zones = dc.list_project_zones(project.id)

        # Delete the zones, collecting the names of the deleted zones
        deleted_zones = []
        for zone in zones:
            if not self.dry_run:
                dc.delete_project_zone(zone['id'], project.id)
            self.debug_log('DELETED zone: {}'. format(zone['name']))
            deleted_zones.append(zone['name'])

        # Return a list of deleted zone names
        return deleted_zones

    def __revoke_image_shares(self, project, region):
        """ Use glanceclient to revoke membership for any shared images that
            are shared to this project, for all regions
            version: 2021-06 """
        regions = [region] if not isinstance(region, list) else region
        for region in regions:
            gc = self._get_client(Glance, region)

            # Find all shared images
            filters = {
                'member_status': 'accepted',
                'visibility':    'shared'
            }
            images = gc.get_images(filters=filters)

            # Remove image member status for images shared to this project
            revoked_images = []
            for image in images:
                members = gc.get_image_access(image_id=image.id)
                for member in members:
                    if member.member_id == project.id:
                        if not self.dry_run:
                            gc.set_image_access(image_id=image.id, project_id=project.id, action='revoke')
                        self.debug_log('REVOKED access to image: {} ({})'. format(image.name, region))
                        revoked_images.append("%s (%s)" % (image.name, region))

            # Return a list of revoked images
            return revoked_images

    def __delete_images(self, project, region):
        """ Use glanceclient to delete all private images for a project in
            one or more regions
            version: 2019-10 """
        regions = [region] if not isinstance(region, list) else region
        for region in regions:
            gc = self._get_client(Glance, region)
            gc.delete_private_images(project.id)

    def __delete_security_groups(self, project, region):
        """ Use neutronclient to delete all security groups for a project in
            one or more regions
            version: 2019-10 """
        regions = [region] if not isinstance(region, list) else region
        for region in regions:
            nc = self._get_client(Neutron, region)
            nc.purge_security_groups(project)

    def __delete_volumes(self, project, region):
        """ Use cinder client to delete all project volumes in one or all regions
            version: 2019-11 """
        regions = [region] if not isinstance(region, list) else region
        for region in regions:
            cc = self._get_client(Cinder, region)
            cc.purge_project_volumes(project.id)

    def __list_compute_quota(self, project):
        self.novaclient = Nova(config_path=self.config_path,
                               debug=self.debug,
                               log=self.logger,
                               region=self.region)
        return self.novaclient.get_quota(project.id)

    def __set_compute_quota(self, project, quota):
        self.novaclient = Nova(config_path=self.config_path,
                               debug=self.debug,
                               log=self.logger,
                               region=self.region)
        return self.novaclient.set_quota(project.id, quota)

    @staticmethod
    def get_user_org(email):
        if not "@" in email:
            return None
        domain = email.split("@")[1]
        if domain and "." in domain:
            return domain.split(".")[-2]
        return None

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

    @staticmethod
    def __validate_email(email):
        match = r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$'
        if re.match(match, email) != None:
            return True
        return False
