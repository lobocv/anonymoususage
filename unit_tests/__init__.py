__author__ = 'calvin'

import unittest
import tempfile
import os
import shutil

from anonymoususage import AnonymousUsageTracker


class AnonymousUsageTests(unittest.TestCase):

    def __init__(self, *args):
        super(AnonymousUsageTests, self).__init__(*args)

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        trackerfile = os.path.join(self.tmpdir, 'au_unittests.db')
        self.tracker = AnonymousUsageTracker('UnitTests', trackerfile)
        self.tracker.track_statistic('Statistic')
        self.tracker.track_state('State', True)
        self.tracker.track_time('Timer')
        self.tracker.track_sequence('Sequence', ['A', 'B', 'C', 'D'])

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()


