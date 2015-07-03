__author__ = 'calvin'

import logging

from .tools import *

logger = logging.getLogger('AnonymousUsage')


class Table(object):
    time_fmt = "%d/%m/%Y %H:%M:%S"
    table_args = ("UUID", "INT"), ("Count", "INT"), ("Time", "TEXT")

    def __init__(self, name, tracker, *args, **kwargs):
        self.tracker = tracker
        self.name = name

        self.count = self.get_number_of_rows()
        if not check_table_exists(self.tracker.dbcon, name):
            create_table(self.tracker.dbcon, name, self.table_args)

    def get_number_of_rows(self):
        """
        Attempt to load the statistic from the database.
        :return: Number of entries for the statistic
        """
        rows = []
        if check_table_exists(self.tracker.dbcon_master, self.name):
            rows.extend(get_rows(self.tracker.dbcon_master, self.name))
        if check_table_exists(self.tracker.dbcon_part, self.name):
            rows.extend(get_rows(self.tracker.dbcon_part, self.name))

        logger.debug("{name}: {n} table entries found".format(name=self.name,
                                                                  n=len(rows),
                                                                  rows='\n\t'.join(map(str, rows))))
        return len(rows)

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
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())
        # Then add rows from the master if required
        if len(rows) < n and check_table_exists(self.tracker.dbcon_master, self.name):
            cur = self.tracker.dbcon_master.cursor()
            # cur.execute("SELECT * FROM %s" % self.name)
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())

        return rows[-n:]
