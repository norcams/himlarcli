import sys
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from himlarcli.client import Client

# Use Resource from State as base 
from himlarcli.state import Resource

Base = declarative_base(cls=Resource)

class GlobalState(Client):

    """ Global State client to manage state data 

        Tips:
        * Resource is a db table, and a new resource is a new row in the table.
        * Kwargs is usually column names in the table
    """

    def __init__(self, config_path, debug, log=False):
        super().__init__(config_path, debug, log)
        self.connect()

    def get_client(self):
        """ We return the db session since we do not have a client """
        return self.session

    def connect(self):
        """ Connect to the global state database """
        db_uri = self.get_config('global_state', 'database_uri')
        self.engine = create_engine(db_uri, poolclass=NullPool)
        Base.metadata.bind = self.engine
        DBSession = sessionmaker()
        self.session = DBSession()
        Base.metadata.create_all(self.engine)
        self.logger.debug("=> driver %s", self.engine.driver)
        self.logger.debug("=> connected to %s", db_uri)

    def close(self):
        self.logger.debug('=> close db session')
        self.session.close()

    def add(self, resource):
        """ Add a new resource to database """
        pf = self.log_prefix()
        self.logger.debug('%s add new resource of type %s', pf, resource.to_str())
        if not self.dry_run:
            self.session.add(resource)
        self.session.commit()

    def update(self, resource, data):
        """ Update a resource with new data """
        pf = self.log_prefix()
        if not self.dry_run:
            resource.update(data)
        self.logger.debug('%s update resource %s', pf, resource.to_str())

    def get_all(self, class_name, **kwargs):
        """ Get all resources based on input args """ 
        return self.session.query(class_name).filter_by(**kwargs).all()

    def get_first(self, class_name, **kwargs):
        """ Get first resource found based on input args """
        return self.session.query(class_name).filter_by(**kwargs).first()

    def purge(self, table):
        """ Drop a table for database """
        pf = self.log_prefix()
        self.logger.debug('%s drop table %s', pf, table.title())
        found_table = getattr(sys.modules[__name__], table.title())
        if not self.dry_run:
            found_table.__table__.drop()

#
# Resource data models
#

class Instance(Base):

    """  Instance data model """

    __tablename__ = 'instance'
    id = Column(Integer, primary_key=True)
    user_id = Column(String(63), nullable=False, index=True)
    created = Column(DateTime, default=datetime.now)
    name = Column(String(255))
    type = Column(String(15))
    region = Column(String(15), index=True)

    def to_str(self):
        return f'instance: {self.name}'

    def compare(self, attributes):
        pass
