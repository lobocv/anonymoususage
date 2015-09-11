__author__ = 'calvin'

from anonymoususage.analysis import plot_statistic, plot_total_statistics, plot_state, plot_timer
from anonymoususage.datamanager import DataManager
from anonymoususage.database import DataBase
import sqlite3
import datetime
import logging
import os
from anonymoususage import tools

logger = logging.basicConfig(level=logging.DEBUG)
interval = datetime.timedelta(seconds=1)


dm = DataManager(config='anonymoususage.cfg')
# dm.consolidate_individuals(delete_parts=True)
# dm.consolidate_into_master()
if os.path.exists('./master.db'):
    os.remove('./master.db')
dm.download_master('./master.db')

db = sqlite3.connect('./master.db', factory=DataBase)
uuids = tools.get_uuid_list(db)


# uuid = "0076-7877-0001"
# dm.download_database(uuid, './%s.db' % uuid)
# db2 = sqlite3.connect('./%s.db' % uuid, factory=DataBase)
#
# rows = tools.get_rows(db2, 'power_cycles')
# tools.delete_row(db2, 'power_cycles', "Count", 6)
# rows_after = tools.get_rows(db2, 'power_cycles')
# plot_stat(db, ('total_line_length_m', 'power_cycles', 'screenshots'))
plot_state(db, ('units', 'grid_line_visibility'))
plot_timer(db, ('total_line_collection_time', 'total_grid_collection_time'))
plot_total_statistics(db, ('power_cycles', 'lines', 'grids', 'screenshots', '__submissions__'))
plot_statistic(db, ('total_line_length_m', 'power_cycles', 'lines', 'screenshots', '__submissions__'))

matplmatsdf=3