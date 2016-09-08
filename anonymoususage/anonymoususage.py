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
import requests

from tables import Table, Statistic, State, Timer, Sequence, NO_STATE
import api
from .exceptions import TableConflictError
from .tools import *

CHECK_INTERVAL = datetime.timedelta(minutes=30)
logger = logging.getLogger('AnonymousUsage')


class AnonymousUsageTracker(object):
    HQ_DEFAULT_TIMEOUT = 10

    IPC_COMMANDS = {'GET': (),
                    'SET': (),
                    'ACT': ('track_statistic', 'track_state', 'track_time', 'track_sequence', 'submit_statistics',
                            'get_table_info', 'new_connection', 'close_connection')}

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

    def submit_statistics(self):
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

                # For tables with data that has not yet been writen to the database (ie inital values),
                # add them manually to the payload
                for name, info in tableinfo.iteritems():
                    if name not in payload['Data']:
                        table = self[name]
                        if isinstance(table, State):
                            data = 'No State' if table.state == NO_STATE else table.state
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
                self.submit_statistics()
        logger.debug('Watcher stopped.')
        self._watcher = None

    #############################################################
    #               Inter-process Communication                 #
    #############################################################

    def open_socket(self, host, port):
        """
        Open a socket on the specified host and port
        :return: socket instance
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        self._open_sockets[port] = dict(local_host=host, socket=sock, local_port=port)
        if len(self._open_sockets) == 1:
            self._discovery_socket_port = port
        return sock

    def new_connection(self, port):
        """
        Create a new connection on a different port that is monitored for IPC commands.
        This command closes the current socket connection and reopens it so that a new connection can be made.
        :param port: Port to open new connection under
        """
        if len(self._open_sockets):
            host = self._open_sockets.values()[0]['local_host']
            if port in [s['local_port'] for s in self._open_sockets.values()]:
                return 'Port %d is already in use' % port

            sock = self.open_socket(host, port)
            thread = threading.Thread(target=self.monitor_socket, args=(sock,))
            thread.start()
            self._open_sockets[port]['thread'] = thread
            del self._open_sockets[self._discovery_socket_port]['connection']

            return 'New connection has been opened on port %d' % port

    def close_connection(self, *ports):
        """
        Close a connection on the specified ports
        :param ports: list of ports to be closed. Closes all open ports if none are specified.
        """
        if len(ports) == 0:
            ports = self._open_sockets.keys()
        for port in ports:
            if port in self._open_sockets:
                sock = self._open_sockets[port]['socket']
                sock.shutdown(socket.SHUT_WR)
                sock.close()
                del self._open_sockets[port]

    def _close_discovery_socket(self):
        """
        Bind to our discovery socket and send a command to close communication and shutdown the socket
        """
        info = self._open_sockets[self._discovery_socket_port]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((info['local_host'], info['local_port']))
        cmd = json.dumps({'command': 'ACT', 'trackable': '', 'action': 'close_connection', 'args': (info['local_port'],)})
        sock.send(cmd)
        response = sock.recv(1024)

    def monitor_socket(self, sock):
        """
        Start listening for and monitor inter-process communication on a socket
        :param sock: Socket
        """
        sock.setblocking(1)
        sock.listen(1)
        local_host, local_port = sock.getsockname()

        while local_port in self._open_sockets:

            if self._open_sockets[local_port].get('connection') is None:
                sock = self._open_sockets[local_port]['socket']
                local_host, local_port = sock.getsockname()
                logging.info('Looking for connections on port %d' % local_port)
                conn, (remote_host, remote_port) = sock.accept()
                logging.info('Communication opened at %s:%d' % (remote_host, remote_port))
                self._open_sockets[local_port].update(dict(connection=conn, remote_host=remote_host,
                                                           remote_port=remote_port))

            response = action = error_msg = ''
            packet = conn.recv(1024)
            if packet == '':
                break
            struct = json.loads(packet)

            if struct.get('trackable') == '':
                obj = self
            else:
                obj = self[struct.get('trackable')]

            cmd = struct.get('command')
            if cmd == 'GET':
                attr = struct.get('attribute').lower()
                if obj and attr:
                    try:
                        response = api.get_(obj, attr)
                    except Exception as e:
                        error_msg = e.message
            elif cmd == 'SET':
                attr = struct.get('attribute').lower()
                value = struct.get('value')
                if obj and attr:
                    try:
                        response = api.set_(obj, attr, value)
                    except Exception as e:
                        error_msg = e.message
            elif cmd == 'ACT':
                action = struct.get('action')
                args = struct.get('args', [])
                if obj and action:
                    try:
                        response = api.act_(obj, action, *args)
                        if not isinstance(response, basestring):
                            response = json.dumps(response)
                    except Exception as e:
                        error_msg = e.message

            # If there was an error, send back the error message, otherwise the response
            conn.send(error_msg or response)
            logging.info('Request on Port {port}: {packet}'.format(packet=packet, port=remote_port))
            logging.info('Response on Port {port}: {response}'.format(response=(error_msg or response), port=remote_port))

        logging.info('Stopping monitoring of port {port}'.format(port=local_port))
        self.close_connection(local_port)
        if len(self._open_sockets) == 1:
            self._close_discovery_socket()
