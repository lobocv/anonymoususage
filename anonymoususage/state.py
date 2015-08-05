__author__ = 'calvin'

import datetime
import sqlite3
import logging

from .table import Table


logger = logging.getLogger('AnonymousUsage')

NO_STATE = type('NO_STATE', (object, ), {})


class State(Table):
    """
    Tracks the state of a certain attribute over time.

    Usage:
        tracker.track_state(state_name)
        tracker[state_name] = 'ON'
        tracker[state_name] = 'OFF'
    """
    table_args = ("UUID", "INT"), ("Count", "INT"), ("State", "TEXT"), ("Time", "TEXT")

    def __init__(self, name, tracker, initial_state=NO_STATE, keep_redundant=False):
        super(State, self).__init__(name, tracker)
        self.keep_redundant = keep_redundant
        self.state = initial_state
        if self.count:
            self.last_value = self.get_last(1)[0]['State']
        elif initial_state is NO_STATE:
            self.last_value = NO_STATE
        else:
            self.last_value = NO_STATE
            self.insert(self.state)

    def insert(self, value):
        if not self.keep_redundant and value == self.last_value:
            # Don't add redundant information, ie if the state value is the same as the previous do not insert a new row
            return

        dt = datetime.datetime.now().strftime(self.time_fmt)

        try:
            self.tracker.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name,
                                                                                args=(self.tracker.uuid,
                                                                                      self.count+1,
                                                                                      str(value),
                                                                                      dt)))
            self.tracker.dbcon.commit()
            self.last_value = value
        except sqlite3.Error as e:
            logger.error(e)
        else:
            self.state = value
            self.count += 1
            logger.debug("{name} state set to {value}".format(name=self.name, value=value))
        return self

    def __repr__(self):
        return "State ({s.name}): {s.last_value}".format(s=self)
