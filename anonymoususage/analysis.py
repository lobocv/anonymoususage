__author__ = 'calvin'


import tempfile
import re
import ConfigParser
import os
import logging

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

        tmpdir = tempfile.mkdtemp('anonymoususage')
        for uuid in uuids:

            partial_dbs = re.findall(r'%s_\d+.db' % uuid, all_files)
            if len(partial_dbs):
                logger.debug('Consolidating UUID %s. %d partial databases found.' % (uuid, len(partial_dbs)))
                # Look for the master database, if there isn't one, use one of the partials as the new master
                masterfilename = '%s.db' % uuid if '%s.db' % uuid in files else partial_dbs[0]

                # Download the master database
                local_master_path = os.path.join(tmpdir, masterfilename)
                with open(local_master_path, 'wb') as _f:
                    ftp.retrlines('RETR %s' % masterfilename, _f.write)

                dbmaster = sqlite3.connect(local_master_path)

                for db in partial_dbs:
                    if db == masterfilename:
                        continue
                    # Download each partial database and merge it with the local master
                    logger.debug('Consolidating part %s' % db)
                    local_partial_path = os.path.join(tmpdir, db)
                    with open(local_partial_path, 'wb') as _f:
                        ftp.retrlines('RETR %s' % db, _f.write)
                    dbpart = sqlite3.connect(local_partial_path)
                    merge_databases(dbmaster, dbpart)
                    dbpart.close()
                dbmaster.close()





if __name__ == '__main__':
    dm = DataManager('../anonymoususage.cfg')

    dm.consolidate()