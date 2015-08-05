__version__ = '1.0'

try:
    from anonymoususage import AnonymousUsageTracker
    from state import NO_STATE
    from exceptions import *
except ImportError as e:
    print e
