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
        {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'},
        {'command': 'SET', 'trackable': 'grids', 'attribute': 'count', 'value': 50},
        {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'},
        {'command': 'ACT', 'trackable': 'grids', 'action': 'increment', 'args': (1,)},
        {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'},
        {'command': 'ACT', 'trackable': 'grids', 'action': 'decrement', 'args': (1,)},
        {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'},

    # State
        {'command': 'GET', 'trackable': 'units', 'attribute': 'state'},
        {'command': 'SET', 'trackable': 'units', 'attribute': 'state', 'value': 'Metric'},
        {'command': 'GET', 'trackable': 'units', 'attribute': 'state'},

        # Timer
        {'command': 'GET', 'trackable': 'run_time', 'attribute': 'total_seconds'},
        {'command': 'ACT', 'trackable': 'run_time', 'action': 'start_timer', 'args': ()},
        lambda: time.sleep(1),
        {'command': 'ACT', 'trackable': 'run_time', 'action': 'pause_timer', 'args': ()},
        lambda: time.sleep(5),
        {'command': 'ACT', 'trackable': 'run_time', 'action': 'resume_timer', 'args': ()},
        lambda: time.sleep(1),
        {'command': 'ACT', 'trackable': 'run_time', 'action': 'stop_timer', 'args': ()},
        {'command': 'GET', 'trackable': 'run_time', 'attribute': 'total_seconds'},
        {'command': 'GET', 'trackable': 'run_time', 'attribute': 'total_minutes'},
        {'command': 'GET', 'trackable': 'run_time', 'attribute': 'total_hours'},
        {'command': 'GET', 'trackable': 'run_time', 'attribute': 'total_days'},

        # Sequence
        {'command': 'GET', 'trackable': 'my_sequence', 'attribute': 'count'},
        {'command': 'SET', 'trackable': 'my_sequence', 'attribute': 'checkpoint', 'value': 'A'},
        {'command': 'SET', 'trackable': 'my_sequence', 'attribute': 'checkpoint', 'value': 'B'},
        {'command': 'GET', 'trackable': 'my_sequence', 'attribute': 'sequence'},
        {'command': 'SET', 'trackable': 'my_sequence', 'attribute': 'checkpoint', 'value': 'C'},
        {'command': 'GET', 'trackable': 'my_sequence', 'attribute': 'checkpoint'},
        {'command': 'SET', 'trackable': 'my_sequence', 'attribute': 'checkpoint', 'value': 'D'},
        {'command': 'GET', 'trackable': 'my_sequence', 'attribute': 'count'},
        {'command': 'ACT', 'trackable': '', 'action': 'disable', 'args': ()},
        {'command': 'ACT', 'trackable': '', 'action': 'submit_statistics', 'args': ()},
        {'command': 'ACT', 'trackable': '', 'action': 'enable', 'args': ()},

]


for cmd in cmds:
    if not isinstance(cmd, dict):
        cmd()
    else:
        s.send(json.dumps(cmd))
        print s.recv(1024)

