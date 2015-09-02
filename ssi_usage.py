__author__ = 'calvin'

from anonymoususage.analysis import plot_stat
from anonymoususage.datamanager import DataManager
from anonymoususage.database import DataBase
import sqlite3
import datetime
import logging
import os

logger = logging.basicConfig(level=logging.DEBUG)
interval = datetime.timedelta(seconds=1)


dm = DataManager(config='anonymoususage.cfg')
# dm.consolidate_into_master()
if not os.path.exists('./master.db'):
    dm.download_master('./master.db')

db = sqlite3.connect('./master.db', factory=DataBase)
db.row_factory = sqlite3.Row

uuid = "0076-7877-0001"
dm.download_database(uuid, './%s.db' % uuid)
db2 = sqlite3.connect('./%s.db' % uuid, factory=DataBase)
db2.row_factory = sqlite3.Row

# plot_stat(db, ('total_line_length_m', 'power_cycles', 'screenshots'))
plot_stat(db, ('operating_time',), uuid=None)
sdf=3