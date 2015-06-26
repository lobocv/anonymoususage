__author__ = 'calvin'

import datetime
import sqlite3

from .table import Table


class Statistic(Table):
    """
    Tracks the usage of a certain statistic over time.

    Usage:
        tracker.track_statistic(stat_name)
        tracker[stat_name] += 1
    """

    def __add__(self, i):
        dt = datetime.datetime.now().strftime(self.time_fmt)
        count = self.count + i
        try:
            self.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name,
                                                                        args=(self.tracker.uuid, count, dt)))
            self.dbcon.commit()
        except sqlite3.Error as e:
            self.logger.error(e)
        else:
            self.count = count
        return self

    def __sub__(self, i):
        count = self.count + 1 - i
        try:
            self.dbcon.execute("DELETE FROM {name} WHERE Count = {count}".format(name=self.name, count=count))
            self.count -= i
            self.dbcon.commit()
        except sqlite3.Error as e:
            self.logger.error(e)
        return self
