__author__ = 'calvin'

import ftplib
import os
import sqlite3
import datetime
import time
import logging

from threading import Thread

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_table_list(dbconn):
    cur = dbconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [item[0] for item in cur.fetchall()]


def check_table_exists(dbcon, tablename):
    dbcur = dbcon.cursor()
    dbcur.execute("SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = '{}'".format(tablename))
    result = dbcur.fetchone()
    dbcur.close()
    return result[0] == 1


class Table(object):
    time_fmt = "%d/%m/%Y %H:%M:%S"
    table_args = "UUID INT, Count INT, Time TEXT"

    def __init__(self, name, tracker, *args, **kwargs):
        self.tracker = tracker
        self.dbcon = self.tracker.dbcon
        self.name = name
        self.count = self.get_table_count()
        if self.count == 0 or tracker.submit_interval:
            self.create_table(self.dbcon)

    def get_table_count(self):
        """
        Attempt to load the statistic from the database.
        :return: Number of entries for the statistic
        """
        rows = []
        if check_table_exists(self.tracker.dbcon_master, self.name):
            cursor = self.tracker.dbcon_master.cursor()
            cursor.execute("SELECT * FROM %s" % self.name)
            rows.extend(cursor.fetchall())
        if check_table_exists(self.tracker.dbcon_part, self.name):
            cursor = self.tracker.dbcon_part.cursor()
            cursor.execute("SELECT * FROM %s" % self.name)
            rows.extend(cursor.fetchall())

        logger.info("AnonymousUsageTracker: {name}: {n} table entries found".format(name=self.name,
                                                                                    n=len(rows),
                                                                                    rows='\n\t'.join(map(str, rows))))

        return len(rows)

    def create_table(self, dbcon):
        try:
            dbcon.execute("CREATE TABLE {name}({args})".format(name=self.name, args=self.table_args))
        except sqlite3.OperationalError:
            pass

    def insert(self, value):
        """
        Contains the functionally of assigning a value to a statistic in the AnonymousUsageTracker. Usually this will
        involve inserting some data into the database table for the statistic.
        :param value: assignment value to the tracker, ie. `tracker[stat_name] = some_value`
        """
        pass

    def get_last(self, n):
        rows = []
        if check_table_exists(self.tracker.dbcon_master, self.name):
            cur = self.tracker.dbcon_master.cursor()
            # cur.execute("SELECT * FROM %s" % self.name)
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())
        if check_table_exists(self.tracker.dbcon_part, self.name):
            cur = self.tracker.dbcon_part.cursor()
            # cur.execute("SELECT * FROM %s" % self.name)
            cur.execute("SELECT * FROM %s ORDER BY Count DESC LIMIT %d;" % (self.name, n))
            rows.extend(cur.fetchall())

        return rows


class Statistic(Table):
    """
    Tracks the usage of a certain statistic over time.

    Usage:
        tracker.track_statistic(stat_name)
        tracker[stat_name] += 1
    """

    def __add__(self, other):
        dt = datetime.datetime.now().strftime(self.time_fmt)
        self.count += other
        self.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name, args=(self.tracker.uuid,
                                                                                   self.count,
                                                                                   dt)))
        self.dbcon.commit()
        return self

    def __sub__(self, other):
        count = self.count + 1 - other
        self.dbcon.execute("DELETE FROM {name} WHERE Count = {count}".format(name=self.name, count=count))
        self.count -= other
        self.dbcon.commit()
        return self

class State(Table):
    """
    Tracks the state of a certain attribute over time.

    Usage:
        tracker.track_state(state_name)
        tracker[state_name] = 'ON'
        tracker[state_name] = 'OFF'
    """
    table_args = "UUID INT, Count INT, State TEXT, Time TEXT"

    def __init__(self, *args, **kwargs):
        super(State, self).__init__(*args, **kwargs)
        self.state = None

    def insert(self, value):
        dt = datetime.datetime.now().strftime(self.time_fmt)
        self.count += 1
        self.state = value
        self.dbcon.execute("INSERT INTO {name} VALUES{args}".format(name=self.name, args=(self.tracker.uuid,
                                                                                   self.count,
                                                                                   self.state,
                                                                                   dt)))
        self.dbcon.commit()
        return self


class AnonymousUsageTracker(object):
    def __init__(self, uuid, tracker_file, submit_interval=None, check_interval=60 * 60):
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
                logging.info('AnonymousUsageTracker: A submission is overdue. Last submission was %s' % last_submission)
            except IndexError:
                logging.info('AnonymousUsageTracker: A submission is overdue')
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
        self._tables[name] = State(name, self, initial_state)

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
                    logger.info("AnonymousUsageTracker: Merging entries {n} through {m} of {name}".format(name=table,
                                                                                                          n=n,
                                                                                                          m=m))
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
            ftpinfo = self._ftp
            ftp = ftplib.FTP(host=ftpinfo['host'], user=ftpinfo['user'], passwd=ftpinfo['passwd'],
                             timeout=ftpinfo['timeout'])
        except ftplib.error_perm as e:
            logging.error(e)
            self.stop_watcher()
            return

        ftp.cwd(ftpinfo['path'])
        with open(self.tracker_file_part, 'rb') as _f:
            new_filename = self.uuid + '.db'
            ftp.storbinary('STOR %s' % new_filename, _f)
            self['__submissions__'] += 1
            logging.info('AnonymousUsageTracker: Submission to %s successful.' % ftpinfo['host'])
            self.merge_part()
            return True

    def start_watcher(self):
        """
        Start the watcher thread that tries to upload usage statistics.
        """
        logging.info('AnonymousUsageTracker: Starting watcher.')
        self._watcher = Thread(target=self._watcher_thread, name='usage_tracker')
        self._watcher.setDaemon(True)
        self._watcher_enabled = True
        self._watcher.start()

    def stop_watcher(self):
        """
        Stop the watcher thread that tries to upload usage statistics.
        """
        if self._watcher:
            self._watcher_enabled = False
            logging.info('AnonymousUsageTracker: Stopping watcher.')

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
            logging.info('AnonymousUsageTracker: Attempting to upload usage statistics.')
            if self._ftp:
                great_success = self.ftp_submit()
        logging.info('AnonymousUsageTracker: Watcher stopped.')


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
