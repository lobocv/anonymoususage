__author__ = 'calvin'

import datetime
import logging

logger = logging.getLogger('AnonymousUsage')


from .statistic import Statistic


class Timer(Statistic):
    """
    A timer is a special case of a Statistic where the count is the number of elapsed seconds. A Timer object can be
    started and stopped in order to record the time it takes for certain tasks to be completed.

    """
    def __init__(self, name, tracker):
        super(Timer, self).__init__(name, tracker)
        self._start_time = None
        self._delta_seconds = 0

    def start_timer(self):
        self._start_time = datetime.datetime.now()
        self._delta_seconds = 0
        logger.debug('AnonymousUsage: Starting %s timer' % self.name)

    def pause_timer(self):
        timedelta = datetime.datetime.now() - self._start_time
        self._delta_seconds += timedelta.total_seconds()
        logger.debug('AnonymousUsage: Pausing %s timer' % self.name)

    def stop_timer(self):
        if self._start_time is None:
            logger.debug('AnonymousUsage: Cannot stop timer that has not been started.')
            return
        timedelta = datetime.datetime.now() - self._start_time
        self._delta_seconds += timedelta.total_seconds()
        self += self._delta_seconds
        self._delta_seconds = 0
        self._start_time = None
        logger.debug('AnonymousUsage: Stopping %s timer' % self.name)

    def __sub__(self, other):
        raise NotImplementedError('Cannot subtract from timer.')

    def __repr__(self):
        last_two = self.get_last(2)
        if len(last_two) == 1:
            last_time = last_two[0]['Count']
        elif len(last_two) == 0:
            return "Timer ({s.name}): Total 0 s".format(s=self)
        else:
            last_time = abs(last_two[1]['Count'] - last_two[0]['Count'])
        average = self.get_average('None')
        return "Timer ({s.name}): Total {s.count} s, last {} s, average {} s".format(last_time,
                                                                                     average,
                                                                                     s=self)
