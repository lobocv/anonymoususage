from anonymoususage import AnonymousUsageTracker
from anonymoususage.tables import TRACKABLES
from anonymoususage.api import COMMANDS
import sys

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



try:
    UUID, HOST, PORT, FILEPATH = sys.argv[1:]
except Exception as e:
    print __help__
    sys.exit(-1)


print 'Creating Usage Tracker..'
usage_tracker = AnonymousUsageTracker(uuid=UUID,
                                      filepath=FILEPATH)

print 'Opening connection..'
if HOST in ('localhost', '127.0.0.1'):
    HOST = ''

sock = usage_tracker.open_socket(HOST, int(PORT))

print 'Starting tracker..'
usage_tracker.monitor_socket(sock)

print 'Stopping tracker..'

