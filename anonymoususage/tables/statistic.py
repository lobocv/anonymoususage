__author__ = 'calvin'

import datetime
import sqlite3
import logging

from .table import Table
from ..tools import insert_row

logger = logging.getLogger('AnonymousUsage')


class Statistic(Table):
    """
    Tracks the usage of a certain statistic over time.

    Usage:
        tracker.track_statistic(stat_name)
        tracker[stat_name] += 1
    """
    IPC_COMMANDS = {'GET': ('count',),
                    'SET': ('count',),
                    'ACT': ('increment', 'decrement')}

    def __add__(self, i):
        dt = datetime.datetime.now().strftime(self.time_fmt)
        count = self.count + i
        try:
            with Table.lock:
                if self.get_number_of_rows() >= self.max_rows:
                    self.delete_first()
                insert_row(self.tracker.dbcon, self.name, self.tracker.uuid, count, dt)
        except sqlite3.Error as e:
            logger.error(e)
        else:
            self.count = count
            logging.debug('{s.name} count set to {s.count}'.format(s=self))

        return self

    def __sub__(self, i):
        self += -i
        return self

    def increment(self, by):
        self += by
        return self.count

    def decrement(self, by):
        self -= by
        return self.count

    def __repr__(self):
        return "Statistic ({s.name}): {s.count}".format(s=self)

    def get_average(self, default=None):
        """
        Return the statistic's count divided by the number of rows in the table. If it cannot be calculated return
        `default`.
        :return: The average count value (count / table rows) or `default` if it cannot be calculated.
        """
        try:
            average = self.count / self.get_number_of_rows()
        except Exception as e:
            logging.error(e)
            return default
        else:
            return average