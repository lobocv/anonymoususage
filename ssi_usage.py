__author__ = 'calvin'

from anonymoususage.analysis import plot_statistic, plot_total_statistics, plot_state, plot_timer
from anonymoususage.analysis import DataManager, DataBase
import sqlite3
import datetime
import logging
import os
from anonymoususage import tools

logger = logging.basicConfig(level=logging.DEBUG)
interval = datetime.timedelta(seconds=1)

dm = DataManager(config='anonymoususage.cfg')
dm.consolidate_individuals(delete_parts=True)
dm.consolidate_into_master()
if os.path.exists('./master.db'):
    os.remove('./master.db')
dm.download_master('./master.db')

db = sqlite3.connect('./master.db', factory=DataBase)
db.rename_table('total_line_length_m', 'line_length_m')
db.rename_table('total_line_length_m', 'power_cycles')
db.rename_table('total_line_collection_time', 'line_collection_time')
db.rename_table('total_grid_area_m2', 'grid_area_m2')
db.rename_table('total_grid_line_length_m', 'grid_line_length_m')
db.rename_table('total_grid_collection_time', 'grid_collection_time')

uuids = tools.get_uuid_list(db)


plot_state(db, ('units', 'grid_line_visibility'))
plot_timer(db, ('line_collection_time', 'grid_collection_time'))
plot_total_statistics(db, ('power_cycles', 'lines', 'grids', 'screenshots', '__submissions__'))
plot_statistic(db, ('line_length_m', 'power_cycles', 'lines', 'screenshots', '__submissions__'))

matplmatsdf=3