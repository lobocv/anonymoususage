__author__ = 'calvin'

import time
import json
import socket
from threading import Thread

def run(port, cmds):
    HOST = '127.0.0.1'
    DISCOVER_PORT = 1213

    def communicate(sock, cmd):
        """
        Send a command and print it's response
        :param cmd:
        :return:
        """
        if not isinstance(cmd, dict):
            cmd()
        else:
            sock.send(json.dumps(cmd))
            time.sleep(1)
            print sock.recv(1024)

    # Connect to the discoverer socket
    print 'Opening discoverer port'
    discover_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    discover_socket.connect((HOST, DISCOVER_PORT))

    # Ask the process to create a new socket for communication
    print 'Requesting new socket'
    response = communicate(discover_socket, {'command': 'ACT', 'trackable': '', 'action': 'new_connection', 'args': (port,)})
    print response
    print 'Closing discoverer port'
    # Close the discoverer socket so that another process can connect to it
    discover_socket.shutdown(socket.SHUT_RDWR)
    discover_socket.close()

    print 'Connecting to new socket'
    # Connect to the new socket that we requested have made
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, port))

    # Run the commands
    for c in cmds:
        communicate(sock, c)


ports =[1214, 1215, 1216]
cmds = [
          [{'command': 'ACT', 'trackable': '', 'action': 'track_statistic', 'args': ('grids',)},
          {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'},
          {'command': 'SET', 'trackable': 'grids', 'attribute': 'count', 'value': 0},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'decrement', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'grids', 'action': 'decrement', 'args': (1,)},
          {'command': 'GET', 'trackable': 'grids', 'attribute': 'count'}],

          [{'command': 'ACT', 'trackable': '', 'action': 'track_statistic', 'args': ('lines',)},
          {'command': 'GET', 'trackable': 'lines', 'attribute': 'count'},
          {'command': 'SET', 'trackable': 'lines', 'attribute': 'count', 'value': 0},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'decrement', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'lines', 'action': 'decrement', 'args': (1,)},
          {'command': 'GET', 'trackable': 'lines', 'attribute': 'count'}],

          [{'command': 'ACT', 'trackable': '', 'action': 'track_statistic', 'args': ('screenshots',)},
          {'command': 'GET', 'trackable': 'screenshots', 'attribute': 'count'},
          {'command': 'SET', 'trackable': 'screenshots', 'attribute': 'count', 'value': 0},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'increment', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'decrement', 'args': (1,)},
          {'command': 'ACT', 'trackable': 'screenshots', 'action': 'decrement', 'args': (1,)},
          {'command': 'GET', 'trackable': 'screenshots', 'attribute': 'count'}]
        ]


for i in xrange(3):
    t = Thread(target=run, args=(ports[i], cmds[i]))
    t.start()
    time.sleep(2)