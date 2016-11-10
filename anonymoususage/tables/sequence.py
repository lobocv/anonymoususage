__author__ = 'calvin'

import datetime
import sqlite3
import logging

from itertools import imap
from operator import eq
from collections import deque
from .table import Table
from ..tools import insert_row
from anonymoususage.exceptions import InvalidCheckpointError

logger = logging.getLogger('AnonymousUsage')


class Sequence(Table):
    """
    Tracks the number of times a user performs a certain sequence of events.

    Usage:
        tracker.track_sequence(stat_name, ['first', 'second', 'third'])
        tracker[stat_name] = 'first'    # First check point reached
        tracker[stat_name] = 'second'   # Second check point reached
        tracker[stat_name] = 'third'    # Third check point reached. At this point the database is updated.

    """
    IPC_COMMANDS = {'GET': ('count', 'sequence', 'checkpoint'),
                    'SET': ('count', 'checkpoint'),
                    'ACT': ('get_checkpoints', 'remove_checkpoint', 'clear_checkpoints', 'advance_to_checkpoint')}

    def __init__(self, name, tracker, checkpoints, *args, **kwargs):
        super(Sequence, self).__init__(name, tracker, *args, **kwargs)
        self._checkpoints = checkpoints
        self._sequence = deque([], maxlen=len(checkpoints))

    def insert(self, checkpoint):
        if checkpoint in self._checkpoints:
            self._sequence.append(checkpoint)
            logging.debug('{cp} added to sequence "{s.name}"'.format(cp=checkpoint, s=self))
            if len(self._sequence) == len(self._checkpoints) and all(imap(eq, self._sequence, self._checkpoints)):
                # Sequence is complete. Increment the database
                dt = datetime.datetime.now().strftime(self.time_fmt)
                count = self.count + 1
                try:
                    with Table.lock:
                        if self.get_number_of_rows() >= self.max_rows:
                            self.delete_first()
                        insert_row(self.tracker.dbcon, self.name, self.tracker.uuid, count, dt)
                except sqlite3.Error as e:
                    logger.error(e)
                else:
                    self.count = count
                    self._sequence.clear()
                    logging.debug("Sequence {s.name} complete, count set to {s.count}".format(s=self))
        else:
            raise InvalidCheckpointError(checkpoint)

    @property
    def checkpoint(self):
        try:
            return self._sequence[-1]
        except IndexError:
            return None

    @checkpoint.setter
    def checkpoint(self, checkpoint):
        self.insert(checkpoint)

    @property
    def sequence(self):
        return tuple(self._sequence)

    @property
    def checkpoints(self):
        """
        return a list of checkpoints (copy)
        """
        return self._checkpoints[:]

    def remove_checkpoint(self):
        """
        Remove the last check point.
        """
        if len(self._sequence):
            return self._sequence.pop()

    def clear_checkpoints(self):
        """
        Clear all completed check points.
        """
        self._sequence.clear()

    def advance_to_checkpoint(self, checkpoint):
        """
        Advance to the specified checkpoint, passing all preceding checkpoints including the specified checkpoint.
        """
        if checkpoint in self._checkpoints:
            for cp in self._checkpoints:
                self.insert(cp)
                if cp == checkpoint:
                    return cp
        else:
            raise InvalidCheckpointError(checkpoint)

