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
        self.tracker.track_statistic('Cheese')
        self.tracker.track_state('Fresh', True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_statistic(self):
        cheese = self.tracker['Cheese']
        cheese += 1
        nrows = cheese.get_number_of_rows()
        self.assertEquals(1, nrows)

if __name__ == '__main__':
    unittest.main()


