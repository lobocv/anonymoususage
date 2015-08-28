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

    def consolidate(self, delete_parts=True):
        """
        Consolidate partial database information into a single .db file.
        """
        ftpinfo = self._ftp
        ftp = ftplib.FTP()
        ftp.connect(host=ftpinfo['host'], port=ftpinfo['port'], timeout=ftpinfo['timeout'])
        ftp.login(user=ftpinfo['user'], passwd=ftpinfo['passwd'], acct=ftpinfo['acct'])
        ftp.cwd(ftpinfo['path'])

        files = ftp.nlst()

        uuid_regex = re.compile(r'(.*?)_\d*.db')
        uuids = defaultdict(list)
        for f in files:
            uuid = uuid_regex.findall(f)
            if uuid:
                uuids[uuid[0]].append(f)

        tmpdir = tempfile.mkdtemp('anonymoususage')
        for uuid, partial_dbs in uuids.iteritems():
            # partial_regex = re.compile(r'%s_\d+.db' % uuid)
            # partial_dbs = partial_regex.findall(all_files)
            if len(partial_dbs):
                logger.debug('Consolidating UUID %s. %d partial databases found.' % (uuid, len(partial_dbs)))
                # Look for the master database, if there isn't one, use one of the partials as the new master
                masterfilename = '%s.db' % uuid if '%s.db' % uuid in files else partial_dbs[0]

                # Download the master database
                local_master_path = os.path.join(tmpdir, masterfilename)
                with open(local_master_path, 'wb') as _f:
                    ftp.retrbinary('RETR %s' % masterfilename, _f.write)

                dbmaster = sqlite3.connect(local_master_path)

                for db in partial_dbs:
                    if db == masterfilename:
                        continue
                    # Download each partial database and merge it with the local master
                    logger.debug('Consolidating part %s' % db)
                    local_partial_path = os.path.join(tmpdir, db)
                    with open(local_partial_path, 'wb') as _f:
                        ftp.retrbinary('RETR %s' % db, _f.write)
                    dbpart = sqlite3.connect(local_partial_path)
                    merge_databases(dbmaster, dbpart)
                    dbpart.close()
                dbmaster.close()

                # Upload the merged local master back to the FTP
                logger.debug('Uploading master database for UUID %s' % uuid)
                with open(local_master_path, 'rb') as _f:
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

    def download_database(self, uuid, local_path):
        ftpinfo = self._ftp
        ftp = ftplib.FTP()
        ftp.connect(host=ftpinfo['host'], port=ftpinfo['port'], timeout=ftpinfo['timeout'])
        ftp.login(user=ftpinfo['user'], passwd=ftpinfo['passwd'], acct=ftpinfo['acct'])
        ftp.cwd(ftpinfo['path'])
        ftp_download(ftp, uuid + '.db', local_path)


def plot_stat(dbconn, table_names, date_limits=(None, None)):

    fig, ax = plt.subplots()

    ax.xaxis.set_major_formatter(DateFormatter("%d %B %Y"))
    ax.fmt_xdata = DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.set_xlabel('Date')
    ax.set_ylabel('Count')
    plotted_tables = set()
    for table_name in table_names:
        rows = get_rows(dbconn, table_name)
        data = []
        for r in rows:
            dt = datetime.datetime.strptime(r['Time'], "%d/%m/%Y %H:%M:%S")
            data.append((dt, r['Count']))

        if data:
            data.sort()
            times, counts = zip(*data)
            ax.plot_date(times, counts, '-', label=table_name)
            plotted_tables.add(table_name)
        else:
            logging.warning('No data for %s. Omitting from plot.' % table_name)
    ax.legend(plotted_tables, loc='center left', bbox_to_anchor=(0, 1),
              fancybox=True, ncol=max(1, 3 * (len(plotted_tables) / 3)))

    if date_limits:
        ax.set_xlim(*date_limits)
    else:
        fig.autofmt_xdate()
    fig.set_size_inches(12, 8, forward=True)
    plt.show()

if __name__ == '__main__':

    dm = DataManager('/home/calvin/smc/pygame/LMX/server.cfg')

    dm.consolidate()