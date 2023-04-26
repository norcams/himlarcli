#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

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
parser.toggle_show('dry-run')
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
    timestamp = Column(DateTime, default=datetime.now)
    instance_id = Column(String(63))

    def update(self, attributes):
        for k,v in attributes.items():
            setattr(self, k, v)

def action_sync():
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
            # Get IP address
            if not i.addresses:
                continue
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
            # Update owner
            old = session.query(Owner).filter(Owner.ip == owner['ip']).first()
            if old is not None:
                logger.debug('=> update owner for ip %s', owner['ip'])
                old.update(owner)
            else:
                logger.debug('=> create owner for ip %s', owner['ip'])
                session.add(Owner(**owner))
            session.commit()
    session.close()

def action_purge():
    engine = create_engine(kc.get_config('report', 'database_uri'))
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = nc.get_all_instances({'all_tenants': 1, 'deleted': 1})
        for i in instances:
            old = session.query(Owner).filter(Owner.instance_id == i.id).first()
            if old is not None:
                logger.debug('=> purge owner for instance %s', old.ip)
                session.delete(old)
                session.commit()
    session.close()

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
