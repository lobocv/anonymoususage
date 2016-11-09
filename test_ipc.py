import time
import requests

host = 'http://127.0.0.1:8080'
STATISTIC_URL = host + "/statistics"
STATE_URL = host + "/states"
TIMER_URL = host + "/timers"


# Statistic tests
r = requests.post(STATISTIC_URL, data={'name': 'age', 'description': 'my age'})
print r.content

r = requests.get(STATISTIC_URL + '/age')
print r.content

r = requests.get(STATISTIC_URL + '/non-existent-trackable')
assert(r.status_code == 404)

r = requests.put(STATISTIC_URL + '/age/set/25.00452')
print r.content

r = requests.put(STATISTIC_URL + '/age/increment/2')
print r.content

r = requests.put(STATISTIC_URL + '/age/decrement')
print r.content

# State tests

r = requests.post(STATE_URL, data={'name': 'hair_colour', 'value': 'black', 'description': 'my hair colour'})
print r.content

r = requests.get(STATE_URL + '/hair_colour')
print r.content

r = requests.get(STATE_URL + '/non-existent-trackable')
assert(r.status_code == 404)

r = requests.put(STATE_URL + '/hair_colour/set/None')
print r.content

r = requests.put(STATE_URL + '/hair_colour/set/brown')
print r.content


# Timer tests
r = requests.post(TIMER_URL, data={'name': 'my_timer', 'description': 'timer for test'})
print r.content

r = requests.get(TIMER_URL + '/my_timer')
print r.content

r = requests.get(TIMER_URL + '/non-existent-trackable')
assert(r.status_code == 404)

r = requests.put(TIMER_URL + '/my_timer/start_timer')
print r.content
time.sleep(3)

r = requests.put(TIMER_URL + '/my_timer/pause_timer')
print r.content

time.sleep(2)

r = requests.put(TIMER_URL + '/my_timer/resume_timer')
print r.content


r = requests.put(TIMER_URL + '/my_timer/stop_timer')
print r.content

r = requests.get(TIMER_URL + '/my_timer/total_minutes')
print r.content


print 'done'

