__author__ = 'calvin'

import time
import json
import socket


HOST = ''
PORT = 1213

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))

cmds = [{'command': 'ACT', 'trackable': '', 'action': 'track_statistic', 'args': ('grids',)},
        {'command': 'ACT', 'trackable': '', 'action': 'track_statistic', 'args': ('lines',)},
        {'command': 'ACT', 'trackable': '', 'action': 'track_time', 'args': ('run_time',)},
        {'command': 'ACT', 'trackable': '', 'action': 'track_sequence', 'args': ('my_sequence', ['A', 'B', 'C', 'D'])},
        {'command': 'ACT', 'trackable': '', 'action': 'track_state', 'args': ('units', 'Metric')},
        {'command': 'ACT', 'trackable': '', 'action': 'get_table_info', 'args': ()},
        ]

for cmd in cmds:
    if not isinstance(cmd, dict):
        cmd()
    else:
        s.send(json.dumps(cmd))
        print s.recv(1024)


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

