import sys
import ConfigParser
import sqlite3
import utils

class State(object):

    conn = None
    table = 'Active'

    def __init__(self, config_path, debug, log=False):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.debug = debug
        try:
            self.state = self.config._sections['state']
        except KeyError as e:
            self.logger.exception('missing [state]')
            self.logger.critical('Could not find section [state] in %s', config_path)
            sys.exit(1)

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.state['db'])
            cur = self.conn.cursor()
            cur.execute('SELECT SQLITE_VERSION()')
            data = cur.fetchone()
            self.logger.debug("=> sqlite3 version %s" % data)
            self.logger.debug("=> connected to %s" % self.state['db'])
        except sqlite3.Error as e:
            self.logger.critical("ERROR %s" % e.args[0])
            sys.exit(1)

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

    def purge(self):
        if not self.conn:
            self.connect()

        sql = "DROP TABLE IF EXISTS %s" % self.table
        cur = self.conn.cursor()
        cur.execute(sql)
        self.logger.debug("=> %s" % sql)
        self._create_active_table()

    def close(self):
        if self.conn:
            self.conn.close()

    def _create_active_table(self):
        with self.conn:
            sql = "CREATE TABLE %s(id TEXT PRIMARY KEY, \
                                   name TEXT, \
                                   state TEXT, \
                                   host TEXT)" % self.table
            cur = self.conn.cursor()
            cur.execute(sql)
            self.logger.debug("=> %s" % sql)
