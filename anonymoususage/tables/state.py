__author__ = 'calvin'

import datetime
import sqlite3
import logging

from .table import Table

logger = logging.getLogger('AnonymousUsage')


class NO_STATE(object):
    """
    Class used to specify that there is no initial value to the State.
    """
    pass


class State(Table):
    """
    Tracks the state of a certain attribute over time.

    Usage:
        tracker.track_state(state_name)
        tracker[state_name] = 'ON'
        tracker[state_name] = 'OFF'

    :param name: Name of the table
    :param tracker: usage tracker object
    :param initial_state: Initial value
    :param bool keep_redundant: Allow for adding of duplicate values to the database.
    """

    table_args = ("UUID", "INT"), ("Count", "INT"), ("State", "TEXT"), ("Time", "TEXT")

    def __init__(self, name, tracker, initial_state=NO_STATE, keep_redundant=False):
        super(State, self).__init__(name, tracker)
        self.keep_redundant = keep_redundant

        if self.count == 0:
            # This is a new table
            self.state = initial_state
            if initial_state is not NO_STATE:
                # If the initial state was not NO_STATE, then add it to the database
                self.insert(self.state)
        else:
            self.state = self.get_last(1)[0]['State']

    def insert(self, value):
        """
        Insert a value into the table. If keep_redundant is False and the value specified is equal to the currently set
        value, do not add a row to the database

        :param value: value of the State
        :returns: self
        """
        if not self.keep_redundant and value == self.state:
            # Don't add redundant information, ie if the state value is the same as the previous do not insert a new row
            return

        dt = datetime.datetime.now().strftime(self.time_fmt)

        try:
            self.tracker.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name,
                                                                                args=(self.tracker.uuid,
                                                                                      self.count + 1,
                                                                                      str(value),
                                                                                      dt)))
            self.tracker.dbcon.commit()
        except sqlite3.Error as e:
            logger.error(e)
        else:
            self.state = value
            self.count += 1
            logger.debug("{name} state set to {value}".format(name=self.name, value=value))
        return self

    def __repr__(self):
        state = self.state if self.state is not NO_STATE else 'No State'
        return "State ({s.name}): {state}".format(s=self, state=state)
