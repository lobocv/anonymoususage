__author__ = 'calvin'

import collections


def get_(obj, attr):
    """
    API call to a GET command.
    --------------------------
    GET Usage:
        command: 'GET'
        trackable: Trackable name or '' for the tracker itself
        attribute:  Attribute to get

    For example, the following query returns the statistic count of the 'grids_collected' trackable
        {'command': 'GET', 'trackable': 'grids_collected', 'attribute': 'count'}
    """
    if attr in obj.IPC_COMMANDS['GET']:
        value = getattr(obj, attr)
    else:
        raise ValueError('GET command is not available for %s' % attr)

    # Convert the response to string representation
    if isinstance(value, basestring):
        response = value
    elif isinstance(value, collections.Iterable):
        response = ','.join(map(str, value))
    else:
        response = str(value)

    return response


def set_(obj, attr, value):
    """
    API call to a SET command.
    --------------------------
    SET Usage:
        command: 'SET'
        trackable: Trackable name or '' for the tracker itself
        attribute:  Attribute to set
        value:  Value to assign

    For example, the following query sets the statistic count of the 'grids_collected' trackable to 50
        {'command': 'SET', 'trackable': 'grids_collected', 'attribute': 'count', 'value': 50}
    """
    if attr in obj.IPC_COMMANDS['SET']:
        setattr(obj, attr, value)
        return '{} set to {}'.format(attr, value)
    else:
        raise ValueError('SET command is not available for %s' % attr)


def act_(obj, action, *args):
    """
    API call to a ACT command.
    --------------------------
    ACT Usage:
        command: 'ACT'
        trackable: Trackable name or '' for the tracker itself
        action:  Action to call
        args:  List of arguments to the call

    For example, the following query starts the 'run_time' Timer
        {'command': 'ACT', 'trackable': 'run_time', 'action': 'start_timer', 'args': ()},
    """
    if action in obj.IPC_COMMANDS['ACT']:
        response = getattr(obj, action)(*args)
        return response or 'Call to %s has been processed' % action


COMMANDS = [get_, set_, act_]