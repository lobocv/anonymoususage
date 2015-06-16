__author__ = 'calvin'

import sqlite3


def get_table_list(dbconn):
    cur = dbconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [item[0] for item in cur.fetchall()]


def check_table_exists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = '{}'".format(tablename))
    result = dbcur.fetchone()
    dbcur.close()
    return result[0] == 1


class Table(object):
    time_fmt = "%d/%m/%Y %H:%M:%S"
    table_args = "UUID INT, Count INT, Time TEXT"

    def __init__(self, name, tracker, *args, **kwargs):
        self.tracker = tracker
        self.dbcon = self.tracker.dbcon
        self.name = name
        self.logger = tracker.logger

        self.count = self.get_table_count()
        if not check_table_exists(self.dbcon, name):
            self.create_table(self.dbcon)

    def get_table_count(self):
        """
        Attempt to load the statistic from the database.
        :return: Number of entries for the statistic
        """
        rows = []
        if check_table_exists(self.tracker.dbcon_master, self.name):
            cursor = self.tracker.dbcon_master.cursor()
            cursor.execute("SELECT * FROM %s" % self.name)
            rows.extend(cursor.fetchall())
        if check_table_exists(self.tracker.dbcon_part, self.name):
            cursor = self.tracker.dbcon_part.cursor()
            cursor.execute("SELECT * FROM %s" % self.name)
            rows.extend(cursor.fetchall())

        self.logger.debug("{name}: {n} table entries found".format(name=self.name,
                                                                  n=len(rows),
                                                                  rows='\n\t'.join(map(str, rows))))
        return len(rows)

    def create_table(self, dbcon):
        """
        Create a table in the database.
        :param dbcon: database
        :return: True if a new table was created
        """
        try:
            dbcon.execute("CREATE TABLE {name}({args})".format(name=self.name, args=self.table_args))
            return True
        except sqlite3.OperationalError as e:
            self.logger.error(e)
            return False

    def insert(self, value):
        """
        Contains the functionally of assigning a value to a statistic in the AnonymousUsageTracker. Usually this will
        involve inserting some data into the database table for the statistic.
        :param value: assignment value to the tracker, ie. `tracker[stat_name] = some_value`
        """
        pass

    def get_last(self, n):
        """
        Retrieve the last n rows from the table
        :param n: number of rows to return
        :return: list of rows
        """
        rows = []
        # Get values from the partial db first
        if check_table_exists(self.tracker.dbcon_part, self.name):
            cur = self.tracker.dbcon_part.cursor()
            # cur.execute("SELECT * FROM %s" % self.name)
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())
        # Then add rows from the master if required
        if len(rows) < n and check_table_exists(self.tracker.dbcon_master, self.name):
            cur = self.tracker.dbcon_master.cursor()
            # cur.execute("SELECT * FROM %s" % self.name)
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())

        return rows
