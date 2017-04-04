import ConfigParser
import sqlite3
import sys
from himlarcli import utils


class State(object):

    ACTIVE_TABLE = 'active'
    IMAGE_TABLE = 'images'
    TABLES = dict()
    TABLES[IMAGE_TABLE] = ('CREATE TABLE IF NOT EXISTS %s ('
                           'id TEXT PRIMARY KEY, '
                           'name TEXT, '
                           'status TEXT, '
                           'region TEXT)') % IMAGE_TABLE
    TABLES[ACTIVE_TABLE] = ('CREATE TABLE IF NOT EXISTS %s ('
                            'id TEXT PRIMARY KEY, '
                            'name TEXT, '
                            'state TEXT, '
                            'host TEXT)') % ACTIVE_TABLE
    conn = None

    def __init__(self, config_path, debug, log=False):
        self.config_path = config_path
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s', config_path)
        self.debug = debug
        self.db = self.__get_config('state', 'db')
        self.connect()
        # Make sure all tables exists
        self.__create_tables()

    """
    Connect to db
    """
    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db)
            cur = self.conn.cursor()
            cur.execute('SELECT SQLITE_VERSION()')
            data = cur.fetchone()
            self.logger.debug("=> sqlite3 version %s", data)
            self.logger.debug("=> connected to %s", self.db)
        except sqlite3.Error as e:
            self.logger.critical("ERROR %s", e.args[0])
            sys.exit(1)

    def close(self):
        self.conn.close()

    def purge(self, table_name):
        self.__purge_table(name=table_name)
        self.__create_table(name=table_name)

    def insert(self, table, **kwargs):
        cur = self.conn.cursor()
        if 'id' in kwargs:
            sql = "SELECT count(*) FROM %s WHERE id = '%s';" % (table, kwargs['id'])
            cur.execute(sql)
            if cur.fetchone()[0] > 0:
                self.logger.debug("=> id %s exits in table %s", kwargs['id'], table)
                return
        sql = ('INSERT')
        columns = []
        values = []
        for key, value in kwargs.iteritems():
            columns.append(key)
            if isinstance(value, basestring):
                values.append("'%s'" % value)
            else:
                values.append(value)
        sql = ('INSERT INTO %s (%s) VALUES (%s)') % (
            table, ', '.join(str(x) for x in columns),
            ', '.join(str(x) for x in values))

        self.logger.debug("=> SQL=%s", sql)
        cur.execute(sql)
        self.conn.commit()

    def fetch(self, table, columns='*', **kwargs):
        sql = ('SELECT %s FROM %s') % (columns, table)
        clause = []
        for key, value in kwargs.iteritems():
            if isinstance(value, basestring):
                clause.append("%s='%s'" % (key, value))
            else:
                clause.append("%s=%s" % (key, value))
        if clause:
            sql += (' WHERE ')
            sql += ' and '.join(str(x) for x in clause)
        cur = self.conn.cursor()
        self.logger.debug("=> SQL=%s", sql)
        cur.execute(sql)
        return cur.fetchall()

    def add_active(self, instances):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        instance_list = list()
        for i in instances:
            host = i._info['OS-EXT-SRV-ATTR:host']
            state = i._info['status']
            sql = "SELECT count(*) FROM %s WHERE id = '%s'" % (self.table, i.id)
            #self.logger.debug("add_active(): %s" % sql)
            cur.execute(sql)
            if cur.fetchone()[0] == 0:
                instance_list.append((i.id, i.name, state, host))
                self.logger.debug("=> add instance %s" % i.id)
            else:
                self.logger.debug("=> instance %s exits in db" % i.id)
        if instance_list:
            sql = "INSERT INTO %s VALUES(?, ?, ?, ?)" % self.table
            cur.executemany(sql, instance_list)
            self.conn.commit()
            #self.logger.debug("add_active(): %s" % sql)

    def get_instances(self, state=None, host=None):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        if state and host:
            sql = "SELECT * FROM %s WHERE state = '%s' AND host = '%s'" \
                % (self.table, state, host)
        elif state:
            sql = "SELECT * FROM %s WHERE state = '%s'" % (self.table, state)
        elif host:
            sql = "SELECT * FROM %s WHERE host = '%s'" % (self.table, host)
        else:
            sql = "SELECT * FROM %s" % self.table
        self.logger.debug("=> %s" % sql)
        cur.execute(sql)
        rows = cur.fetchall()
        self.logger.debug("=> row size %s" % len(rows))
        return rows

    def dump(self):
        if not self.conn:
            self.connect()
        sql = "SELECT * FROM %s" % self.table
        cur = self.conn.cursor()
        self.logger.debug("%s" % sql)
        cur.execute(sql)
        rows = cur.fetchall()
        self.logger.debug("=> row size %s" % len(rows))
        for row in rows:
            self.logger.debug("%s" % str(row))
        return rows

#    def purge(self):
#        if not self.conn:
#            self.connect()
#        sql = "DROP TABLE IF EXISTS %s" % self.table
#        cur = self.conn.cursor()
#        cur.execute(sql)
#        self.logger.debug("=> %s" % sql)
#        self._create_active_table()

    def _create_active_table(self):
        with self.conn:
            sql = "CREATE TABLE %s(id TEXT PRIMARY KEY, \
                                   name TEXT, \
                                   state TEXT, \
                                   host TEXT)" % self.table
            cur = self.conn.cursor()
            cur.execute(sql)
            self.logger.debug("=> %s" % sql)

    """
    Purge all tables
    """
    def __purge_tables(self):
        for name in self.TABLES.iterkeys():
            self.__purge_table(name=name)

    """
    Purge table if it exists
    """
    def __purge_table(self, name):
        cur = self.conn.cursor()
        sql = "DROP TABLE IF EXISTS %s" % name
        cur.execute(sql)
        self.logger.debug('=> purge table for %s', name)

    """
    Create all new tables if they do not exists
    """
    def __create_tables(self):
        for name in self.TABLES.iterkeys():
            self.__create_table(name=name)

    """
    Create new table if it does not exists
    """
    def __create_table(self, name):
        table = self.TABLES[name]
        cur = self.conn.cursor()
        cur.execute(table)
        self.logger.debug('=> create new table for %s', name)

    """
    Fetch config from config file
    """
    def __get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s',
                              section, option)
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s', section)
        return None
