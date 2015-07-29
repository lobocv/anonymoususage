__author__ = 'calvin'

from anonymoususage import AnonymousUsageTracker
from anonymoususage.tools import *
from anonymoususage.analysis import *
import datetime
import logging
import time

logger = logging.basicConfig(level=logging.DEBUG)
interval = datetime.timedelta(seconds=1)

tracker = AnonymousUsageTracker(uuid='abc',
                                tracker_file='/home/calvin/test/ftp/usage/abc.db',
                                config='./anonymoususage.cfg',
                                check_interval=datetime.timedelta(seconds=5),
                                submit_interval=interval)


db = tracker.dbcon_master
rc = get_table_list(db)

plot_stat(tracker.dbcon_master, 'Grids')