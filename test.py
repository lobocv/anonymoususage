__author__ = 'calvin'

import os
import time
import datetime
from anonymoususage import AnonymousUsageTracker


usage_tracker = AnonymousUsageTracker(config='./anonymoususage.cfg',
                                           uuid="ASDFGH",
                                           tracker_file='./test.db',
                                           submit_interval=datetime.timedelta(seconds=10),
                                           check_interval=datetime.timedelta(minutes=2))
usage_tracker.track_statistic('grids')
usage_tracker.track_statistic('lines')

while 1:
    usage_tracker['grids'] += 1
    time.sleep(2)