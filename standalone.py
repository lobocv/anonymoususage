import os
import logging
import sys
import argparse

from anonymoususage import AnonymousUsageTracker
from anonymoususage.tables import TRACKABLES
from anonymoususage.api import COMMANDS

__help__ = \
    '''
    This application creates and starts a new anonymous usage tracker. Use the API to communicate with
    the tracker through a socket to setup and track statistics in your application.


    Call Arguments:
         UUID        - Unique identifier for the user being tracked (string)
         HOST        - Host address to open the socket under (use 'localhost' or '127.0.0.1' for local)
         PORT        - Port to open the socket under
         FILEPATH    - File path to write the database

    Example

    standalone 'USER100049' localhost 1213 ./my_statistics.db

    ============================================================================
    =                                  API                                     =
    ============================================================================
    {API}

    ============================================================================
    =                             TRACKABLE API                                =
    ============================================================================

    {TRACKABLES}
    '''.format(API='\n'.join(c.__doc__ for c in COMMANDS),
               TRACKABLES='\n'.join(t.api_help() for t in TRACKABLES))


def run_server(uuid, host, port, db_path, config=None):

    logging.basicConfig(filename=os.path.splitext(FILEPATH)[0] + '.log', level=logging.DEBUG)

    logging.info('Creating Usage Tracker..')
    if config:
        usage_tracker = AnonymousUsageTracker.load_from_configuration(config, uuid, filepath=db_path)
    else:
        usage_tracker = AnonymousUsageTracker(uuid=uuid,
                                              filepath=db_path)

    logging.info('Opening connection..')
    if host in ('localhost', '127.0.0.1'):
        host = ''

    sock = usage_tracker.open_socket(host, port)

    logging.info('Starting tracker..')
    usage_tracker.monitor_socket(sock)

    logging.info('Stopping tracker..')


if __name__ == '__main__':

    parser = argparse.ArgumentParser('Start a server that can be communicated through sockets to track user behaviour')
    parser.add_argument('uuid', nargs=1, type=str)
    parser.add_argument('host', nargs=1, type=str)
    parser.add_argument('port', nargs=1, type=int)
    parser.add_argument('db_path', nargs=1, type=str)
    parser.add_argument('--config', nargs=1, default=[None], type=str, dest='config')

    args = parser.parse_args()
    try:
        UUID, HOST, PORT, FILEPATH = sys.argv[1:]
    except Exception as e:
        print __help__
        sys.exit(-1)
    else:
        run_server(args.uuid[0], args.host[0], args.port[0], args.db_path[0], config=args.config[0])
