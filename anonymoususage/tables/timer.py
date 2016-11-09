__author__ = 'calvin'

import datetime
import logging
import time

logger = logging.getLogger('AnonymousUsage')


from .statistic import Statistic


class Timer(Statistic):
    """
    A timer is a special case of a Statistic where the count is the number of elapsed seconds. A Timer object can be
    started and stopped in order to record the time it takes for certain tasks to be completed.

    """
    IPC_COMMANDS = {'GET': ('count', 'total_days', 'total_hours', 'total_minutes', 'total_seconds'),
                    'SET': (),
                    'ACT': ('start_timer', 'pause_timer', 'resume_timer', 'stop_timer')}

    def __init__(self, name, tracker, *args, **kwargs):
        super(Timer, self).__init__(name, tracker, *args, **kwargs)
        self._start_time = None
        self.paused = False
        self._delta_seconds = 0

    def start_timer(self):
        self._start_time = datetime.datetime.now()
        self._delta_seconds = 0
        logger.debug('AnonymousUsage: Starting %s timer' % self.name)

    def pause_timer(self):
        timedelta = datetime.datetime.now() - self._start_time
        self._delta_seconds += timedelta.total_seconds()
        self.paused = True
        logger.debug('AnonymousUsage: Pausing %s timer' % self.name)

    def resume_timer(self):
        self.paused = False
        self._start_time = datetime.datetime.now()
        logger.debug('AnonymousUsage: Resuming %s timer' % self.name)

    def stop_timer(self):
        if self._start_time is None:
            logger.debug('AnonymousUsage: Cannot stop timer that has not been started.')
            return
        if not self.paused:
            timedelta = datetime.datetime.now() - self._start_time
            self._delta_seconds += timedelta.total_seconds()
        self += self._delta_seconds
        delta_seconds = self._delta_seconds
        self._delta_seconds = 0
        self._start_time = None
        self.paused = False
        logger.debug('AnonymousUsage: Stopping %s timer' % self.name)
        return delta_seconds

    @property
    def elapsed_time_s(self):
        """
        Return the amount of time that has elapsed since the timer was started.
        Only works if the timer is active.
        """
        if self._start_time:
            return (datetime.datetime.now() - self._start_time).total_seconds()
        else:
            return 0

    @property
    def total_minutes(self):
        return self.count / 60.

    @property
    def total_hours(self):
        return self.count / 3600.

    @property
    def total_seconds(self):
        return self.count

    @property
    def total_days(self):
        return self.count / 86400.

    def strftime(self, format, average=False):
        seconds = self.get_average(0) if average else self.count
        return time.strftime(format, time.gmtime(seconds))

    def formatted_total_time(self, **kwargs):
        return self.format_time(self.count, **kwargs)

    def formatted_average_time(self, **kwargs):
        return self.format_time(self.get_average(default=0), **kwargs)

    @staticmethod
    def format_time(n_seconds, seconds=True, minutes=True, hours=True, days=True, years=True):
        y = d = h = m = 0
        if years:
            y, n_seconds = divmod(n_seconds, 31536000)
        if days:
            d, n_seconds = divmod(n_seconds, 86400)
        if hours:
            h, n_seconds = divmod(n_seconds, 3600)
        if minutes:
            m, n_seconds = divmod(n_seconds, 60)

        fmt = ' '.join([bool(y) * years * ('%d years' % y),
                        bool(d) * days * ('%d days' % d),
                        bool(h) * hours * ('%d hours' % h),
                        bool(m) * minutes * ('%d minutes' % m),
                        bool(n_seconds) * seconds * ('%d seconds' % n_seconds)]).strip()
        return fmt

    def __sub__(self, other):
        raise NotImplementedError('Cannot subtract from timer.')

    def __repr__(self):
        if hasattr(self, 'count'):
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
        else:
            return "Timer ({s.name})".format(s=self)
