__version__ = '1.10'

try:
    from anonymoususage import AnonymousUsageTracker
    from tables import NO_STATE
    from exceptions import *
except ImportError as e:
    print e
