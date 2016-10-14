__author__ = 'calvin'

import os
import time
import datetime
from anonymoususage import AnonymousUsageTracker


usage_tracker = AnonymousUsageTracker.load_from_configuration('./anonymoususage.cfg',
                                      uuid="Calvin")
AnonymousUsageTracker.MAX_ROWS_PER_TABLE = 5
usage_tracker.track_state('some_state', '0')
usage_tracker.track_state('some_state2', '0')
usage_tracker.track_statistic('some_statistic')
usage_tracker.track_time('some_timer')
usage_tracker.track_sequence('some_sequence', [1, 2, 3])

for i in xrange(10):
    usage_tracker['some_state'] = str(i+1)
    usage_tracker['some_statistic'] += 1
    usage_tracker['some_timer'].start_timer()
    time.sleep(1)
    usage_tracker['some_timer'].stop_timer()
    usage_tracker['some_sequence'] = 1
    usage_tracker['some_sequence'] = 2
    usage_tracker['some_sequence'] = 3

usage_tracker.to_file('summary.csv')