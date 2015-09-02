__author__ = 'calvin'

import tempfile
import shutil
import re
import ConfigParser
import os
import ftplib
import logging
import sqlite3

from .tools import *
from collections import defaultdict


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

        uuid_regex = re.compile(r'(.*?)_Part\d*.db')
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
                logging.debug('Consolidating UUID %s. %d partial databases found.' % (uuid, len(partial_dbs)))
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
                    logging.debug('Consolidating part %s' % db)
                    local_partial_path = os.path.join(tmpdir, db)
                    with open(local_partial_path, 'wb') as _f:
                        ftp.retrbinary('RETR %s' % db, _f.write)
                    dbpart = sqlite3.connect(local_partial_path)
                    merge_databases(db_submaster, dbpart)
                    dbpart.close()

                # Upload the merged local submaster back to the FTP
                logging.debug('Uploading submaster database for UUID %s' % uuid)
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

        uuid_regex = re.compile(r'(.*?)\.db')
        uuids = []
        for f in files:
            uuid = uuid_regex.findall(f)
            if uuid and 'Part' not in uuid[0]:
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
        logging.debug('Uploading master database for UUID %s' % uuid)
        with open(local_submaster_path, 'rb') as _f:
            ftp.storbinary('STOR master.db', _f)

    def download_database(self, uuid, local_path):
        ftp = self.login_ftp()
        ftp_download(ftp, uuid + '.db', local_path)

    def download_master(self, local_path):
        self.download_database('master', local_path)