import requests

host = 'http://127.0.0.1:8080'
host_statistics = host + "/statistics"

r = requests.post(host_statistics, data={'name': 'age', 'description': 'my age'})
print r.content

r = requests.get(host_statistics + '/age')
print r.content


r = requests.get(host_statistics + '/non-existent-trackable')
print r.content

r = requests.put(host_statistics + '/age/set/25.00452')
print r.content



print 'done'