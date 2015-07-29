__author__ = 'calvin'

from anonymoususage import AnonymousUsageTracker
from anonymoususage.tools import *
from anonymoususage.analysis import *
from anonymoususage.database import DataBase
import sqlite3
import datetime
import logging
import time
import os

logger = logging.basicConfig(level=logging.DEBUG)
interval = datetime.timedelta(seconds=1)

tracker = AnonymousUsageTracker(uuid='abc',
                                tracker_file='/home/calvin/test/ftp/usage/abc.db',
                                config='./anonymoususage.cfg',
                                check_interval=datetime.timedelta(seconds=5),
                                submit_interval=interval)

if not os.path.exists('./TestUUID.db'):
    dm = DataManager(config='./anonymoususage.cfg')
    dm.download_database('TestUUID', './TestUUID.db')

db = sqlite3.connect('./TestUUID.db', factory=DataBase)
db.row_factory = sqlite3.Row

plot_stat(db, 'Grids')