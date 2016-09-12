from . import AnonymousUsageTests


class StatisticTests(AnonymousUsageTests):

    def test_increment(self):
        s = self.tracker['Statistic']
        # We must remember to test both ways of incrementing the stat due to custom __setitem__ implementation
        s += 1
        self.tracker['Statistic'] += 1

        nrows = s.get_number_of_rows()
        self.assertEquals(2, nrows)
        self.assertEquals(s.count, 2)
        s += 10
        self.assertEquals(s.count, 12)

    def test_decrement(self):
        s = self.tracker['Statistic']
        s -= 1
        self.tracker['Statistic'] -= 1
        nrows = s.get_number_of_rows()
        self.assertEquals(2, nrows)
        self.assertEquals(s.count, -2)

        s -= 10
        self.assertEquals(s.count, -12)

    def test_set_value(self):
        s = self.tracker['Statistic']
        self.tracker['Statistic'] = 100
        nrows = s.get_number_of_rows()
        self.assertEquals(1, nrows)
        row = s.get_last(1)[0]
        self.assertEquals(row['Count'], 100)

        self.tracker['Statistic'] = 50
        nrows = s.get_number_of_rows()
        self.assertEquals(2, nrows)
        row = s.get_last(1)[0]
        self.assertEquals(row['Count'], 50)
