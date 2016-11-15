__author__ = 'calvin'

import ConfigParser
import datetime
import logging
import os
import csv
import re
import json
import sqlite3
import threading
import time
import socket
import requests

from tables import Table, Statistic, State, Timer, Sequence, NO_STATE
from .exceptions import TableConflictError
from .tools import *

CHECK_INTERVAL = datetime.timedelta(minutes=30)
logger = logging.getLogger('AnonymousUsage')


class AnonymousUsageTracker(object):
    HQ_DEFAULT_TIMEOUT = 10
    MAX_ROWS_PER_TABLE = 1000

    def __init__(self, uuid, filepath, submit_interval_s=0, check_interval_s=0, enabled=True,
                 application_name='', application_version='', debug=False):
        """
        Create a usage tracker database with statistics from a unique user defined by the uuid.
        :param uuid: unique identifier
        :param filepath: path to store the database
        :param application_name: Name of the application as a string
        :param application_version: Application version as a string
        :param check_interval_s: How often the tracker should check to see if an upload is required (seconds)
        :param submit_interval_s: How often the usage statistics should be uploaded (seconds)
        """

        if debug:
            logger.setLevel(logging.DEBUG)

        self.uuid = str(uuid)
        self.filename = os.path.splitext(filepath)[0]
        self.filepath = self.filename + '.db'
        self.submit_interval_s = submit_interval_s
        self.check_interval_s = check_interval_s
        self.application_name = application_name
        self.application_version = application_version

        self.regex_db = re.compile(r'%s_\d+.db' % self.uuid)
        self._tables = {}
        self._hq = {}
        self._enabled = enabled
        self._watcher = None
        self._watcher_enabled = False
        self._open_sockets = {}
        self._discovery_socket_port = None

        # Create the data base connections to the master database and partial database (if submit_interval)
        self.dbcon_master = sqlite3.connect(self.filepath, check_same_thread=False)
        self.dbcon_master.row_factory = sqlite3.Row

        # If a submit interval is given, create a partial database that contains only the table entries since
        # the last submission. Merge this partial database into the master after a submission.
        # If no submit interval is given, just use a single (master) database.
        if submit_interval_s:
            self.filepath_part = self.filename + '.part.db'
            self.dbcon_part = sqlite3.connect(self.filepath_part, check_same_thread=False)
            self.dbcon_part.row_factory = sqlite3.Row
            self.dbcon = self.dbcon_part
        else:
            self.dbcon_part = None
            self.filepath_part = None
            self.dbcon = self.dbcon_master

        self.track_statistic('__submissions__', description='The number of statistic submissions to the server.')
        if self._hq and self._requires_submission():
            self.submit_statistics()

        if check_interval_s and submit_interval_s:
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
        table = self._tables.get(key)
        if table:
            if isinstance(table, Statistic) and isinstance(value, (float, int)):
                # Due to Statistic.__add__ returning itself, we must check that the value is a number,
                # otherwise we could be adding a object to a number
                diff = value - table.count
                table += diff
            elif isinstance(table, (State, Sequence)):
                table.insert(value)

    @property
    def states(self):
        return [t for t in self._tables.itervalues() if type(t) is State]

    @property
    def statistics(self):
        return [t for t in self._tables.itervalues() if type(t) is Statistic]

    @property
    def timers(self):
        return [t for t in self._tables.itervalues() if type(t) is Timer]

    @property
    def sequences(self):
        return [t for t in self._tables.itervalues() if type(t) is Sequence]

    def close(self):
        self.dbcon_part.commit()
        self.dbcon_part.close()
        self.dbcon_master.commit()
        self.dbcon_master.close()

    def setup_hq(self, host, api_key):
        self._hq = dict(host=host, api_key=api_key)

    def register_table(self, tablename, uuid, type, description):
        exists_in_master = check_table_exists(self.dbcon_master, '__tableinfo__')
        exists_in_partial = self.dbcon_part and check_table_exists(self.dbcon_part, '__tableinfo__')
        if not exists_in_master and not exists_in_partial:
            # The table doesn't exist in master, create it in partial so it can be merged in on submit
            # (if partial exists) otherwise, create it in the master
            if self.dbcon_part:
                db = self.dbcon_part
            else:
                db = self.dbcon_master
                exists_in_master = True
            create_table(db, '__tableinfo__', [("TableName", "TEXT"), ("Type", "TEXT"), ("Description", "TEXT")])

        # Check if info is already in the table
        dbconn = self.dbcon_master if exists_in_master else self.dbcon_part
        tableinfo = dbconn.execute("SELECT * FROM __tableinfo__ WHERE TableName='{}'".format(tablename)).fetchall()
        # If the info for this table is not in the database, add it
        if len(tableinfo) == 0:
            dbconn.execute("INSERT INTO {name} VALUES{args}".format(name='__tableinfo__',
                                                                    args=(str(tablename), type, description)))

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

    def track_statistic(self, name, description='', max_rows=None):
        """
        Create a Statistic object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        if max_rows is None:
            max_rows = AnonymousUsageTracker.MAX_ROWS_PER_TABLE
        self.register_table(name, self.uuid, 'Statistic', description)
        self._tables[name] = Statistic(name, self, max_rows=max_rows)

    def track_state(self, name, initial_state, description='', max_rows=None, **state_kw):
        """
        Create a State object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        if max_rows is None:
            max_rows = AnonymousUsageTracker.MAX_ROWS_PER_TABLE
        self.register_table(name, self.uuid, 'State', description)
        self._tables[name] = State(name, self, initial_state, max_rows=max_rows, **state_kw)

    def track_time(self, name, description='', max_rows=None):
        """
        Create a Timer object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        if max_rows is None:
            max_rows = AnonymousUsageTracker.MAX_ROWS_PER_TABLE
        self.register_table(name, self.uuid, 'Timer', description)
        self._tables[name] = Timer(name, self, max_rows=max_rows)

    def track_sequence(self, name, checkpoints, description='', max_rows=None):
        """
        Create a Sequence object in the Tracker.
        """
        if name in self._tables:
            raise TableConflictError(name)
        if max_rows is None:
            max_rows = AnonymousUsageTracker.MAX_ROWS_PER_TABLE
        self.register_table(name, self.uuid, 'Sequence', description)
        self._tables[name] = Sequence(name, self, checkpoints, max_rows=max_rows)

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

    def submit_statistics(self):
        """
        Upload the database to the FTP server. Only submit new information contained in the partial database.
        Merge the partial database back into master after a successful upload.
        """
        if not self._hq.get('api_key', False) or not self._enabled:
            return
        for r in ('uuid', 'application_name', 'application_version'):
            if not getattr(self, r, False):
                return False
        self['__submissions__'] += 1
        if self.dbcon_part:
            db = self.dbcon_part
            db_file = self.filepath_part
        else:
            db = self.dbcon_master
            db_file = self.filepath
        try:
            # To ensure the usage tracker does not interfere with script functionality, catch all exceptions so any
            # errors always exit nicely.
            with open(db_file, 'rb') as _f:

                tableinfo = self.get_table_info()
                payload = {'API Key': self._hq['api_key'],
                           'User Identifier': self.uuid,
                           'Application Name': self.application_name,
                           'Application Version': self.application_version,
                           'Data': database_to_json(db, tableinfo)
                           }

                # For tables with data that has not yet been writen to the database (ie inital values),
                # add them manually to the payload
                for name, info in tableinfo.iteritems():
                    if name not in payload['Data']:
                        table = self[name]
                        if isinstance(table, State):
                            data = 'No State' if table._state == NO_STATE else table._state
                        else:
                            data = table.count
                        tableinfo[name]['data'] = data
                        payload['Data'][name] = tableinfo[name]

                try:
                    response = requests.post(self._hq['host'] + '/usagestats/upload',
                                             data=json.dumps(payload),
                                             timeout=self.HQ_DEFAULT_TIMEOUT)
                except Exception as e:
                    logging.error(e)
                    response = False

                if response and response.status_code == 200:
                    logger.debug('Submission to %s successful.' % self._hq['host'])

                # If we have a partial database, merge it into the local master and create a new partial
                if self.dbcon_part:
                    merge_databases(self.dbcon_master, self.dbcon_part)

                    # Remove the partial file and create a new one
                    os.remove(self.filepath_part)
                    self.dbcon = self.dbcon_part = sqlite3.connect(self.filepath_part, check_same_thread=False)
                    self.dbcon_part.row_factory = sqlite3.Row
                    for table in self._tables.itervalues():
                        create_table(self.dbcon_part, table.name, table.table_args)

                return True
        except Exception as e:
            logger.error(e)
            self['__submissions__'].delete_last()
            self.stop_watcher()
            return False

    def to_file(self, path, precision='%.2g'):
        """
        Create a CSV report of the trackables
        :param path: path to file
        :param precision: numeric string formatter
        """
        table_info = self.get_table_info()

        def dump_rows(rows):
            if len(rows) > 1:
                for row in rows:
                    csv_writer.writerow(row)
                csv_writer.writerow([])

        with open(path, 'wb') as _f:
            csv_writer = csv.writer(_f)

            state_rows = [['States']]
            state_rows += [['Name', 'Description', 'State', 'Number of Changes']]
            for state in self.states:
                state_rows.append([state.name, table_info[state.name]['description'], state.state, state.count])
            dump_rows(state_rows)

            stat_rows = [['Statistics']]
            stat_rows += [['Name', 'Description', 'Total', 'Average']]
            for stat in self.statistics:
                if stat.name == '__submissions__':
                    continue
                stat_rows.append([stat.name, table_info[stat.name]['description'], stat.count, stat.get_average(0)])
                dump_rows(stat_rows)

            timer_rows = [['Timers']]
            timer_rows += [['Name', 'Description', 'Average Seconds', 'Total Seconds', 'Total Minutes', 'Total Hours', 'Total Days']]
            for timer in self.timers:
                timer_rows.append([timer.name, table_info[timer.name]['description'],
                                   precision % timer.get_average(0), precision % timer.total_seconds, precision % timer.total_minutes,
                                   precision % timer.total_hours, precision % timer.total_days])
                dump_rows(timer_rows)

            sequence_rows = [['Sequences']]
            sequence_rows += [['Name', 'Description', 'Sequence', 'Number of Completions']]
            for sequence in self.sequences:
                checkpoints = '-->'.join(map(str, sequence.get_checkpoints()))
                sequence_rows.append([sequence.name, table_info[sequence.name]['description'], checkpoints, sequence.count])
                dump_rows(sequence_rows)

    @classmethod
    def load_from_configuration(cls, path, uuid, **kwargs):
        """
        Load FTP server credentials from a configuration file.
        """
        cfg = ConfigParser.ConfigParser()
        kw = {}
        with open(path, 'r') as _f:
            cfg.readfp(_f)
            if cfg.has_section('General'):
                general = dict(cfg.items('General'))
                kw['filepath'] = kwargs.get('filepath', False) or general['filepath']
                kw['application_name'] = general.get('application_name', '')
                kw['application_version'] = general.get('application_version', '')
                kw['submit_interval_s'] = int(general.get('submit_interval_s', 0))
                kw['check_interval_s'] = int(general.get('check_interval_s', 0))
                kw['debug'] = bool(general.get('debug', False))

            if cfg.has_section('HQ'):
                hq_params = dict(cfg.items('HQ'))
            else:
                hq_params = None

        kw.update(**kwargs)
        tracker = cls(uuid, **kw)
        if hq_params:
            tracker.setup_hq(**hq_params)

        return tracker

    def enable(self):
        """
        Gives the tracker permission to upload statistics
        """
        logger.debug('Enabled.')
        self._enabled = True
        self.start_watcher()
        return 'Uploading of statistics has been enabled'

    def disable(self):
        """
        Revokes the tracker's permission to upload statistics
        """
        logger.debug('Disabled.')
        self._enabled = False
        self.stop_watcher()
        return 'Uploading of statistics has been disabled'

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
        if self.dbcon_part is None:
            return False

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
            t_ref = datetime.datetime.fromtimestamp(os.path.getmtime(self.filepath))

        submission_interval_passed = (t0 - t_ref).total_seconds() > self.submit_interval_s
        submission_required = bool(submission_interval_passed and nrows)
        if submission_required:
            logger.debug('A submission is overdue.')
        else:
            logger.debug('No submission required.')
        return submission_required

    def _watcher_thread(self):
        while 1:
            time.sleep(self.check_interval_s or 300)
            if not self._watcher_enabled:
                break
            if self._hq and self._requires_submission():
                logger.debug('Attempting to upload usage statistics.')
                self.submit_statistics()
        logger.debug('Watcher stopped.')
        self._watcher = None
