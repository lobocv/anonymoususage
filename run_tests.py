__author__ = 'Calvin'

import unittest
from StringIO import StringIO
from pprint import pprint

from unit_tests.statistic import StatisticTests
from unit_tests.state import StateTests

RUN_TESTS = [StatisticTests, StateTests]

total_errors = 0
total_failures = 0

for test in RUN_TESTS:
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(unittest.makeSuite(test))
    print '****************************************************************'
    print '                {}'.format(test.__name__)
    print '****************************************************************'
    if result.errors:
        print 'Errors: ', result.errors
        total_errors += len(result.errors)
    if result.failures:
        pprint(result.failures)
        total_failures += len(result.failures)
    stream.seek(0)
    print stream.read()

print 'Tests completed:\n\tTotal Errors: {errors}\n\tTotal failures: {fails}'.format(errors=total_errors,
                                                                                     fails=total_failures)