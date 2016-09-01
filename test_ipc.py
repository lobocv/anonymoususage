__author__ = 'calvin'

import sys
import time
import json
import datetime
from anonymoususage import AnonymousUsageTracker


mode = sys.argv[1]

HOST = ''
PORT = 1214
if mode == '0':

    usage_tracker = AnonymousUsageTracker(uuid="ASDFGH",
                                          filepath='./test.db')
    usage_tracker.track_statistic('grids')
    usage_tracker.track_statistic('lines')
    usage_tracker.track_time('run_time')
    usage_tracker.track_sequence('my_sequence', checkpoints=['A', 'B', 'C', 'D'])
    usage_tracker.track_state('units', 'Metric')

    usage_tracker['grids'] = 10
    usage_tracker['units'] = 'US Standard'
    usage_tracker['run_time'].start_timer()
    time.sleep(1.1)
    usage_tracker['run_time'].stop_timer()

    s = usage_tracker.open_socket(HOST, PORT)
    usage_tracker.monitor_socket(s)
elif mode == '1':

    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))

    cmds = [# Statistic
            {'command': 'GET', 'trackable': 'grids', 'field': 'count'},
            {'command': 'SET', 'trackable': 'grids', 'field': 'count', 'value': 50},
            {'command': 'GET', 'trackable': 'grids', 'field': 'count'},

        # State
            {'command': 'GET', 'trackable': 'units', 'field': 'state'},
            {'command': 'SET', 'trackable': 'units', 'field': 'state', 'value': 'Metric'},
            {'command': 'GET', 'trackable': 'units', 'field': 'state'},

            # Timer
            {'command': 'GET', 'trackable': 'run_time', 'field': 'total_seconds'},
            {'command': 'ACT', 'trackable': 'run_time', 'action': 'start_timer', 'args': ()},
            lambda: time.sleep(1),
            {'command': 'ACT', 'trackable': 'run_time', 'action': 'pause_timer', 'args': ()},
            lambda: time.sleep(5),
            {'command': 'ACT', 'trackable': 'run_time', 'action': 'resume_timer', 'args': ()},
            lambda: time.sleep(1),
            {'command': 'ACT', 'trackable': 'run_time', 'action': 'stop_timer', 'args': ()},
            {'command': 'GET', 'trackable': 'run_time', 'field': 'total_seconds'},
            {'command': 'GET', 'trackable': 'run_time', 'field': 'total_minutes'},
            {'command': 'GET', 'trackable': 'run_time', 'field': 'total_hours'},
            {'command': 'GET', 'trackable': 'run_time', 'field': 'total_days'},

            # Sequence
            {'command': 'GET', 'trackable': 'my_sequence', 'field': 'count'},
            {'command': 'SET', 'trackable': 'my_sequence', 'field': 'checkpoint', 'value': 'A'},
            {'command': 'SET', 'trackable': 'my_sequence', 'field': 'checkpoint', 'value': 'B'},
            {'command': 'GET', 'trackable': 'my_sequence', 'field': 'sequence'},
            {'command': 'SET', 'trackable': 'my_sequence', 'field': 'checkpoint', 'value': 'C'},
            {'command': 'GET', 'trackable': 'my_sequence', 'field': 'checkpoint'},
            {'command': 'SET', 'trackable': 'my_sequence', 'field': 'checkpoint', 'value': 'D'},
            {'command': 'GET', 'trackable': 'my_sequence', 'field': 'count'},

    ]

    for cmd in cmds:
        if not isinstance(cmd, dict):
            cmd()
        else:
            s.send(json.dumps(cmd))
            print s.recv(1024)

