#!/usr/bin/env python

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nova.db.sqlalchemy import api_models

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
    spec = session.query(api_models.RequestSpec).filter_by(instance_uuid=options.instance).first()
    print(options.instance)
    print(test)

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error(f"Function action_{options.action}() not implemented")
action()
