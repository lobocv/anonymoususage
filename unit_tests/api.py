__author__ = 'Calvin'

import unittest
import json
import time
import requests

host = 'http://127.0.0.1:8080'
STATISTIC_URL = host + "/statistics"
STATE_URL = host + "/states"
TIMER_URL = host + "/timers"
SEQUENCE_URL = host + "/sequences"

"""
All tests are assuming the event dispatcher instance is stored in self.dispatcher or self.dispatcher2
And all properties are named p1 or p2.
"""

# Create some trackables
r = requests.post(STATISTIC_URL, data={'name': 'age', 'description': 'my age'})
assert(r.status_code == 200)
r = requests.post(STATE_URL, data={'name': 'hair_colour', 'value': 'black', 'description': 'my hair colour'})
assert(r.status_code == 200)
r = requests.post(TIMER_URL, data={'name': 'my_timer', 'description': 'timer for test'})
assert(r.status_code == 200)
r = requests.post(SEQUENCE_URL,data={'name': 'my_sequence', 'checkpoints': 'a,b,c,d', 'description': 'example sequence'})
assert(r.status_code == 200)



class API_TEST(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(API_TEST, self).__init__(*args, **kwargs)

    def test_statistic_get(self):
        r = requests.get(STATISTIC_URL + '/age')
        self.assertEqual(r.status_code, 200)
        r = requests.get(STATISTIC_URL + '/non-existent-trackable')
        self.assertEqual(r.status_code, 404)

    def test_statistic_set(self):
        age = 25
        incr = 2
        decr = 1
        r = requests.put(STATISTIC_URL + '/age/set/%d' % age)
        self.assertEqual(r.status_code, 200)

        r = requests.get(STATISTIC_URL + '/age')
        self.assertEqual(json.loads(r.content)['count'], age)
        self.assertEqual(r.status_code, 200)

        r = requests.put(STATISTIC_URL + '/age/increment/%d' % incr)
        self.assertEqual(r.status_code, 200)

        r = requests.get(STATISTIC_URL + '/age')
        self.assertEqual(json.loads(r.content)['count'], age + incr)
        self.assertEqual(r.status_code, 200)

        r = requests.put(STATISTIC_URL + '/age/decrement/%d' % decr)
        self.assertEqual(r.status_code, 200)

        r = requests.get(STATISTIC_URL + '/age')
        self.assertEqual(json.loads(r.content)['count'], age + incr - decr)
        self.assertEqual(r.status_code, 200)

    def test_state_get(self):
        r = requests.get(STATE_URL + '/hair_colour')
        self.assertEqual(r.status_code, 200)
        r = requests.get(STATE_URL+ '/non-existent-trackable')
        self.assertEqual(r.status_code, 404)

    def test_state_set(self):
        r = requests.put(STATE_URL + '/hair_colour/set/None')
        self.assertEqual(r.status_code, 200)

        r = requests.get(STATE_URL + '/hair_colour')
        self.assertEqual(json.loads(r.content)['state'], None)
        self.assertEqual(r.status_code, 200)

        r = requests.put(STATE_URL + '/hair_colour/set/black')
        self.assertEqual(r.status_code, 200)

        r = requests.get(STATE_URL + '/hair_colour')
        self.assertEqual(json.loads(r.content)['state'], 'black')
        self.assertEqual(r.status_code, 200)

    def test_timer_get(self):
        r = requests.get(TIMER_URL + '/my_timer')
        self.assertEqual(r.status_code, 200)
        r = requests.get(TIMER_URL + '/non-existent-trackable')
        self.assertEqual(r.status_code, 404)

    def test_timer_set(self):
        r = requests.get(TIMER_URL + '/my_timer')
        self.assertEqual(r.status_code, 200)
        t0 = json.loads(r.content)
        sleeptime = 1
        r = requests.put(TIMER_URL + '/my_timer/start_timer')
        self.assertEqual(r.status_code, 200)

        time.sleep(sleeptime)
        r = requests.put(TIMER_URL + '/my_timer/pause_timer')
        self.assertEqual(r.status_code, 200)

        time.sleep(sleeptime)
        r = requests.put(TIMER_URL + '/my_timer/resume_timer')
        self.assertEqual(r.status_code, 200)

        time.sleep(sleeptime)
        r = requests.put(TIMER_URL + '/my_timer/stop_timer')
        self.assertEqual(r.status_code, 200)

        r = requests.get(TIMER_URL + '/my_timer')
        self.assertEqual(r.status_code, 200)
        t1 = json.loads(r.content)

        self.assertAlmostEqual(t0['total_seconds'] + 2 * sleeptime, t1['total_seconds'], 1)

    def test_sequence_get(self):
        r = requests.get(SEQUENCE_URL + '/my_sequence')
        self.assertEqual(r.status_code, 200)
        r = requests.get(SEQUENCE_URL + '/non-existent-trackable')
        self.assertEqual(r.status_code, 404)

    def test_sequence_set(self):
        r = requests.get(SEQUENCE_URL + '/my_sequence')
        self.assertEqual(r.status_code, 200)

        r = requests.get(SEQUENCE_URL + '/non-existent-trackable')
        self.assertEqual(r.status_code, 404)

        checkpoints = ['a', 'b', 'c', 'd']
        for cp in checkpoints:
            cp_passed = checkpoints[:checkpoints.index(cp)+1]
            r = requests.put(SEQUENCE_URL + '/my_sequence/set/%s' % cp)
            self.assertEqual(r.status_code, 200)
            r = requests.get(SEQUENCE_URL + '/my_sequence')
            self.assertEqual(json.loads(r.content)['checkpoint'], cp if cp != 'd' else None)
            self.assertListEqual(json.loads(r.content)['sequence'], cp_passed if cp != 'd' else [])
            self.assertEqual(r.status_code, 200)

        r = requests.put(SEQUENCE_URL + '/my_sequence/advance_to_checkpoint/c')
        self.assertEqual(r.status_code, 200)
        r = requests.get(SEQUENCE_URL + '/my_sequence')
        self.assertEqual(json.loads(r.content)['checkpoint'], 'c')

        r = requests.put(SEQUENCE_URL + '/my_sequence/set/not-a-checkpoint')
        self.assertEqual(r.status_code, 404)

        r = requests.put(SEQUENCE_URL + '/my_sequence/remove_checkpoint')
        r = requests.get(SEQUENCE_URL + '/my_sequence')
        self.assertEqual(json.loads(r.content)['checkpoint'], 'b')

        r = requests.put(SEQUENCE_URL + '/my_sequence/clear_checkpoints')
        self.assertEqual(r.status_code, 200)
        r = requests.get(SEQUENCE_URL + '/my_sequence')
        self.assertEqual(len(json.loads(r.content)['sequence']), 0)
        self.assertEqual(json.loads(r.content)['checkpoint'], None)


if __name__ == '__main__':
    unittest.main()
