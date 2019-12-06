#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils
from himlarcli.mail import Mail
from datetime import datetime, date, timedelta
import re

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

regions = kc.find_regions()

def action_disable():
    projects = kc.get_projects()
    subject = '[UH-IaaS] Your project is due for deletion'
    logfile = 'logs/expired-disabled-{}.log'.format(date.today().isoformat())
    if options.template:
        template = options.template
    else:
        template = 'notify/notify_expired_last.txt'
    mail = utils.get_client(Mail, options, logger)
    fromaddr = mail.get_config('mail', 'from_addr')
    for project in projects:
        project = expired_project(project)
        if not project:
            continue

        # Allow 30 days gracetime before we disable
        disabled_date = utils.get_date(project.notified, None, '%Y-%m-%d')
        gracetime = timedelta(30)
        if date.today() - disabled_date < gracetime:
            continue

        # stop instances
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            for i in instances:
                if i.status == 'ACTIVE':
                    i.stop()

        mapping = dict(project=project.name, enddate=project.enddate)
        body_content = utils.load_template(inputfile=template,
                                           mapping=mapping,
                                           log=logger)
        msg = mail.get_mime_text(subject, body_content, fromaddr)
        mail.send_mail(project.admin, msg, fromaddr)
        print "mail sendt to {}".format(project.admin)
        if not options.dry_run:
            utils.append_to_file(logfile, project.admin)
        # Add metadata to project for the time of project disable
        kc.update_project(project_id=project.id, enabled=False,
                          disabled=str(date.today()))

def action_notify():
    projects = kc.get_projects()
    subject = '[UH-IaaS] Your project has expired'
    logfile = 'logs/expired-notify-{}.log'.format(date.today().isoformat())
    mail = utils.get_client(Mail, options, logger)
    fromaddr = mail.get_config('mail', 'from_addr')
    if options.template:
        template = options.template
    else:
        template = 'notify/notify_expired_first.txt'
    for project in projects:
        project = expired_project(project)
        if not project or hasattr(project, 'notified'):
            continue
        mapping = dict(project=project.name, enddate=project.enddate)
        body_content = utils.load_template(inputfile=template,
                                           mapping=mapping,
                                           log=logger)
        msg = mail.get_mime_text(subject, body_content, fromaddr)
        mail.send_mail(project.admin, msg, fromaddr)
        print "mail sendt to {}".format(project.admin)
        if not options.dry_run:
            utils.append_to_file(logfile, project.admin)
        # Add metadata to project for the time of notification
        kc.update_project(project_id=project.id, notified=str(date.today()))

def action_list():
    projects = kc.get_projects()
    count = 0 # project counter
    i_count = 0 # instance counter
    printer.output_dict({'header': 'Project list (enddate, name, type, instances, status)'})
    for project in projects:
        project = expired_project(project)
        if not project:
            continue
        if hasattr(project, 'disabled'):
            project_mail = 'disabled'
        elif hasattr(project, 'notified'):
            project_mail = 'notified'
        else:
            project_mail = 'NA'
        output_project = {
            0: project.enddate,
            1: project.type,
            2: project.name,
            #3: project.enddate,
            5: project_mail
        }
        resources = dict({'compute': 0, 'volume': 0})
        for region in regions:
            nc = utils.get_client(Nova, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            resources['compute'] = resources.get('compute', 0) + len(instances)
            # Todo find volume usage
            #cc = utils.get_client(Cinder, options, logger, region)
        output_project[4] = resources['compute']
        i_count += int(resources['compute'])
        count += 1
        printer.output_dict(output_project, sort=True, one_line=True)
    printer.output_dict({'header': 'Counts', 'projects': count, 'instances': i_count})

def expired_project(project):
    """ Will return a possible updated project if expired """
    if not hasattr(project, 'enddate'):
        kc.debug_log('{} has no enddate'.format(project.name))
        return None
    if not hasattr(project, 'type'):
        project.type = 'unknown'
    # hack to fix manually edited project end dates with wrong format
    if re.search(r'\d{2}\.\d{2}\.\d{4}', project.enddate):
        new_enddate = utils.convert_date(project.enddate, '%d.%m.%Y')
        kc.update_project(project_id=project.id,
                          enddate=new_enddate)
        project.enddate = new_enddate
    if project.enddate == 'None' or not utils.past_date(project.enddate):
        kc.debug_log('project {} has not reached {}'
                     .format(project.name, project.enddate))
        return None
    return project


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
