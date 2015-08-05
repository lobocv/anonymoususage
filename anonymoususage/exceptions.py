__author__ = 'calvin'


class AnonymousUsageError(Exception):
    """
    Base class for errors in this module
    """
    pass


class IntervalError(AnonymousUsageError):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'Interval must be a datetime.timedelta object. Received %s.' % self.value


class TableNameError(AnonymousUsageError):

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Table name "{}" cannot contain spaces. Consider "{}" instead.'.format(self.name,
                                                                                      self.name.replace(' ', '_'))