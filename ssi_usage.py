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
if not os.path.exists('./master.db'):
    dm.download_master('./master.db')

db = sqlite3.connect('./master.db', factory=DataBase)
db.row_factory = sqlite3.Row

# plot_stat(db, ('total_line_length_m', 'power_cycles', 'screenshots'))
plot_stat(db, ('operating_time', 'power_cycles'))
sdf=3