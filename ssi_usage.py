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

# tracker = AnonymousUsageTracker(uuid='abc',
#                                 tracker_file='/home/calvin/test/ftp/usage/abc.db',
#                                 config='./anonymoususage.cfg',
#                                 check_interval=datetime.timedelta(seconds=5),
#                                 submit_interval=interval)

dbname = "0076-7877-0001.db"
if not os.path.exists('./%s' % dbname):
    dm = DataManager(config='/home/calvin/smc/pygame/LMX/lmx/anonymoususage.cfg')
    # dm.consolidate()
    dm.download_database(dbname[:-3], './%s' % dbname)

db = sqlite3.connect('./%s' % dbname, factory=DataBase)
db.row_factory = sqlite3.Row

plot_stat(db, ('total_line_length_m', 'power_cycles', 'screenshots'))
sdf=3