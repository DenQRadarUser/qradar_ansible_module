#!/usr/bin/python
from pprint import pprint
from urllib import urlencode, quote
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json
import requests

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

console_user='admin'
console_password='S0meP@ssword'
col='tables'
#col='sets'
#col='maps'
action = 'get'
# action = 'delete'

url = 'https://192.168.56.102/api/reference_data/' + col
headers = {
    'Version': "9.1",
    'Accept': "application/json",
    'Content-Type': "application/json",
    'Allow-Hidden': "true",
     }

r = requests.get(url, auth=(console_user,console_password), headers=headers, verify=False)
pprint(r.json())

for i in r.json():
   url = 'https://192.168.56.102/api/reference_data/' + col + '/' + quote(i['name'])
   r = requests.request(action, url, auth=(console_user,console_password), headers=headers, verify=False)

pprint(r.json())

