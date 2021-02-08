#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.mail import Mail
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from datetime import date

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

def action_list():
    projects = kc.get_projects(type='demo')
    printer.output_dict({'header': 'Demo project (instances, vcpus, volumes, gb, name)'})
    count = {'size': 0, 'vcpus': 0, 'instances': 0}
    for project in projects:
        ins_data = {'count': 0, 'vcpu': 0}
        vol_data = dict({'count': 0, 'size': 0})
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            cc = utils.get_client(Cinder, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            ins_data = {'count': 0, 'vcpus': 0}
            for i in instances:
                ins_data['vcpus'] += i.flavor['vcpus']
                ins_data['count'] += 1
            volumes = cc.get_volumes(detailed=True, search_opts={'project_id': project.id})
            for volume in volumes:
                vol_data['size'] += volume.size
                vol_data['count'] += 1
        output = {
            '5': project.name,
            '1': ins_data['count'],
            '2': ins_data['vcpus'],
            '3': vol_data['count'],
            '4': vol_data['size']
        }
        printer.output_dict(output, one_line=True)
        count['size'] += vol_data['size']
        count['vcpus'] += ins_data['vcpus']
        count['instances'] += ins_data['count']
    printer.output_dict({
        'header': 'Count',
        'instances': count['instances'],
        'volume_gb': count['size'],
        'vcpus': count['vcpus']})

def action_instances():
    projects = kc.get_projects(type='demo')
    printer.output_dict({'header': 'Demo instances (id, lifetime in days, name, flavor)'})
    count = 0
    for project in projects:
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            for i in instances:
                created = utils.get_date(i.created, None, '%Y-%m-%dT%H:%M:%SZ')
                output = {
                    '0': i.id,
                    '2': i.name,
                    '1': (date.today() - created).days,
                    '3': i.flavor['original_name']
                }
                count += 1
                printer.output_dict(output, one_line=True)
    printer.output_dict({'header': 'Count', 'count': count})

def action_expired():
    projects = kc.get_projects(type='demo')
    subject = '[NREC] Your instance is due for deletion'
    logfile = 'logs/demo-notify-expired-instances-{}.log'.format(date.today().isoformat())
    lognoneadmin = 'logs/demo-notify-expired-instances-noneadmin-{}.log'.format(date.today().isoformat())
    mail = utils.get_client(Mail, options, logger)
    fromaddr = mail.get_config('mail', 'from_addr')
    template = options.template
    if not options.template:
        utils.sys_error("Specify a template file. E.g. -t notify/demo-notify-expired-instances.txt")
    inputday = options.day
    if not options.day:
        utils.sys_error("Specify the number of days for running demo instances. E.g. -d 30")
    for project in projects:
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            for instance in instances:
                created = utils.get_date(instance.created, None, '%Y-%m-%dT%H:%M:%SZ')
                active_days = (date.today() - created).days
                if (int(active_days) >= int(inputday)):
                    print('----------------------------------------------------------------------------')
                    #printer.output_dict({'Region' : region.upper(), 'Project' : project.name, 'Instance': instance.name, 'Active days' : active_days})
                    mapping = dict(project=project.name, enddate=active_days, region=region.upper(), instance=instance.name)
                    body_content = utils.load_template(inputfile=template, mapping=mapping, log=logger)
                    msg = mail.get_mime_text(subject, body_content, fromaddr)
		    try:
                        if not options.dry_run:
			    if not utils.confirm_action('Send mail to instances that have been running for %s days?' %(inputday)):
                                return
                            mail.send_mail(project.admin, msg, fromaddr)
		            print("Mail sendt to {}".format(project.admin))
                            utils.append_to_logfile(logfile, date.today(), region, project.admin, instance.name)
                            #ToDo add exp volume and image
                    except:
                        print("Admin not found for %s" % project.name)
                        utils.append_to_logfile(lognoneadmin, date.today(), region, " ", instance.id)

                    #FIXME instances' tag 
		    #kc.update_project(project_id=project.id, notified=str(date.today()))

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
