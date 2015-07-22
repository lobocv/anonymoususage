__version__ = '1.0'

try:
    from anonymoususage import AnonymousUsageTracker
    from exceptions import *
except ImportError as e:
    print e
