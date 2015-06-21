__author__ = 'calvin'

import sqlite3
import re
import ConfigParser
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

    def consolidate(self):
        """
        Consolidate partial database information into a single .db file.
        """
        ftpinfo = self._ftp
        ftp = ftplib.FTP()
        ftp.connect(host=ftpinfo['host'], port=ftpinfo['port'], timeout=ftpinfo['timeout'])
        ftp.login(user=ftpinfo['user'], passwd=ftpinfo['passwd'], acct=ftpinfo['acct'])
        ftp.cwd(ftpinfo['path'])

        files = ftp.nlst()
        all_files = ' '.join(files)
        uuids = set(re.findall(r'\s(.*?)_\d+', all_files))

        for uuid in uuids:
            partial_dbs = re.findall(r'[^\s].*?_\d+.db', all_files)
            for db in partial_dbs:
                dbconn = sqlite3.connect(db)
                get_table_list(dbconn)
                tables = get_table_list()




if __name__ == '__main__':
    dm = DataManager('../anonymoususage.cfg')

    dm.consolidate()