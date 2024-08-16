#!/usr/bin/python3

import requests
import json
import yaml
import argparse
import re
from getpass import getpass
from UliPlot.XLSX import auto_adjust_xlsx_column_width
requests.urllib3.disable_warnings()
from prettytable import PrettyTable


# Argument definitions
parser = argparse.ArgumentParser(description='Script to search interface description. *** Required ACI 5.2 or above ***')
parser.add_argument('-d', '--description', type=str, help='String to search. You can use pipe "|" to search more strings.', required=True)
args = parser.parse_args()


# Function to ask password
def interactive_pwd():
    global apic_pwd
    if apic_pwd == "" or apic_pwd == None:
          apic_pwd = getpass("Insert APIC password for user " + apic_user +": ")
    else:
          pass
    

# Function to convert yaml to json
def yaml_to_json(file):
    with open(file, "r") as stream:
        try:
            parsed_yaml=yaml.safe_load(stream)
            return parsed_yaml
        except yaml.YAMLError as exc:
            print(exc)
    pass


# Import APIC vars
apic_vars = yaml_to_json("apic.yaml")


# APIC
apic_ip = apic_vars['apic_ip']
apic_user = apic_vars['apic_user']
apic_pwd = apic_vars['apic_pwd']
BASE_URL = 'https://' + apic_ip + '/api'


# Get APIC Token
def get_apic_token(url, apic_user, apic_pwd):
	login_url = f'{url}/aaaLogin.json'
	s = requests.Session()
	payload = {
		"aaaUser" : {
			"attributes" : {
				"name" : apic_user,
				"pwd" : apic_pwd
			}
		}
	}
	resp = s.post(login_url, json=payload, verify=False)
	resp_json = resp.json()
	token = resp_json['imdata'][0]['aaaLogin']['attributes']['token']
	cookie = {'APIC-cookie':token}
	return cookie

########################

# Function to query description
def aci_query(url, description, cookie):
    r_get = requests.get(url + '/node/class/infraPortSummary.json?query-target-filter=and(wcard(infraPortSummary.description,"' + description + '"))&order-by=infraPortSummary.description|desc', cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    #get_json = [i['l1PhysIf']['attributes'] for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    log_file = open("output.log", "w")
    log_file.write(formatted_str)
    log_file.write("\n")
    return get_json


# Function to extract data
def extract_data(imdata):
    dict = {}
    list_of_dict = []
    for i in imdata:
        dict['POD']=(i['infraPortSummary']['attributes']['pod'])
        dict['NODE']=(i['infraPortSummary']['attributes']['node'])
        dict['INTERFACE']=re.findall('eth\S+(?=])', (i['infraPortSummary']['attributes']['portDn']))[0]
        dict['SHUTDOWN']=(i['infraPortSummary']['attributes']['shutdown'])
        dict['PORT MODE']=(i['infraPortSummary']['attributes']['mode'])
        dict['POLICY GROUP']=re.findall('(?<=accbundle-|ccportgrp-)\S+', (i['infraPortSummary']['attributes']['assocGrp']))[0]
        dict['DESCRIPTION']=(i['infraPortSummary']['attributes']['description'])
        list_of_dict.append(dict.copy())
    return list_of_dict


def listDict_to_table(listDict):
    table = PrettyTable()
    table.field_names = ['POD','NODE','INTERFACE','ADMIN SHUTDOWN','PORT MODE','POLICY GROUP','DESCRIPTION']
    for dict in listDict:
        table.add_row(dict.values())
    return table


########################

#check_property_filter()
interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)
query_response = aci_query(BASE_URL, args.description, cookie)
data_extract = extract_data(query_response)
#print(data_extract)
outputTable = listDict_to_table(data_extract)
print(outputTable)
