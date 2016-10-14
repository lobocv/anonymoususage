__author__ = 'calvin'

import logging

from anonymoususage.tools import *
from anonymoususage.exceptions import *
from threading import RLock

logger = logging.getLogger('AnonymousUsage')


class Table(object):
    time_fmt = "%d/%m/%Y %H:%M:%S"
    table_args = ("UUID", "INT"), ("Count", "INT"), ("Time", "TEXT")
    IPC_COMMANDS = {'GET': ('count',),
                    'SET': (),
                    'ACT': ()}
    lock = RLock()

    def __init__(self, name, tracker, max_rows):
        if ' ' in name:
            raise TableNameError(name)
        self.max_rows = max_rows
        self.tracker = tracker
        self.name = name

        self.number_of_rows = self.get_number_of_rows()
        last = self.get_last()
        if last:
            self.count = last[0]['Count']
        else:
            self.count = 0

        logger.debug("{s.name}: {s.number_of_rows} table entries found".format(s=self))

        if not check_table_exists(self.tracker.dbcon, name):
            create_table(self.tracker.dbcon, name, self.table_args)

    def get_rows(self):
        """
        Attempt to load the statistic from the database.
        :return: Number of entries for the statistic
        """
        rows = []
        if check_table_exists(self.tracker.dbcon_master, self.name):
            rows.extend(get_rows(self.tracker.dbcon_master, self.name))
        if self.tracker.dbcon_part and check_table_exists(self.tracker.dbcon_part, self.name):
            rows.extend(get_rows(self.tracker.dbcon_part, self.name))
        return rows

    def get_number_of_rows(self):
        n_rows = get_number_of_rows(self.tracker.dbcon_master, self.name)
        if self.tracker.dbcon_part:
            n_rows += get_number_of_rows(self.tracker.dbcon_part, self.name)
        return n_rows

    def insert(self, value):
        """
        Contains the functionally of assigning a value to a statistic in the AnonymousUsageTracker. Usually this will
        involve inserting some data into the database table for the statistic.
        :param value: assignment value to the tracker, ie. `tracker[stat_name] = some_value`
        """
        pass

    def get_first(self, n=1):
        """
        Retrieve the first n rows from the table
        :param n: number of rows to return
        :return: list of rows
        """
        rows = []
        # Get values from the partial db first
        if self.tracker.dbcon_master and check_table_exists(self.tracker.dbcon_master, self.name):
            rows.extend(get_first_row(self.tracker.dbcon_master, self.name, n))
        # Then add rows from the master if required
        if len(rows) < n and self.tracker.dbcon_part and check_table_exists(self.tracker.dbcon_part, self.name):
            rows.extend(get_first_row(self.tracker.dbcon_part, self.name, n))
        return rows[:n]

    def get_last(self, n=1):
        """
        Retrieve the last n rows from the table
        :param n: number of rows to return
        :return: list of rows
        """
        rows = []
        # Get values from the partial db first
        if self.tracker.dbcon_part and check_table_exists(self.tracker.dbcon_part, self.name):
            rows.extend(get_last_row(self.tracker.dbcon_part, self.name, n))
        # Then add rows from the master if required
        if len(rows) < n and check_table_exists(self.tracker.dbcon_master, self.name):
            rows.extend(get_last_row(self.tracker.dbcon_master, self.name, n))
        return rows[-n:]

    def delete_last(self):
        last = self.get_last()
        if last:
            last = last[0]
            db = self.tracker.dbcon_part if self.tracker.dbcon_part else self.tracker.dbcon_master
            delete_row(db, self.name, "Time", last['Time'])
            self.count -= 1

    def delete_first(self):
        for db in (self.tracker.dbcon_master, self.tracker.dbcon_part):
            if db:
                rowid = get_first_row(db, self.name)
                if rowid:
                    delete_row(db, self.name, "Time", rowid[0]['Time'])
                    break

    def get_count(self):
        row = self.get_last()
        if row:
            return row[0]['Count']
        else:
            return 0

    @classmethod
    def api_help(cls):
        return "{cls}\n" \
               "---------\n" \
               "GET : {get}\n" \
               "SET : {set}\n" \
               "ACT : {act}\n".format(cls=cls.__name__,
                                       get=','.join(cls.IPC_COMMANDS['GET']),
                                       set=','.join(cls.IPC_COMMANDS['SET']),
                                       act=','.join(cls.IPC_COMMANDS['ACT']))