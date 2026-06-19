#!/usr/bin/env python

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nova.db.sqlalchemy import api_models
import json

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

config = utils.get_himlarcli_config(options.config)
logger = utils.get_logger(__name__, config, options.debug)

db_host = config.get('db-nova', 'host')
db_pw = config.get('db-nova', 'password')
engine = create_engine(f"mysql+pymysql://nova_api:{db_pw}@{db_host}/nova_api")
Session = sessionmaker(bind=engine)
session = Session()

def action_show():
    request_spec = session.query(api_models.RequestSpec) \
                .filter_by(instance_uuid=options.instance).first()
    if request_spec:
        logger.debug('=> found request spec for instance %s', options.instance)
        spec = json.loads(request_spec.spec)
        if 'instance_group' in spec['nova_object.data'] and spec['nova_object.data']['instance_group']:
            printer.output_dict(spec['nova_object.data']['instance_group'])
            printer.output_msg('NB! if this server group is delete we will '
                               'need to remove the scheduler hints')
        else:
            printer.output_msg('no instance_group found for instance')

def action_remove_hints():
    request_spec = session.query(api_models.RequestSpec) \
                .filter_by(instance_uuid=options.instance).first()
    if request_spec:
        logger.debug('=> found request spec for instance %s', options.instance)
        spec = json.loads(request_spec.spec)
        if 'instance_group' in spec['nova_object.data'] and spec['nova_object.data']['instance_group']:
            spec['nova_object.data']['instance_group'] = None
            logger.debug('=> try to remove instance_group from request spec')
            q = ("Are you sure you will remove the scheduler hints for this "
                "instance in the database? Please run backup first. Continue?")
            if not utils.confirm_action(q):
                return
            request_spec.spec = json.dumps(spec)
            if not options.dry_run:
                session.commit()
                printer.output_msg('instance_group removed from instance')
            else:
                printer.output_msg(('DRY-RUN: instance_group should '
                                    'be removed from instance'))
        else:
            printer.output_msg('no instance_group found for instance')

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error(f"Function action_{options.action}() not implemented")
action()
