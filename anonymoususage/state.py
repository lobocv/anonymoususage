__author__ = 'calvin'

import datetime

from .table import Table


class State(Table):
    """
    Tracks the state of a certain attribute over time.

    Usage:
        tracker.track_state(state_name)
        tracker[state_name] = 'ON'
        tracker[state_name] = 'OFF'
    """
    table_args = "UUID INT, Count INT, State TEXT, Time TEXT"

    def __init__(self, *args, **kwargs):
        super(State, self).__init__(*args, **kwargs)
        self.state = kwargs.get('initial_state', None)
        if self.count == 0:
            self.insert(self.state)

    def insert(self, value):
        last_value = self.get_last(1)[0]['State']
        if value == last_value:
            # Don't add redundant information
            return
        dt = datetime.datetime.now().strftime(self.time_fmt)
        self.count += 1
        self.state = value
        self.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name, args=(self.tracker.uuid,
                                                                                   self.count,
                                                                                   self.state,
                                                                                   dt)))
        self.dbcon.commit()
        self.logger.debug("{name} state set to {value}".format(name=self.name, value=value))
        return self
