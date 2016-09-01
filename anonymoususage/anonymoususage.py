__author__ = 'calvin'

import ConfigParser
import datetime
import logging
import os
import re
import json
import sqlite3
import threading
import time
import socket
import collections

from tables import Table, Statistic, State, Timer, Sequence
from .api import upload_stats
from .exceptions import IntervalError, TableConflictError
from .tools import *

CHECK_INTERVAL = datetime.timedelta(minutes=30)
logger = logging.getLogger('AnonymousUsage')


class AnonymousUsageTracker(object):

    def __init__(self, uuid, filepath, submit_interval_s=0, check_interval_s=0,
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
        self._watcher = None
        self._watcher_enabled = False

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
            self.hq_submit()

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
        self._tables[key].insert(value)

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

                response = upload_stats(self._hq['server'], payload)
                if response == 'Success':
                    logger.debug('Submission to %s successful.' % self._hq['server'])

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
                kw['filepath'] = general['filepath']
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
            time.sleep(self.check_interval_s)
            if not self._watcher_enabled:
                break
            if self._hq and self._requires_submission():
                logger.debug('Attempting to upload usage statistics.')
                self.hq_submit()
        logger.debug('Watcher stopped.')
        self._watcher = None


    #############################################################
    #               Interprocess Communication                  #
    #############################################################

    def open_socket(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        return s

    def monitor_socket(self, socket):
        s = socket
        s.setblocking(1)
        s.listen(1)
        conn, addr = s.accept()
        while 1:
            error_msg = ''
            response = ''
            action = ''
            packet = conn.recv(1024)
            if packet == '':
                break
            struct = json.loads(packet)

            cmd = struct.get('command')
            if cmd == 'GET':
                table = self[struct.get('trackable')]
                attr = struct.get('field').lower()
                if table and attr:
                    if attr in table.IPC_COMMANDS['GET']:
                        value = getattr(table, attr)
                    else:
                        error_msg = 'GET command is not available for %s' % attr

                    # Convert the response to string representation
                    if isinstance(value, basestring):
                        response = value
                    elif isinstance(value, collections.Iterable):
                        response = ','.join(map(str, value))
                    else:
                        response = str(value)
            elif cmd == 'SET':
                table = self[struct.get('trackable')]
                attr = struct.get('field').lower()
                value = struct.get('value')
                if table and attr:
                    if attr in table.IPC_COMMANDS['SET']:
                        try:
                            setattr(table, attr, value)
                            response = '{} set to {}'.format(attr, value)
                        except Exception as e:
                            error_msg = e.message

                    else:
                        error_msg = 'SET command is not available for %s' % attr
            elif cmd == 'ACT':
                table = self[struct.get('trackable')]
                action = struct.get('action')
                args = struct.get('args', [])
                if table and action:
                    if action in table.IPC_COMMANDS['ACT']:
                        try:
                            getattr(table, action)(*args)
                            response = 'Call to %s has been processed' % action
                        except Exception as e:
                            error_msg = e.message

                # If there was an error, send back the error message, otherwise the response
            conn.send(error_msg or response)

            print packet


if __name__ == '__main__':

    interval = datetime.timedelta(seconds=2)
    # interval = None
    tracker = AnonymousUsageTracker(uuid='123',
                                    filepath='/home/calvin/test/testtracker.db',
                                    check_interval_s=600,
                                    submit_interval_s=interval)
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
