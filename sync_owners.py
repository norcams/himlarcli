#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from dateutil import parser as dateparser
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli import utils as himutils

parser = Parser()
parser.toggle_show('format')
options = parser.parse_args()

kc= Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
logger = kc.get_logger()

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

logger.debug('=> regions used: %s', ','.join(regions))

Base = declarative_base()

class Owner(Base):
    __tablename__ = 'owners'
    ip = Column(String(16), primary_key=True)
    organization = Column(String(16), nullable=False)
    project_name = Column(String(255), nullable=False)
    admin = Column(String(255))
    user = Column(String(255))
    last_sync = Column(DateTime, default=datetime.now, nullable=False)
    created = Column(DateTime, nullable=False)
    instance_id = Column(String(63))
    status = Column(String(16), nullable=False)

    def update(self, attributes):
        dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
        change_last_sync = False
        for k,v in attributes.items():
            if getattr(self, k) != v:
                change_last_sync = True
            setattr(self, k, v)
        if change_last_sync:
            logger.debug('=> %supdate owner for ip %s', dry_run_txt, self.ip)
            self.last_sync = datetime.now()
        else:
            logger.debug('=> %sno need to update owner for ip %s', dry_run_txt, self.ip)

def action_sync():
    dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
    engine = create_engine(kc.get_config('report', 'database_uri'))
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        net = Neutron(options.config, debug=options.debug, log=logger, region=region)
        network_list = list()
        for network in net.list_networks():
            network_list.append(network['name'])
        instances = nc.get_all_instances()
        for i in instances:
            owner = dict()
            # If the instance do not have addresses we continue
            if not i.addresses:
                continue
            # Get IP address
            for network in network_list:
                if str(network) not in i.addresses:
                    continue
                for addr in i.addresses[str(network)]:
                    if addr['version'] == 4:
                        owner['ip'] = addr['addr']
            # Get project, admin and org
            project = kc.get_by_id('project', i.tenant_id)
            if project:
                owner['project_name'] = project.name
                owner['admin'] = project.admin if hasattr(project, 'admin') else None
                domain = project.admin.split("@")[1] if hasattr(project, 'admin') else ''
                if len(domain.split(".")) > 1:
                    org = domain.split(".")[-2]
                else:
                    org = 'unknown'
                owner['organization'] = org
            else:
                owner['project_name'] = 'unknown'
                owner['organization'] = 'unknown'
            # Get user and instance_id
            user = kc.get_by_id('user', i.user_id)
            owner['user'] = user.name.lower() if user else None
            owner['instance_id'] = i.id
            owner['status'] = i.status.lower()
            owner['created'] = dateparser.parse(i.created).replace(tzinfo=None)
            # Update owner
            old = session.query(Owner).filter(Owner.ip == owner['ip']).first()
            if old is not None:
                old.update(owner)
            else:
                logger.debug('=> %screate owner for ip %s', dry_run_txt, owner['ip'])
                session.add(Owner(**owner))
            if not options.dry_run:
                session.commit()
        instances = nc.get_all_instances({'all_tenants': 1, 'deleted': 1})
        # Update status for deleted instances
        for i in instances:
            owner = dict()
            owner['status'] = i.status.lower()
            old = session.query(Owner).filter(Owner.instance_id == i.id).first()
            if old is not None:
                terminated = dateparser.parse(getattr(i, 'OS-SRV-USG:terminated_at'))
                if old.last_sync < terminated:
                    logger.debug('=> %sinstance terminated since last sync %s', dry_run_txt, i.id)
                    old.update(owner)
            if not options.dry_run:
                session.commit()
    session.close()

def action_purge():
    print('do not work at the moment')
    pass
    dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
    engine = create_engine(kc.get_config('report', 'database_uri'))
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        # delete instance from owner table when instance do not exists in openstack
        # and status is not deleted (this must be an old delete instance)
        for i in session.query(Owner).filter(Owner.status != 'deleted').all():
            instance = nc.get_by_id('server', i.instance_id)
            if not instance:
                logger.debug('=> %spurge owner for instance %s', dry_run_txt, i.ip)
                session.delete(i)
                if not options.dry_run:
                    session.commit()
        # todo: delete all from table instances where there is not an corresponding IP in owner
    session.close()

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
