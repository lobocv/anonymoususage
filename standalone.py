import sys
import os
import logging
import logging.handlers
import argparse
from anonymoususage.api import UsageTrackerServer, Views

__help__ = \
    '''
This application creates and starts a new anonymous usage tracker. Use the API to communicate with
the tracker through a socket to setup and track statistics in your application.


standalone.py 'USER100049' localhost 1213 ./my_statistics.db --config ./server.config --username calvin --password supersecret

                API
===============================
{}
    '''.format('\n\n'.join(v.api_help() for v in Views))


def run_server(uuid, host, port, db_path, config=None, username=None, password=None):

    print __help__
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(os.path.splitext(db_path)[0] + '.log', maxBytes=1000000,
                                                   backupCount=5)
    logger.addHandler(handler)

    logging.info('Creating Usage Tracker..')
    if config:
        server = UsageTrackerServer.load_from_configuration(config, uuid, filepath=db_path)
    else:
        server = UsageTrackerServer(uuid=uuid, filepath=db_path)

    logging.info('Opening connection..')
    if host == 'localhost':
        host = '127.0.0.1'

    logging.info('Starting tracker..')

    server.run(host, port, username=username, password=password)
    logging.info('Stopping tracker..')


if __name__ == '__main__':

    parser = argparse.ArgumentParser(__help__)
    parser.add_argument('uuid', nargs=1, type=str, help='Unique identifier associated with the user')
    parser.add_argument('host', nargs=1, type=str, help='IP to host the server')
    parser.add_argument('port', nargs=1, type=int, help='Port to host the server')
    parser.add_argument('db_path', nargs=1, type=str, help='Path to store the database')
    parser.add_argument('--username', nargs=1, default=[None], type=str, dest='username', help='Username used for Digest secure API calls')
    parser.add_argument('--password', nargs=1, default=[None], type=str, dest='password', help='Password used for Digest secure API calls')
    parser.add_argument('--config', nargs=1, default=[None], type=str, dest='config', help='Path to the configuration file')

    if len(sys.argv) == 1:
        parser.print_usage()
        exit()

    args = parser.parse_args()

    run_server(args.uuid[0], args.host[0], args.port[0], args.db_path[0],
               config=args.config[0],
               username=args.username[0],
               password=args.password[0])
