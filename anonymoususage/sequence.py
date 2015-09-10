__author__ = 'calvin'

import datetime
import sqlite3
import logging

from itertools import imap
from operator import eq
from collections import deque
from .table import Table
from .exceptions import InvalidCheckpointError

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

    def __init__(self, name, tracker, checkpoints):
        super(Sequence, self).__init__(name, tracker)
        self.checkpoints = checkpoints
        self.sequence = deque([], maxlen=len(checkpoints))

    def insert(self, checkpoint):
        if checkpoint in self.checkpoints:
            self.sequence.append(checkpoint)
            logging.debug('{cp} added to sequence "{s.name}"'.format(cp=checkpoint, s=self))
            if len(self.sequence) == len(self.checkpoints) and all(imap(eq, self.sequence, self.checkpoints)):
                # Sequence is complete. Increment the database
                dt = datetime.datetime.now().strftime(self.time_fmt)
                count = self.count + 1
                uuid = self.tracker.uuid
                try:
                    self.tracker.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name,
                                                                                        args=(uuid, count, dt)))
                    self.tracker.dbcon.commit()
                except sqlite3.Error as e:
                    logger.error(e)
                else:
                    self.count = count
                    logging.debug("Sequence {s.name} complete, count set to {s.count}".format(s=self))
        else:
            raise InvalidCheckpointError(checkpoint)

    def get_checkpoints(self):
        """
        return a list of checkpoints (copy)
        """
        return self.checkpoints[:]

    def remove_checkpoint(self):
        """
        Remove the last check point.
        """
        if len(self.sequence):
            self.sequence.pop()

    def clear_checkpoints(self):
        """
        Clear all completed check points.
        """
        self.sequence.clear()

    def advance_to_checkpoint(self, checkpoint):
        """
        Advance to the specified checkpoint, passing all preceding checkpoints including the specified checkpoint.
        """
        if checkpoint in self.checkpoints:
            for cp in self.checkpoints:
                self.insert(cp)
                if cp == checkpoint:
                    break
        else:
            raise InvalidCheckpointError(checkpoint)

