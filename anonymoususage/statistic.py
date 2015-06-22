__author__ = 'calvin'

import datetime

from .table import Table


class Statistic(Table):
    """
    Tracks the usage of a certain statistic over time.

    Usage:
        tracker.track_statistic(stat_name)
        tracker[stat_name] += 1
    """

    def __add__(self, other):
        dt = datetime.datetime.now().strftime(self.time_fmt)
        self.count += other
        self.tracker.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name, args=(self.tracker.uuid,
                                                                                   self.count,
                                                                                   dt)))
        self.tracker.dbcon.commit()
        return self

    def __sub__(self, other):
        count = self.count + 1 - other
        self.tracker.dbcon.execute("DELETE FROM {name} WHERE Count = {count}".format(name=self.name, count=count))
        self.count -= other
        self.tracker.dbcon.commit()
        return self
