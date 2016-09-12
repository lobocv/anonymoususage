from . import AnonymousUsageTests
import random


class SequenceTests(AnonymousUsageTests):

    def test_set_follow_check_points(self):
        checkpoints = ['A', 'B', 'C', 'D']
        self.assertEqual(self.tracker['Sequence'].checkpoint, None)
        self.assertItemsEqual(self.tracker['Sequence'].get_checkpoints(), checkpoints)

        self.assertEqual(self.tracker['Sequence'].get_count(), 0)

        for ii, cp in enumerate(checkpoints):
            self.tracker['Sequence'] = cp
            self.assertEqual(self.tracker['Sequence'].checkpoint, cp)

            if ii == len(checkpoints)-1:
                self.assertEqual(self.tracker['Sequence'].get_count(), 1)
            else:
                self.assertEqual(self.tracker['Sequence'].get_count(), 0)

    def test_random_checkpoint_order(self):

        checkpoints = ['A', 'B', 'C', 'D']
        self.assertEqual(self.tracker['Sequence'].checkpoint, None)
        self.assertItemsEqual(self.tracker['Sequence'].get_checkpoints(), checkpoints)

        count = self.tracker['Sequence'].get_count()
        self.assertEqual(count, 0)

        cp_path = [random.choice(checkpoints) for ii in xrange(1000)]

        for ii, cp in enumerate(cp_path):
            self.tracker['Sequence'] = cp
            if cp_path[ii-4: ii] == checkpoints:
                count += 1
            self.assertEqual(self.tracker['Sequence'].checkpoint, cp)

        self.assertEqual(self.tracker['Sequence'].get_count(), count)

    def test_advance_to_checkpoint(self):

        checkpoints = ['A', 'B', 'C', 'D']
        self.assertEqual(self.tracker['Sequence'].checkpoint, None)

        count = 0
        for i in xrange(10):
            advance_to = random.choice(checkpoints)

            self.tracker['Sequence'].advance_to_checkpoint(advance_to)

            for cp in checkpoints[checkpoints.index(advance_to)+1:]:
                self.tracker['Sequence'] = cp
            count += 1

            self.assertEqual(self.tracker['Sequence'].get_count(), count)

    def test_clear_checkpoints(self):
        checkpoints = ['A', 'B', 'C', 'D']
        self.assertEqual(self.tracker['Sequence'].checkpoint, None)

        for i in xrange(10):
            self.tracker['Sequence'] = random.choice(checkpoints)
            self.assertGreater(len(self.tracker['Sequence'].sequence), 0)
            self.tracker['Sequence'].clear_checkpoints()
            self.assertEqual(self.tracker['Sequence'].get_count(), 0)

    def test_remove_last_checkpoint(self):
        checkpoints = ['A', 'B', 'C', 'D']
        self.assertEqual(self.tracker['Sequence'].checkpoint, None)

        for i in xrange(10):
            self.tracker['Sequence'] = random.choice(checkpoints)
            self.assertGreater(len(self.tracker['Sequence'].sequence), 0)
            self.tracker['Sequence'].remove_checkpoint()
            self.assertEqual(self.tracker['Sequence'].get_count(), 0)
