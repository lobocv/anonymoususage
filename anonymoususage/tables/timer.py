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
    def __init__(self, name, tracker):
        super(Timer, self).__init__(name, tracker)
        self._start_time = None
        self._delta_seconds = 0

    def start_timer(self):
        """
        Start the timer.
        """
        self._start_time = datetime.datetime.now()
        self._delta_seconds = 0
        logger.debug('AnonymousUsage: Starting %s timer' % self.name)

    def pause_timer(self):
        """
        Pause the timer.
        """
        timedelta = datetime.datetime.now() - self._start_time
        self._delta_seconds += timedelta.total_seconds()
        logger.debug('AnonymousUsage: Pausing %s timer' % self.name)

    def stop_timer(self):
        """
        Stop the timer and commit value to the database
        """
        if self._start_time is None:
            logger.debug('AnonymousUsage: Cannot stop timer that has not been started.')
            return
        timedelta = datetime.datetime.now() - self._start_time
        self._delta_seconds += timedelta.total_seconds()
        self += self._delta_seconds
        self._delta_seconds = 0
        self._start_time = None
        logger.debug('AnonymousUsage: Stopping %s timer' % self.name)

    @property
    def total_minutes(self):
        """
        Return the total time in minutes. Excludes timers in progress.
        """
        return self.count / 60.

    @property
    def total_hours(self):
        """
        Return the total time in hours. Excludes timers in progress.
        """
        return self.count / 3600.

    @property
    def total_seconds(self):
        """
        Return the total time in seconds. Excludes timers in progress.
        """
        return self.count

    @property
    def total_days(self):
        """
        Return the total time in days. Excludes timers in progress.
        """
        return self.count / 86400.

    def strftime(self, format, average=False):
        """
        Return a formatted string of the time.
        :param format:  time.strftime format string
        :param bool average: Use the average time instead of total
        """
        seconds = self.get_average(0) if average else self.count
        return time.strftime(format, time.gmtime(seconds))

    def formatted_total_time(self, **kwargs):
        """
        Convenience method for format_time using the total time
        """
        return self.format_time(self.count, **kwargs)

    def formatted_average_time(self, **kwargs):
        """
        Convenience method for format_time using the average time
        """
        return self.format_time(self.get_average(default=0), **kwargs)

    @staticmethod
    def format_time(n_seconds, seconds=True, minutes=True, hours=True, days=True, years=True):
        """
        Return a formatted string of the total time in years, days, hours, minutes and seconds.
        :param bool n_seconds: Number of seconds
        :param bool seconds: Show seconds
        :param bool minutes: Show minutes
        :param bool hours: Show hours
        :param bool days: Show days
        :param bool years: Show years
        :return:
        """
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
