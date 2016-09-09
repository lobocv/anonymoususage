from . import AnonymousUsageTests


class StateTests(AnonymousUsageTests):

    trackable = 'State'

    def _assign_a_value(self):
        self.tracker['State'] = 'SomeValue'
        return 'SomeValue'

    def test_set_value(self):
        s = self.tracker['State']
        self.tracker['State'] = 'SomeState'
        nrows = s.get_number_of_rows()
        self.assertEquals(1, nrows)
        self.tracker['State'] = 'SomeState'
        self.tracker['State'] = 'SomeState'
        self.tracker['State'] = 'SomeState'

        row = s.get_last()[0]
        self.assertEquals(row['State'], 'SomeState')

        nrows = s.get_number_of_rows()
        self.assertEquals(1, nrows)

        self.tracker['State'] = 'SomeOtherState'
        nrows = s.get_number_of_rows()
        self.assertEquals(2, nrows)
        row = s.get_last()[0]
        self.assertEquals(row['State'], 'SomeOtherState')

