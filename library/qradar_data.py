#!/usr/bin/python
# -*- coding: utf-8 -*-

ANSIBLE_METADATA = {
    'metadata_version': '0.3',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = r'''
---
module: qradar_data
short_description: Add / Remove refernce data from QRadar
description:
- This module can be used to add / remove refernce data from qradar
author:
- Chris Schulz (@schulcp)
notes:
- tested on QRadar 7.3.1
requirements:
- python >= 2.7
options:
  console_ip:
    description:
    - hostname or ip to add the data.
    required: yes
  console_user:
    description:
    - qradar username.
  console_password:
    description:
    - qradar console password.
    - required with console_user
  token:
    description:
    - qradar api token
    - token or usser must be included
  ref_col_type:
    description:
    - qradar refernce data to be updated
    - 'SET','MAP','TABLE'
  ref_data_type:
    description:
    - data set type
    - 'IP','ALN','ALNIC','PORT'
  state:
    description:
    - present / abasent 
    - If set to C(absent), then remove the data if data is present.
    - If set to C(present), then add the data if data is absent.
    default: present
'''

EXAMPLES = r'''
environment:
  console_ip: "192.168.56.102"
  token: "282d5950-ca6a-4cba-9015-19bccd9b784e"
tasks:
  - name: add refernce map
    qradar_data:
       ref_name: 'testtable'
       ref_col_type: 'TABLE'
       ref_data_type: 'ALN'
       timetolive: "1 month"
       ref_data:
           Flast:
              name: "First Last"
              dept: "Some departmet"
              mgr: "First Last"
           first.last: 
              name: "First Last" 
              dept: "Some departmet"
              mgr: "First Last"
              email: "Flast@somedepartment.com"
'''

RETURN = r'''
result:
    description: metadata about api call
    type: json
'''

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from urllib import urlencode, quote
from ast import literal_eval
from os import environ
import requests
import time
import json
import q

class QRadarData:
    def __init__(self, module):
        self.module = module
        self.ref_name = module.params['ref_name'].lower()
        self.console_ip = module.params['console_ip']
        self.console_user = module.params['console_user']
        self.console_password = module.params['console_password']
        self.token = module.params['token']
        self.timetolive = module.params['timetolive']
        self.state = module.params['state'].lower()
        self.ref_data_type = module.params['ref_data_type']
        self.ref_col_type = module.params['ref_col_type'].lower()
        self.ref_data = literal_eval(module.params['ref_data'])  # ref_data is str, convert to dict
        self.ref_result = {}

        # if playbook vars not set check for env vars or exit
        if not self.console_user:
           if environ.get('console_user'):
              self.console_user = environ['console_user']
        if not self.console_ip:
           if environ.get('console_ip'):
              self.console_ip = environ['console_ip']
        if not self.console_password:
           if environ.get('console_password'):
              self.console_password = environ['console_password']
        if not self.token:
           if environ.get('token'):
              self.token = environ['token']

        if not self.token and not self.console_password:
           module.exit_json(changed=False, meta={ "message" : "missing credentials" })

        self.base_url = "https://" + self.console_ip + "/api/reference_data/" + self.ref_col_type + 's' 
        # set aip header based on credentuals
        if self.token:
           self.header = {
             'Version': "9.1",
             'Content-Type': "application/json",
             'Allow-Hidden': "true",
             'SEC': self.token, 
             }
        else:
           self.header = {
             'Version': "9.1",
             'Content-Type': "application/json",
             'Allow-Hidden': "true" 
             }

    def process_state(self):
        data_states = {
            'absent': {
                'present': self.remove_data, # remove data
                'absent': self.exit_unchanged,
            },
            'present': {
                'absent': self.add_data, # add new data
                #'present': self.update_data, # update existing data
                'present': self.update_bulk, # update existing data
            }
        }

        try:
            data_states[self.state][self.check_data_state()]()
            # --if state=present and date exists/present call self.exit_unchanged()
        except Exception as e:
            self.module.fail_json(msg=to_native(e))

    def exit_unchanged(self):
        self.module.exit_json(changed=False)

    def add_data(self):
        action = 'POST'

        parameters = {
            'element_type': self.ref_data_type.upper(),
            'name': self.ref_name,
            'time_to_live': self.timetolive,
        }

        try:
          r = requests.request(action, self.base_url, auth=(self.console_user, self.console_password), verify=False, headers=self.header, params=parameters)
        except Exception as e:
            self.module.exit_json(changed=False, meta={'message': 'could not call api'})

        if r.status_code == 201:
           if self.ref_data:
            self.update_bulk() 
           else:
            self.module.exit_json(changed=True, meta=r.json())
        else: 
            self.module.exit_json(changed=False, meta={'message': 'could not add reference data'})
    #<-- end add

    def update_bulk(self):
        action = 'POST'
        url = self.base_url + '/bulk_load/' + quote(self.ref_name)

        params = self.ref_data
        try:
          r = requests.request(action, url, auth=(self.console_user, self.console_password), verify=False, headers=self.header, json=params)
        except Exception as e:
          self.module.exit_json(changed=False, meta={'message': 'could not call api'})
        if r.status_code == 200:
          self.module.exit_json(changed=True, meta=r.json())
        else: 
            self.module.exit_json(changed=False, meta={'message': 'could not add reference data'})
    #<-- end update
    
# <-- moving all update to bulk add - supports complex data types / yaml 
    def update_data(self):
        action = 'POST'
        url = self.base_url + '/' + quote(self.ref_name)

        try:
          r = requests.request(action, url, auth=(self.console_user, self.console_password), verify=False, headers=self.header, params=self.ref_data)
        except Exception as e:
          self.module.exit_json(changed=False, meta={'message': 'could not call api'})
        if r.status_code == 200:
          self.module.exit_json(changed=True, meta=r.json())
        else: 
          self.module.exit_json(changed=False, meta={'message': 'could not add reference data'})
    #<-- end update

    def remove_data(self):
        action = 'DELETE'
        return_code = 'unknown'
        if self.ref_data:
          for key in self.ref_data:
            if self.ref_col_type.lower() == 'set' :
                url = self.base_url + '/' + quote(self.ref_name) + '/' + quote(self.ref_data[key])
                params=None
            if self.ref_col_type.lower() == 'map' :
                url = self.base_url + '/' + quote(self.ref_name) + '/' + quote(key) 
                params={ 'value': self.ref_data[key] }
            if self.ref_col_type.lower() == 'table' :
                for inner_key in self.ref_data[key]:
                    url = self.base_url + '/' + quote(self.ref_name) + '/' + quote(key) + '/' + quote(inner_key) 
                    params={ 'value': self.ref_data[key][inner_key] }
            try:
              r = requests.request(action, url, auth=(self.console_user, self.console_password), verify=False, headers=self.header, params=params)
            except Exception as e:
              self.module.exit_json(changed=False, meta={'message': 'could not call api'})
            if r.status_code == 202 or r.status_code == 200:
               return_code = r.status_code
            else: 
               self.module.exit_json(changed=False, meta={'message': 'could not remove reference data'})
          self.module.exit_json(changed=True, meta={'rc': return_code})

        else:
          url = self.base_url + '/' + quote(self.ref_name)
          try:
            r = requests.request(action, url, auth=(self.console_user, self.console_password), verify=False, headers=self.header, params=self.ref_data)
          except Exception as e:
            self.module.exit_json(changed=False, meta={'message': 'could not call api'})
          if r.status_code == 202:
            self.module.exit_json(changed=True, meta=r.json())
          else: 
            self.module.exit_json(changed=False, meta={'message': 'could not remove reference data'})
    #<-- end remove

    def check_data_state(self):
        action = 'GET'
        try:
          r = requests.request(action, self.base_url, auth=(self.console_user, self.console_password), verify=False, headers=self.header)
        except Exception as e:
          return 'absent'
        if r.status_code == 200:
          for item in r.json():
            if item.get('name').lower() == self.ref_name: # found ref set from playbook
               self.ref_result = item
               return 'present'
        return 'absent'
    #<-- end state
#<-- end class

def main():
    fields = dict(
       console_ip=dict(type='str', required=False),
       console_user=dict(type='str', required=False),
       console_password=dict(type='str', no_log=True, required=False),
       token=dict(type='str', required=False),
       state=dict(type='str', required=False, default='present', choices=['present','absent']),
       ref_data_type=dict(type='str', required=False, choices=['IP','ALN','ALNIC','PORT']),
       ref_col_type=dict(type='str', required=True, choices=['SET','MAP','TABLE']),
       ref_name=dict(type='str', required=True),
       timetolive=dict(type='str', required=False, default=''),
       ref_data = dict(required=False, default={})
       )

    module = AnsibleModule(
        argument_spec=fields,
    )

    qradar_data = QRadarData(module)
    time.sleep(0.5)
    qradar_data.process_state()


if __name__ == '__main__':
    main()
