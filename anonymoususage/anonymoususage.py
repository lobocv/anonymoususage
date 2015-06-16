__author__ = 'calvin'

import ftplib
import os
import sqlite3
import datetime
import time
import logging
import re
import threading

from .table import Table, check_table_exists
from .state import State
from .statistic import Statistic

class AnonymousUsageTracker(object):
    def __init__(self, uuid, tracker_file, submit_interval=None, check_interval=60 * 60,
                 logger=None, log_level=logging.INFO):
        """
        Create a usage tracker database with statistics from a unique user defined by the uuid.
        :param uuid: unique identifier
        :param tracker_file: path to store the database
        :param submit_interval: datetime.timedelta object for the interval in which usage statistics should be sent back
        """
        if submit_interval is not None and not isinstance(submit_interval, datetime.timedelta):
            raise ValueError('submit_interval must be a datetime.timedelta object.')
        self.uuid = uuid
        self.filename = os.path.splitext(tracker_file)[0]
        self.tracker_file = self.filename + '.db'
        self.submit_interval = submit_interval
        self.check_interval = check_interval
        self._ftp = {}
        self._tables = {}
        self._watcher = None
        self._watcher_enabled = False

        if logger is None:
            self.logger = logging.getLogger('AnonymousUsage')
            self.logger.setLevel(log_level)
        else:
            self.logger = logger

        # Create the data base connections to the master database and partial database (if submit_interval)
        self.tracker_file_master = self.filename + '.db'
        self.dbcon_master = sqlite3.connect(self.tracker_file_master, check_same_thread=False)
        self.dbcon_master.row_factory = sqlite3.Row
        if submit_interval:
            # Create a partial database that contains only the table entries since the last submit
            self.tracker_file_part = self.filename + '.part.db'
            self.dbcon_part = sqlite3.connect(self.tracker_file_part, check_same_thread=False)
            self.dbcon_part.row_factory = sqlite3.Row
            # Use the partial database to append stats
            self.dbcon = self.dbcon_part
        else:
            # Use the master database to append stats
            self.dbcon = self.dbcon_master

        self.track_statistic('__submissions__')
        if self._requires_submission():
            try:
                last_submission = self['__submissions__'].get_last(1)[0]['Time']
                self.logger.info('A submission is overdue. Last submission was %s' % last_submission)
            except IndexError:
                self.logger.info('A submission is overdue')
            self.start_watcher()

    def __getitem__(self, item):
        """
        Returns the Table object with name `item`
        """
        return self._tables[item]

    def __setitem__(self, key, value):
        """
        Insert a new row into the table of name `key` with value `value`
        """
        self._tables[key].insert(value)

    def setup_ftp(self, host, user, passwd, path='', timeout=5):
        self._ftp = dict(host=host, user=user, passwd=passwd, timeout=timeout, path=path)

    def track_statistic(self, name):
        """
        Create a Statistic object in the Tracker.
        """
        self._tables[name] = Statistic(name, self)

    def track_state(self, name, initial_state):
        """
        Create a State object in the Tracker.
        """
        self._tables[name] = State(name, self, initial_state=initial_state)

    def get_row_count(self):
        info = {}
        for db in (self.dbcon_master, self.dbcon_part):
            cursor = db.cursor()
            for table, stat in self._tables.items():
                row_count_query = "SELECT Count() FROM %s" % table
                try:
                    cursor.execute(row_count_query)
                except sqlite3.OperationalError:
                    continue
                nrows = cursor.fetchone()[0]
                if table in info:
                    info[table]['nrows'] += nrows
                else:
                    info[table] = {'nrows': nrows}
        return info

    def merge_part(self):
        """
        Merge the partial database into the master.
        """
        if self.submit_interval:
            master = self.dbcon_master
            part = self.dbcon_part
            master.row_factory = part.row_factory = None
            mcur = master.cursor()
            pcur = part.cursor()
            for table, stat in self._tables.items():
                pcur.execute("SELECT * FROM %s" % table)
                rows = pcur.fetchall()
                if rows:
                    n = rows[0][1]
                    m = n + len(rows) - 1
                    self.logger.debug("Merging entries {n} through {m} of {name}".format(name=table, n=n, m=m))
                    if not check_table_exists(master, table):
                        stat.create_table(master)

                    args = ("?," * len(stat.table_args.split(',')))[:-1]
                    query = 'INSERT INTO {name} VALUES ({args})'.format(name=table, args=args)
                    mcur.executemany(query, rows)

            master.row_factory = part.row_factory = sqlite3.Row
            master.commit()
            os.remove(self.filename + '.part.db')

    def ftp_submit(self):
        """
        Upload the database to the FTP server. Only submit new information contained in the partial database.
        Merge the partial database back into master after a successful upload.
        """
        try:
            # To ensure the usage tracker does not interfere with script functionality, catch all exceptions so any
            # errors always exit nicely.
            ftpinfo = self._ftp
            ftp = ftplib.FTP(host=ftpinfo['host'], user=ftpinfo['user'], passwd=ftpinfo['passwd'],
                             timeout=ftpinfo['timeout'])

            ftp.cwd(ftpinfo['path'])
            with open(self.tracker_file_part, 'rb') as _f:
                regex_db = re.compile(r'%s\_\d+.db' % self.uuid)
                files = regex_db.findall(','.join(ftp.nlst()))
                if files:
                    regex_number = re.compile(r'_\d+')
                    n = max(map(lambda x: int(x[1:]), regex_number.findall(','.join(files)))) + 1
                else:
                    n = 1
                new_filename = self.uuid + '_%03d.db' % n
                ftp.storbinary('STOR %s' % new_filename, _f)
                self['__submissions__'] += 1
                self.logger.info('Submission to %s successful.' % ftpinfo['host'])
                self.merge_part()
                return True
        except Exception as e:
            self.logger.error(e)
            self.stop_watcher()
            return

    def enable(self):
        self.logger.info('Enabled.')
        self.start_watcher()

    def disable(self):
        self.logger.info('Disabled.')
        self.stop_watcher()

    def start_watcher(self):
        """
        Start the watcher thread that tries to upload usage statistics.
        """
        self.logger.info('Starting watcher.')
        if self._watcher and self._watcher.is_alive:
            self._watcher_enabled = True
        else:
            self._watcher = threading.Thread(target=self._watcher_thread, name='usage_tracker')
            self._watcher.setDaemon(True)
            self._watcher_enabled = True
            self._watcher.start()

    def stop_watcher(self):
        """
        Stop the watcher thread that tries to upload usage statistics.
        """
        if self._watcher:
            self._watcher_enabled = False
            self.logger.info('Stopping watcher.')

    def _requires_submission(self):
        """
        Returns True if the time since the last submission is greater than the submission interval.
        If no submissions have ever been made, check if the database last modified time is greater than the
        submission interval.
        """
        t0 = datetime.datetime.now()
        s = self['__submissions__']
        last_submission = s.get_last(1)
        if last_submission:
            t_ref = datetime.datetime.strptime(last_submission[0]['Time'], Table.time_fmt)
        else:
            t_ref = datetime.datetime.fromtimestamp(os.path.getmtime(self.tracker_file_master))

        return (t0 - t_ref).total_seconds() > self.submit_interval.total_seconds()

    def _watcher_thread(self):
        great_success = False
        while not great_success:
            time.sleep(self.check_interval)
            if not self._watcher_enabled:
                break
            self.logger.info('Attempting to upload usage statistics.')
            if self._ftp:
                great_success = self.ftp_submit()
        self.logger.info('Watcher stopped.')
        self._watcher = None


if __name__ == '__main__':

    interval = datetime.timedelta(seconds=2)
    # interval = None
    tracker = AnonymousUsageTracker(uuid='123',
                                    tracker_file='/home/calvin/test/testtracker.db',
                                    check_interval=600,
                                    submit_interval=interval)
    tracker.setup_ftp(host='ftp.sensoft.ca',
                      user='LMX',
                      passwd='G8mu5YLC6CCKkwme',
                      path='./usage')
    stat1 = 'Screenshots'
    stat2 = 'Grids'
    stat3 = 'Lines'
    state1 = 'Units'

    tracker.track_statistic(stat1)
    tracker.track_statistic(stat2)
    tracker.track_statistic(stat3)

    tracker.track_state(state1, initial_state='US Standard')
    tracker[stat1] += 1
    tracker[stat1] += 1
    # tracker[stat2] += 1
    # tracker[stat3] += 1
    # tracker[state1] = 'Metric'
    tracker[stat1] -= 1
    tracker[stat1] -= 1
    tracker[stat1] += 1
    tracker[stat1] += 1


    # tracker[state1] = 'US Standard'
    # tracker.merge_part()
    # tracker.dbcon.close()


    while 1:
        pass
        # tracker.ftp_submit()
