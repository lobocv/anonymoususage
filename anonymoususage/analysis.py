__author__ = 'calvin'


import tempfile
import shutil
import re
import ConfigParser
import os
import logging
import datetime
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

from collections import defaultdict

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('AnonymousUsage')
logger.setLevel(logging.DEBUG)

from tools import *


class DataManager(object):

    def __init__(self, config=''):
        if config:
            self.load_configuration(config)

    def load_configuration(self, config):
        """
        Load FTP server credentials from a configuration file.
        """
        cfg = ConfigParser.ConfigParser()
        with open(config, 'r') as _f:
            cfg.readfp(_f)
            if cfg.has_section('FTP'):
                self.setup_ftp(**dict(cfg.items('FTP')))

    def setup_ftp(self, host, user, passwd, path='', acct='', port=21, timeout=5):
        self._ftp = dict(host=host, user=user, passwd=passwd, acct=acct,
                         timeout=int(timeout), path=path, port=int(port))

    def login_ftp(self):
        ftpinfo = self._ftp
        ftp = ftplib.FTP()
        ftp.connect(host=ftpinfo['host'], port=ftpinfo['port'], timeout=ftpinfo['timeout'])
        ftp.login(user=ftpinfo['user'], passwd=ftpinfo['passwd'], acct=ftpinfo['acct'])
        ftp.cwd(ftpinfo['path'])
        return ftp

    def consolidate_individuals(self, delete_parts=True):
        """
        Consolidate partial database information into a single .db file.
        """
        ftp = self.login_ftp()
        files = ftp.nlst()

        uuid_regex = re.compile(r'(.*?)_\d*.db')
        uuids = defaultdict(list)
        for f in files:
            uuid = uuid_regex.findall(f)
            if uuid:
                uuids[uuid[0]].append(f)

        tmpdir = tempfile.mkdtemp('anonymoususage')

        master_exists = "master.db" in files
        if master_exists:
            master_path = os.path.join(tmpdir, 'master.db')
            self.download_database("master", master_path)
            db_master = sqlite3.connect(master_path)
            logging.debug("Master database found on FTP server.")
        else:
            logging.debug("No master database found on FTP server.")
            db_master = None

        for uuid, partial_dbs in uuids.iteritems():
            # partial_regex = re.compile(r'%s_\d+.db' % uuid)
            # partial_dbs = partial_regex.findall(all_files)
            if len(partial_dbs):
                logger.debug('Consolidating UUID %s. %d partial databases found.' % (uuid, len(partial_dbs)))
                # Look for the master database, if there isn't one, use one of the partials as the new master
                submaster_filename = '%s.db' % uuid if '%s.db' % uuid in files else partial_dbs[0]

                # Download the submaster database
                local_submaster_path = os.path.join(tmpdir, submaster_filename)
                with open(local_submaster_path, 'wb') as _f:
                    ftp.retrbinary('RETR %s' % submaster_filename, _f.write)

                db_submaster = sqlite3.connect(local_submaster_path)

                for db in partial_dbs:
                    if db == submaster_filename:
                        continue
                    # Download each partial database and merge it with the local submaster
                    logger.debug('Consolidating part %s' % db)
                    local_partial_path = os.path.join(tmpdir, db)
                    with open(local_partial_path, 'wb') as _f:
                        ftp.retrbinary('RETR %s' % db, _f.write)
                    dbpart = sqlite3.connect(local_partial_path)
                    merge_databases(db_submaster, dbpart)
                    dbpart.close()

                # Upload the merged local submaster back to the FTP
                logger.debug('Uploading submaster database for UUID %s' % uuid)
                with open(local_submaster_path, 'rb') as _f:
                    ftp.storbinary('STOR %s.db' % uuid, _f)
                try:
                    ftp.mkd('.merged')
                except ftplib.error_perm:
                    pass

                for db in partial_dbs:
                    if delete_parts:
                        ftp.delete(db)
                    else:
                        ftp.rename(db, os.path.join('.merged', db))

        shutil.rmtree(tmpdir)
        ftp.close()

    def consolidate_into_master(self):
        ftp = self.login_ftp()
        files = ftp.nlst()

        uuid_regex = re.compile(r'(.*?).db')
        uuids = []
        for f in files:
            uuid = uuid_regex.findall(f)
            if uuid:
                uuids.append(uuid[0])

        tmpdir = tempfile.mkdtemp('anonymoususage')
        # Download the master data base if it exists on the FTP server
        master_exists = "master.db" in files
        if master_exists:
            master_path = os.path.join(tmpdir, 'master.db')
            self.download_database("master", master_path)
            db_master = sqlite3.connect(master_path)
            logging.debug("Master database found on FTP server.")
        else:
            logging.debug("No master database found on FTP server.")
            db_master = None

        for uuid in uuids:
            # Download the submaster database
            submaster_filename = '%s.db' % uuid
            local_submaster_path = os.path.join(tmpdir, submaster_filename)
            with open(local_submaster_path, 'wb') as _f:
                ftp.retrbinary('RETR %s' % submaster_filename, _f.write)

            db_submaster = sqlite3.connect(local_submaster_path)

            if db_master is None:
                logging.debug("Using %s as master database." % submaster_filename)
                db_master = db_submaster
            else:
                logging.debug("Merging %s into the master database." % submaster_filename)
                merge_databases(db_master, db_submaster)
                db_submaster.close()

        # Upload the merged local submaster back to the FTP
        logger.debug('Uploading master database for UUID %s' % uuid)
        with open(local_submaster_path, 'rb') as _f:
            ftp.storbinary('STOR master.db', _f)

    def download_database(self, uuid, local_path):
        ftp = self.login_ftp()
        ftp_download(ftp, uuid + '.db', local_path)


def get_sorted_rows(dbconn, table_name):
    rows = get_rows(dbconn, table_name)
    data = []
    for r in rows:
        dt = datetime.datetime.strptime(r['Time'], "%d/%m/%Y %H:%M:%S")
        data.append((dt, r['Count']))
        data.sort()
    return data

def plot_stat(dbconn, table_names, date_limits=(None, None)):

    fig, ax = plt.subplots()

    ax.xaxis.set_major_formatter(DateFormatter("%d %B %Y"))
    ax.fmt_xdata = DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    plotted_tables = set()
    for table_name in table_names:
        data = get_sorted_rows(dbconn, table_name)
        if data:
            times, counts = zip(*data)
            ax.plot_date(times, counts, '-', label=table_name)
            plotted_tables.add(table_name)
        else:
            logging.warning('No data for %s. Omitting from plot.' % table_name)
    ax.legend(plotted_tables, loc='center left', bbox_to_anchor=(0, 1),
              fancybox=True, ncol=max(1, 3 * (len(plotted_tables) / 3)))

    if date_limits[0] and date_limits[1]:
        ax.set_xlim(*date_limits)
    else:
        fig.autofmt_xdate()
    fig.set_size_inches(12, 8, forward=True)
    plt.show()


if __name__ == '__main__':

    dm = DataManager('/home/calvin/smc/pygame/LMX/server.cfg')

    dm.consolidate()