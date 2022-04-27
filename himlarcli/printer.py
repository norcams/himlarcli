from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.designate import Designate
from himlarcli.glance import Glance
from himlarcli import utils
from prettytable import PrettyTable
import re
import json
import operator
import sys
import csv
from collections import OrderedDict
import locale

locale.setlocale(locale.LC_ALL, 'en_DK.UTF-8')

class Printer(object):

    VALID_OPTIONS = ['text', 'json', 'csv']
    INDENT = 2

    def __init__(self, output_format):
        if output_format in self.VALID_OPTIONS:
            self.format = output_format
        else:
            sys.exit('Printer(): Unknown format %s' % output_format)

    def output_list_dicts(self, lists, sort=True, one_line=False):
        if self.format == 'text':
            self.__list_dicts_to_text(lists=lists, sort=sort, one_line=one_line)
        elif self.format == 'json':
            self.__list_dicts_to_json(lists=lists, sort=sort)
        elif self.format == csv:
            print('not implemented')

    def output_dict(self, objects, sort=True, one_line=False):
        if not isinstance(objects, dict):
            self.log_error('cannot output dict in printer. wrong object type')
            return
        if self.format == 'text':
            self.__dict_to_text(objects=objects, sort=sort, one_line=one_line)
        elif self.format == 'json':
            self.__dict_to_json(objects=objects, sort=sort)
        elif self.format == 'csv':
            self.__dict_to_csv(objects=objects, sort=sort)

    def output_msg(self, msg):
        if self.format == 'text':
            print("\n{}\n".format(msg))
        elif self.format == 'json':
            self.__dict_to_json(objects={'message': msg})
        elif self.format == 'csv':
            print("{};".format(msg))

    def __dict_to_json(self, objects, sort=True):
        if 'header' in objects:
            del objects['header']
        if objects:
            print(json.dumps(objects, sort_keys=sort, indent=self.INDENT))

    def __list_dicts_to_text(self, lists, sort=True, one_line=False):
        for obj in lists:
            self.__dict_to_text(obj, sort=sort, one_line=one_line)

    def __list_dicts_to_json(self, lists, sort=True):
        for obj in lists:
            self.__dict_to_json(obj, sort=sort)

    @staticmethod
    def __dict_to_text(objects, order_by=0, sort=True, one_line=False):
        if sort:
            sorted_objects = sorted(objects.items(), key=operator.itemgetter(order_by))
        else:
            sorted_objects = objects.items()
        if 'header' in objects:
            print("".ljust(80, "="))
            print("  %s" % objects['header'].ljust(76))
            print("".ljust(80, "="))
        out_line = str()
        for k, v in sorted_objects:
            if k == 'header':
                continue
            elif isinstance(v, list):
                print('%s =' % k)
                for i in v:
                    print("  %s" % i)
            elif one_line:
                out_line += '%s ' % v
            else:
                if isinstance(v, int) or isinstance(v, float):
                    value = '{:n}'.format(v)
                else:
                    value = v
                print("%s = %s" % (k, value))
        if out_line:
            print(out_line.strip())

    @staticmethod
    def __dict_to_csv(objects, order_by=0, sort=True):
        if 'header' in objects:
            del objects['header']
            print_header = True
        else:
            print_header = False
        writer = csv.DictWriter(sys.stdout,
                                fieldnames=objects.keys(),
                                dialect='excel')
        if objects:
            if print_header:
                writer.writeheader()
            if sort:
                sorted_objects = OrderedDict(sorted(objects.items()))
            else:
                sorted_objects = objects
            writer.writerow(sorted_objects)

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)

    @staticmethod
    def prettyprint_project_metadata(project, options, logger, regions, user=None):
        out_str = ''
        kc = Keystone(options.config, debug=options.debug)
        kc.set_dry_run(options.dry_run)
        kc.set_domain(options.domain)

        project_type = project.type if hasattr(project, 'type') else '(unknown)'
        project_admin = project.admin if hasattr(project, 'admin') else '(unknown)'
        project_created = project.createdate if hasattr(project, 'createdate') else '(unknown)'
        project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
        project_contact = project.contact if hasattr(project, 'contact') else 'None'
        project_roles = kc.list_roles(project_name=project.name)

        # Make project create date readable
        project_created = re.sub(r'T\d\d:\d\d:\d\d.\d\d\d\d\d\d', '', project_created)

        # Disabled project?
        status = "**DISABLED** " if not project.enabled else ''
        
        # Print header for project
        out_str += "%sPROJECT: %s" % (status, project.name)
        if user is not None and not options.admin:
            prole = 'admin' if user == project_admin else 'member'
            out_str += " (%s)" % prole
        out_str += "\n" + '=' * 80 + "\n"

        # Print project metadata
        table_metadata = PrettyTable()
        table_metadata._max_width = {'value' : 70}
        table_metadata.border = 0
        table_metadata.header = 0
        table_metadata.field_names = ['meta','value']
        table_metadata.align['meta'] = 'r'
        table_metadata.align['value'] = 'l'
        table_metadata.add_row(['ID:', project.id])
        table_metadata.add_row(['Admin:', project_admin])
        table_metadata.add_row(['Contact:', project_contact])
        table_metadata.add_row(['Type:', project_type])
        table_metadata.add_row(['Created:', project_created])
        table_metadata.add_row(['Enddate:', project_enddate])
        table_metadata.add_row(['Description:', project.description])
        if len(project_roles) > 0:
            users = dict()
            users['user'] = []
            users['object'] = []
            users['superuser'] = []
            for role in project_roles:
                user = role['group'].replace('-group', '').replace('-disabled', ' **DISABLED**')
                users[role['role']].append(user)
            table_metadata.add_row(['Users:', "\n".join(users['user'])])
            if len(users['superuser']) > 0:
                table_metadata.add_row(['Superusers:', "\n".join(users['superuser'])])
            if len(users['object']) > 0:
                table_metadata.add_row(['Object Users:', "\n".join(users['object'])])
        if not options.detail:
            zones     = Printer._count_project_zones(project, options, logger)
            volumes   = Printer._count_project_volumes(project, options, logger, regions)
            images    = Printer._count_project_images(project, options, logger, regions)
            instances = Printer._count_project_instances(project, options, logger, regions)
            volume_list   = []
            image_list    = []
            instance_list = []
            for region in regions:
                volume_list.append("%d (%s)" % (volumes[region], region))
                image_list.append("%d (%s)" % (images[region], region))
                instance_list.append("%d (%s)" % (instances[region], region))
            table_metadata.add_row(['Zones:', zones])
            table_metadata.add_row(['Volumes:', ', '.join(volume_list)])
            table_metadata.add_row(['Images:', ', '.join(image_list)])
            table_metadata.add_row(['Instances:', ', '.join(instance_list)])

        out_str += table_metadata.get_string() + "\n"
        return out_str

    @staticmethod
    def prettyprint_project_zones(project, options, logger):
        out_str = ''

        # Initiate Designate object
        dc = utils.get_client(Designate, options, logger)

        # Get Zones
        zones = dc.list_project_zones(project.id)

        # Print Zones table
        if len(zones) > 0:
            table_zones = PrettyTable()
            table_zones.field_names = ['id', 'name']
            table_zones.align['id'] = 'l'
            table_zones.align['name'] = 'l'
            for zone in zones:
                table_zones.add_row([zone['id'], zone['name']])
            out_str += "\n  Zones (%d): \n" % len(zones)
            out_str += table_zones.get_string() + "\n"

        return out_str

    @staticmethod
    def prettyprint_project_images(project, options, logger, regions):
        out_str = ''
        images_total = 0
        images = dict()

        # Get Images
        for region in regions:
            # Initiate Glance object
            gc = utils.get_client(Glance, options, logger, region)

            # Get a list of volumes in project
            filters = {'owner': project.id, 'visibility': 'private'}
            images[region] = gc.find_image(filters=filters)
            for i in images[region]:
                images_total += 1

        # Print Images table
        if images_total > 0:
            table_images = PrettyTable()
            table_images.field_names = ['id', 'name', 'created', 'size', 'type', 'owner', 'status', 'region']
            table_images.align['id'] = 'l'
            table_images.align['name'] = 'l'
            table_images.align['created'] = 'l'
            table_images.align['size'] = 'r'
            table_images.align['type'] = 'l'
            table_images.align['owner'] = 'l'
            table_images.align['status'] = 'l'
            table_images.align['region'] = 'l'
            for region in regions:
                for image in images[region]:
                    image_type = image.image_type if hasattr(image, 'image_type') else 'n/a'
                    image_owner = image.owner_user_name if hasattr(image, 'owner_user_name') else 'n/a'
                    image_size = "%d KiB" % (int(image.size) / 1024) if isinstance(image.size, int) else 'n/a'
                    table_images.add_row([image.id,
                                          image.name,
                                          image.created_at,
                                          image_size,
                                          image_type,
                                          image_owner,
                                          image.status,
                                          region])
            out_str += "\n  Images (%d): \n" % images_total
            out_str += table_images.get_string() + "\n"

        return out_str

    @staticmethod
    def prettyprint_project_volumes(project, options, logger, regions):
        out_str = ''
        volumes_total = 0
        volumes = dict()

        # Get Volumes
        for region in regions:
            # Initiate Cinder object
            cc = utils.get_client(Cinder, options, logger, region)

            # Get a list of volumes in project
            volumes[region] = cc.get_volumes(detailed=True, search_opts={'project_id': project.id})
            for i in volumes[region]:
                volumes_total += 1

        # Print Volumes table
        if volumes_total > 0:
            table_volumes = PrettyTable()
            table_volumes.field_names = ['id', 'size', 'type', 'status', 'region']
            table_volumes.align['id'] = 'l'
            table_volumes.align['size'] = 'r'
            table_volumes.align['type'] = 'l'
            table_volumes.align['status'] = 'l'
            table_volumes.align['region'] = 'l'
            for region in regions:
                for volume in volumes[region]:
                    table_volumes.add_row([volume.id, "%d GiB" % volume.size, volume.volume_type, volume.status, region])
            out_str += "\n  Volumes (%d): \n" % volumes_total
            out_str += table_volumes.get_string() + "\n"

        return out_str

    @staticmethod
    def prettyprint_project_instances(project, options, logger, regions):
        out_str = ''
        instances_total = 0
        instances = dict()

        # Get Instances
        for region in regions:
            # Initiate Nova object
            nc = utils.get_client(Nova, options, logger, region)

            # Get a list of instances in project
            instances[region] = nc.get_project_instances(project_id=project.id)
            for instance in instances[region]:
                instances_total += 1

        # Print Instances table
        if instances_total > 0:
            kc = Keystone(options.config, debug=options.debug)
            kc.set_dry_run(options.dry_run)
            kc.set_domain(options.domain)

            table_instances = PrettyTable()
            table_instances.field_names = ['id', 'name', 'status', 'owner', 'IPv4', 'IPv6',  'region', 'flavor', 'image [status]']
            table_instances.align['id'] = 'l'
            table_instances.align['name'] = 'l'
            table_instances.align['status'] = 'l'
            table_instances.align['owner'] = 'l'
            table_instances.align['IPv4'] = 'l'
            table_instances.align['IPv6'] = 'l'
            table_instances.align['region'] = 'l'
            table_instances.align['flavor'] = 'l'
            table_instances.align['image [status]'] = 'l'
            for region in regions:
                # Initiate Glance object
                gc = utils.get_client(Glance, options, logger, region)
                for instance in instances[region]:
                    if len(instance.addresses.keys()) > 0:
                        network = next(iter(instance.addresses))
                        ipv4_list = []
                        ipv6_list = []
                        for interface in instance.addresses[network]:
                            if interface['version'] == 4:
                                ipv4_list.append(interface['addr'])
                            if interface['version'] == 6:
                                ipv6_list.append(interface['addr'])
                        ipv4_addresses = ", ".join(ipv4_list)
                        ipv6_addresses = ", ".join(ipv6_list)
                    else:
                        ipv4_addresses = 'None'
                        ipv6_addresses = 'None'
                    if 'id' not in instance.image:
                        image_name = 'UNKNOWN'
                        image_status = 'N/A'
                    else:
                        filters = {'id': instance.image['id']}
                        image = gc.find_image(filters=filters, limit=1)
                        if len(image) == 1:
                            image_name = image[0]['name']
                            image_status = image[0]['status']
                        else:
                            image_name = 'UNKNOWN'
                            image_status = 'N/A'
                    user = kc.get_by_id('user', instance.user_id)
                    owner = user.name if user else '(deleted-user)'
                    row = []
                    row.append(instance.id)
                    row.append(instance.name)
                    row.append(instance.status)
                    row.append(owner)
                    row.append(ipv4_addresses)
                    row.append(ipv6_addresses)
                    row.append(region)
                    row.append(instance.flavor["original_name"])
                    row.append("%s [%s]" % (image_name, image_status))
                    table_instances.add_row(row)
            out_str += "\n  Instances (%d): \n" % instances_total
            out_str += table_instances.get_string() + "\n"

        return out_str

    @staticmethod
    def _count_project_zones(project, options, logger):
        # Initiate Designate object
        dc = utils.get_client(Designate, options, logger)

        # Get Zones
        zones = dc.list_project_zones(project.id)

        return len(zones)

    @staticmethod
    def _count_project_images(project, options, logger, regions):
        images = dict()

        # Get Images
        for region in regions:
            # Initiate Glance object
            gc = utils.get_client(Glance, options, logger, region)

            # Get a list of volumes in project
            filters = {'owner': project.id, 'visibility': 'private'}
            images[region] = len(gc.find_image(filters=filters))

        return images

    @staticmethod
    def _count_project_volumes(project, options, logger, regions):
        volumes = dict()

        # Get Volumes
        for region in regions:
            # Initiate Cinder object
            cc = utils.get_client(Cinder, options, logger, region)

            # Get a count of volumes in project
            volumes[region] = len(cc.get_volumes(search_opts={'project_id': project.id}))

        return volumes

    @staticmethod
    def _count_project_instances(project, options, logger, regions):
        instances = dict()

        # Get Instances
        for region in regions:
            # Initiate Nova object
            nc = utils.get_client(Nova, options, logger, region)

            # Get a list of instances in project
            instances[region] = len(nc.get_project_instances(project_id=project.id))

        return instances
