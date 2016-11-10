__author__ = 'calvin'

import datetime
import sqlite3
import logging

from .table import Table
from ..tools import insert_row


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

    def __init__(self, name, tracker, initial_state=NO_STATE, keep_redundant=False, *args, **kwargs):
        super(State, self).__init__(name, tracker, *args, **kwargs)
        self.keep_redundant = keep_redundant

        if self.count == 0:
            # This is a new table
            self._state = initial_state
            if initial_state is not NO_STATE:
                # If the initial state was not NO_STATE, then add it to the database
                self.insert(self._state)
        else:
            self._state = self.get_last(1)[0]['State']

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self.insert(value)

    def set(self, value):
        self.state = value
        return self.state

    def insert(self, value):
        if not self.keep_redundant and value == self._state:
            # Don't add redundant information, ie if the state value is the same as the previous do not insert a new row
            return

        dt = datetime.datetime.now().strftime(self.time_fmt)

        try:
            with Table.lock:
                if self.get_number_of_rows() >= self.max_rows:
                    self.delete_first()
                insert_row(self.tracker.dbcon, self.name, self.tracker.uuid, self.count + 1, str(value), dt)

        except sqlite3.Error as e:
            logger.error(e)
        else:
            self._state = value
            self.count += 1
            logger.debug("{name} state set to {value}".format(name=self.name, value=value))
        return self

    def __repr__(self):
        state = self._state if self._state is not NO_STATE else 'No State'
        return "State ({s.name}): {state}".format(s=self, state=state)
