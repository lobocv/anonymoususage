__author__ = 'calvin'

import datetime
import sqlite3
import logging

from .table import Table

logger = logging.getLogger('AnonymousUsage')


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
            self.tracker.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name,
                                                                        args=(self.tracker.uuid, count, dt)))
            self.tracker.dbcon.commit()
        except sqlite3.Error as e:
            logger.error(e)
        else:
            self.count = count
            logging.debug('{s.name} count set to {s.count}'.format(s=self))

        return self

    def __sub__(self, i):
        count = self.count + 1 - i
        try:
            self.tracker.dbcon.execute("DELETE FROM {name} WHERE Count = {count}".format(name=self.name, count=count))
            self.tracker.dbcon.commit()
        except sqlite3.Error as e:
            logger.error(e)
        else:
            self.count = count
            logging.debug('{s.name} count set to {s.count}'.format(s=self))
        return self

    def __repr__(self):
        return "Statistic ({s.name}): {s.count}".format(s=self)
