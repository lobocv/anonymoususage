__author__ = 'calvin'

import requests
import json
import logging


HQ_DEFAULT_TIMEOUT = 10
SMTP_DEFAULT_TIMEOUT = 5


def upload_stats(server, payload, timeout=HQ_DEFAULT_TIMEOUT):
    """
    Upload a report to the server.
    :param payload: Dictionary (JSON serializable) of crash data.
    :return: server response
    """
    data = json.dumps(payload)
    try:
        r = requests.post(server + '/usagestats/upload', data=data, timeout=timeout)
    except Exception as e:
        logging.error(e)
        return False
    return r
