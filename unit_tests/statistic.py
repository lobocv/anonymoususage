from . import AnonymousUsageTests


class StatisticTests(AnonymousUsageTests):

    def test_increment(self):
        s = self.tracker['Statistic']
        s += 1
        s += 1
        s += 1
        nrows = s.get_number_of_rows()
        self.assertEquals(3, nrows)
        self.assertEquals(s.count, 3)
        s += 10
        self.assertEquals(s.count, 13)

    def test_decrement(self):
        s = self.tracker['Statistic']
        s -= 1
        s -= 1
        s -= 1
        nrows = s.get_number_of_rows()
        self.assertEquals(3, nrows)
        self.assertEquals(s.count, -3)

    def test_set_value(self):
        s =self.tracker['Statistic']
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
