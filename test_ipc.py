import requests

host = 'http://127.0.0.1:8080'
STATISTIC_URL = host + "/statistics"
STATE_URL = host + "/states"


# Statistic tests
r = requests.post(STATISTIC_URL, data={'name': 'age', 'description': 'my age'})
print r.content

r = requests.get(STATISTIC_URL + '/age')
print r.content

r = requests.get(STATISTIC_URL + '/non-existent-trackable')
print r.content

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
print r.content

r = requests.put(STATE_URL + '/hair_colour/set/None')
print r.content

r = requests.put(STATE_URL + '/hair_colour/set/brown')
print r.content

print 'done'