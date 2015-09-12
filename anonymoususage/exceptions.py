__author__ = 'calvin'


class AnonymousUsageError(Exception):
    """
    Base class for errors in this module
    """
    pass


class IntervalError(AnonymousUsageError):
    """
    Invalid date time interval specified.
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'Interval must be a datetime.timedelta object. Received %s.' % self.value


class TableNameError(AnonymousUsageError):
    """
    Invalid table name specified.
    """
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Table name "{}" cannot contain spaces. Consider "{}" instead.'.format(self.name,
                                                                                      self.name.replace(' ', '_'))


class TableConflictError(AnonymousUsageError):
    """
    Conflicting table name in the database. Table likely already exists.
    """
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'Table name "{}" already exists in this usage tracker.'.format(self.name)


class InvalidCheckpointError(AnonymousUsageError):
    """
    Invalid checkpoint. Checkpoint does not exist in the list of valid checkpoints.
    """
    def __init__(self, checkpoint):
        self.checkpoint = checkpoint

    def __str__(self):
        return 'Checkpoint "{}" assignment is not in the valid list of checkpoints'.format(self.checkpoint)