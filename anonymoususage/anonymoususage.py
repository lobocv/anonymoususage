__author__ = 'calvin'

import ConfigParser
import datetime
import logging
import os
import re
import sqlite3
import threading
import time

from tables import Table, Statistic, State, Timer, Sequence
from .api import upload_stats
from .exceptions import IntervalError, TableConflictError
from .tools import *

CHECK_INTERVAL = datetime.timedelta(minutes=30)
logger = logging.getLogger('AnonymousUsage')


class AnonymousUsageTracker(object):
    application_name = None
    application_version = None

    def __init__(self, uuid, tracker_file, submit_interval=None, check_interval=CHECK_INTERVAL,
                 config='', debug=False):
        """
        Create a usage tracker database with statistics from a unique user defined by the uuid.
        :param uuid: unique identifier
        :param tracker_file: path to store the database
        :param config: path to store the configuration file.
        :param check_interval: datetime.timedelta object specifying how often the tracker should check to see if an
                               upload is required
        :param submit_interval: datetime.timedelta object for the interval in which usage statistics should be uploaded
        """

        if debug:
            logger.setLevel(logging.DEBUG)

        if not isinstance(submit_interval, datetime.timedelta):
            raise IntervalError(submit_interval)
        if not isinstance(check_interval, datetime.timedelta):
            raise IntervalError(check_interval)

        self.uuid = str(uuid)
        self.filename = os.path.splitext(tracker_file)[0]
        self.tracker_file = self.filename + '.db'
        self.submit_interval = submit_interval
        self.check_interval = check_interval

        self.regex_db = re.compile(r'%s_\d+.db' % self.uuid)
        self._tables = {}
        self._watcher = None
        self._watcher_enabled = False

        # Load the configuration from a file if specified
        if os.path.isfile(config):
            self.load_configuration(config)
        else:
            self._hq = {}

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
        if self._requires_submission() and self._hq:
            self.hq_submit()

        self.start_watcher()

    def __getitem__(self, item):
        """
        Returns the Table object with name `item`
        """
        return self._tables.get(item, None)

    def __setitem__(self, key, value):
        """
        Insert a new row into the table of name `key` with value `value`
        """
        self._tables[key].insert(value)

    def close(self):
        self.dbcon_part.commit()
        self.dbcon_part.close()
        self.dbcon_master.commit()
        self.dbcon_master.close()

    def setup_hq(self, host, user, passwd, path='', acct='', port=21, timeout=5):
        self._hq = dict(host=host, user=user, passwd=passwd, acct=acct,
                         timeout=int(timeout), path=path, port=int(port))

    def register_table(self, tablename, uuid, type, description):
        exists_in_master = check_table_exists(self.dbcon_master, '__tableinfo__')
        exists_in_partial = check_table_exists(self.dbcon_part, '__tableinfo__')
        if not exists_in_master and not exists_in_partial:
            # The table doesn't exist in master, create it in partial so it can be merged in on submit
            create_table(self.dbcon_part, '__tableinfo__', [("TableName", "TEXT"), ("Type", "TEXT"), ("Description", "TEXT")])
        # Check if info is already in the table
        dbconn = self.dbcon_master if exists_in_master else self.dbcon_part
        tableinfo = dbconn.execute("SELECT * FROM __tableinfo__ WHERE TableName='{}'".format(tablename)).fetchall()
        # If the info for this table is not in the database, add it
        if len(tableinfo) == 0:
            dbconn.execute("INSERT INTO {name} VALUES{args}".format(name='__tableinfo__',
                                                                    args=(tablename, type, description)))

    def get_table_info(self, field=None):
        rows = []
        if check_table_exists(self.dbcon_master, '__tableinfo__'):
            rows = get_rows(self.dbcon_master, '__tableinfo__')
        elif check_table_exists(self.dbcon_part, '__tableinfo__'):
            rows = get_rows(self.dbcon_part, '__tableinfo__')

        if field:
            idx = ('type', 'description').index(field.lower()) + 1
            tableinfo = {r[0]: r[idx] for r in rows}
        else:
            tableinfo = {r[0]: {'type': r[1], 'description': r[2]} for r in rows}
        return tableinfo

    def track_statistic(self, name, description=''):
        """
        Create a Statistic object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        self.register_table(name, self.uuid, 'Statistic', description)
        self._tables[name] = Statistic(name, self)

    def track_state(self, name, initial_state, description='', **state_kw):
        """
        Create a State object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        self.register_table(name, self.uuid, 'State', description)
        self._tables[name] = State(name, self, initial_state, **state_kw)

    def track_time(self, name, description=''):
        """
        Create a Timer object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        self.register_table(name, self.uuid, 'Timer', description)
        self._tables[name] = Timer(name, self)

    def track_sequence(self, name, checkpoints, description=''):
        """
        Create a Sequence object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        self.register_table(name, self.uuid, 'Sequence', description)
        self._tables[name] = Sequence(name, self, checkpoints)

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

    def hq_submit(self):
        """
        Upload the database to the FTP server. Only submit new information contained in the partial database.
        Merge the partial database back into master after a successful upload.
        """
        if not self._hq.get('api_key', False):
            return
        for r in ('uuid', 'application_name', 'application_version'):
            if not getattr(self, r, False):
                return False
        self['__submissions__'] += 1
        try:
            # To ensure the usage tracker does not interfere with script functionality, catch all exceptions so any
            # errors always exit nicely.
            with open(self.tracker_file_part, 'rb') as _f:

                tableinfo = self.get_table_info()
                payload = {'API Key': self._hq['api_key'],
                           'User Identifier': self.uuid,
                           'Application Name': self.application_name,
                           'Application Version': self.application_version,
                           'Data': database_to_json(self.dbcon_part, tableinfo)
                           }

                response = upload_stats(self._hq['server'], payload)
                if response == 'Success':
                    logger.debug('Submission to %s successful.' % self._hq['server'])
                # Merge the local partial database into master
                merge_databases(self.dbcon_master, self.dbcon_part)

                # Remove the partial file and create a new one
                os.remove(self.tracker_file_part)
                self.dbcon = self.dbcon_part = sqlite3.connect(self.tracker_file_part, check_same_thread=False)
                self.dbcon_part.row_factory = sqlite3.Row
                for table in self._tables.itervalues():
                    create_table(self.dbcon_part, table.name, table.table_args)
                return True
        except Exception as e:
            logger.error(e)
            self['__submissions__'].delete_last()
            self.stop_watcher()
            return False

    def load_configuration(self, config):
        """
        Load FTP server credentials from a configuration file.
        """
        cfg = ConfigParser.ConfigParser()
        with open(config, 'r') as _f:
            cfg.readfp(_f)
            if cfg.has_section('General'):
                general = dict(cfg.items('General'))
                self.application_name = general.get('application_name', None)
                self.application_version = general.get('application_version', None)
            if cfg.has_section('HQ'):
                self._hq = dict(cfg.items('HQ'))

    def enable(self):
        logger.debug('Enabled.')
        self.start_watcher()

    def disable(self):
        logger.debug('Disabled.')
        self.stop_watcher()

    def start_watcher(self):
        """
        Start the watcher thread that tries to upload usage statistics.
        """
        if self._watcher and self._watcher.is_alive:
            self._watcher_enabled = True
        else:
            logger.debug('Starting watcher.')
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
            logger.debug('Stopping watcher.')

    def _requires_submission(self):
        """
        Returns True if the time since the last submission is greater than the submission interval.
        If no submissions have ever been made, check if the database last modified time is greater than the
        submission interval.
        """
        tables = get_table_list(self.dbcon_part)
        nrows = 0
        for table in tables:
            if table == '__submissions__':
                continue
            nrows += get_number_of_rows(self.dbcon_part, table)
        if nrows:
            logger.debug('%d new statistics were added since the last submission.' % nrows)
        else:
            logger.debug('No new statistics were added since the last submission.')

        t0 = datetime.datetime.now()
        s = self['__submissions__']
        last_submission = s.get_last(1)
        if last_submission:
            logger.debug('Last submission was %s' % last_submission[0]['Time'])
            t_ref = datetime.datetime.strptime(last_submission[0]['Time'], Table.time_fmt)
        else:
            t_ref = datetime.datetime.fromtimestamp(os.path.getmtime(self.tracker_file_master))

        submission_interval_passed = (t0 - t_ref).total_seconds() > self.submit_interval.total_seconds()
        submission_required = bool(submission_interval_passed and nrows)
        if submission_required:
            logger.debug('A submission is overdue.')
        else:
            logger.debug('No submission required.')
        return submission_required

    def _watcher_thread(self):
        while 1:
            time.sleep(self.check_interval.total_seconds())
            if not self._watcher_enabled:
                break
            if self._hq and self._requires_submission():
                logger.debug('Attempting to upload usage statistics.')
                self.hq_submit()
        logger.debug('Watcher stopped.')
        self._watcher = None


if __name__ == '__main__':

    interval = datetime.timedelta(seconds=2)
    # interval = None
    tracker = AnonymousUsageTracker(uuid='123',
                                    tracker_file='/home/calvin/test/testtracker.db',
                                    check_interval=600,
                                    submit_interval=interval)
    tracker.setup_hq(host='ftp.sensoft.ca',
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
