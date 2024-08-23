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
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-d', '--description', type=str, help='String to search.')
# TODO:
# Usare -l per permettere di inserire una lista di descrizioni così da poterle ciclare
# per risolvere il problema degli static path
group.add_argument('-l', '--list', type=str, help='List of strings to search.')
args = parser.parse_args()


def interactive_pwd():
    '''Function to ask password if not set'''
    global apic_pwd
    if apic_pwd == "" or apic_pwd == None:
          apic_pwd = getpass("Insert APIC password for user " + apic_user +": ")
    else:
          pass
    

def yaml_to_json(file):
    '''Function to convert yaml to json'''
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


def get_apic_token(url, apic_user, apic_pwd):
    ''' Get APIC Token'''
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

def aci_query_infraPortSummary(url, description, cookie):
    '''Function to query interface description'''
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

def aci_query_operStQual(url, pod, node, interface, cookie):
    '''Function to query operStQual'''
    r_get = requests.get(url + '/node/mo/topology/pod-' + pod + '/node-' + node + '/sys/phys-[' + interface + '].json?query-target=children', cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    return get_json

def aci_query_fvRsPathAtt(url, portDn, cookie):
    '''Function to query fvRsPathAtt'''
    r_get = requests.get(url + '/node/class/fvRsPathAtt.json?query-target-filter=and(eq(fvRsPathAtt.tDn,"' + portDn + '"))&order-by=fvRsPathAtt.modTs|desc', cookies=cookie, verify=False)
    get_json = r_get.json()
    get_json = [i for i in get_json['imdata']]
    formatted_str = json.dumps(get_json, indent=4)
    #print(formatted_str)
    return get_json

def extract_data(imdata, imdata2, imdata3):
    '''Function to extract data and combine dictionary'''
    dict = {}
    list_of_dict = []
    for i, ii in zip(imdata, imdata2):
        list_of_epgs = []
        dict['POD']=(i['infraPortSummary']['attributes']['pod'])
        dict['NODE']=(i['infraPortSummary']['attributes']['node'])
        dict['INTERFACE']=re.findall('eth\S+(?=])', (i['infraPortSummary']['attributes']['portDn']))[0]
        dict['SHUTDOWN']='shutdown' if (i['infraPortSummary']['attributes']['shutdown']) == 'yes' else 'up'
        dict['OPER STATUS']=(ii[0]['ethpmPhysIf']['attributes']['operSt'])
        dict['OPER REASON']=(ii[0]['ethpmPhysIf']['attributes']['operStQual'])
        #dict['OPER STATUS']=(ii[0]['ethpmPhysIf']['attributes']['operStQual']) if (ii[0]['ethpmPhysIf']['attributes']['operStQual']) != 'admin-down' else 'down'
        if (i['infraPortSummary']['attributes']['mode']) == 'vpc':
             dict['PORT MODE']='Virtual Port-Channel'
        elif (i['infraPortSummary']['attributes']['mode']) == 'pc':
             dict['PORT MODE']='Port-Channel'
        else:
             dict['PORT MODE']='Individual'
        dict['POLICY GROUP']=re.findall('(?<=accbundle-|ccportgrp-)\S+', (i['infraPortSummary']['attributes']['assocGrp']))[0]
        dict['DESCRIPTION']=(i['infraPortSummary']['attributes']['description'])
        for iii in imdata3:
            if (iii['fvRsPathAtt']['attributes']['mode']) == 'regular':
                list_of_epgs.append(str(re.findall('tn-\S+(?=/rspat)', (iii['fvRsPathAtt']['attributes']['dn']))) + ' -> ' + str('trunk'))
            elif (iii['fvRsPathAtt']['attributes']['mode']) == 'untagged':
                list_of_epgs.append(str(re.findall('tn-\S+(?=/rspat)', (iii['fvRsPathAtt']['attributes']['dn']))) + ' -> ' + str('access'))
            else:
                list_of_epgs.append(str(re.findall('tn-\S+(?=/rspat)', (iii['fvRsPathAtt']['attributes']['dn']))) + ' -> ' + str((iii['fvRsPathAtt']['attributes']['mode'])))
        dict['EPGs']=list_of_epgs
        list_of_dict.append(dict.copy())
    return list_of_dict

def listDict_to_table(listDict):
    '''Function to create table'''
    table = PrettyTable()
    table._max_width = {"EPGs" : 50}
    table.field_names = ['POD','NODE','INTERFACE','ADMIN STATUS','OPER STATUS','OPER REASON','PORT MODE','POLICY GROUP','DESCRIPTION', 'EPGs']
    for dict in listDict:
        table.add_row(dict.values())
    return table

########################

interactive_pwd()
cookie = get_apic_token(BASE_URL, apic_user, apic_pwd)
query_response_infraPortSummary = aci_query_infraPortSummary(BASE_URL, args.description, cookie)

# Stop script if no results
if len(query_response_infraPortSummary) == 0:
    print('\nNo results\n')
    exit()
else:
    pass

# This for loop makes other query to ethpmPhysIf and vRsPathAtt based on interfaces in query_response_infraPortSummary
query_response_operStQual = []
query_response_vRsPathAtt = []
for i in query_response_infraPortSummary:
    query_response_operStQual.append(aci_query_operStQual(BASE_URL, i['infraPortSummary']['attributes']['pod'], i['infraPortSummary']['attributes']['node'], re.findall('eth\S+(?=])', (i['infraPortSummary']['attributes']['portDn']))[0], cookie))
    if i['infraPortSummary']['attributes']['mode'] == 'pc' or i['infraPortSummary']['attributes']['mode'] == 'vpc':
        query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['pcPortDn'], cookie))
    else:
        query_response_vRsPathAtt.append(aci_query_fvRsPathAtt(BASE_URL, i['infraPortSummary']['attributes']['portDn'], cookie))

data_extract = extract_data(query_response_infraPortSummary, query_response_operStQual, query_response_vRsPathAtt[0])
#print(data_extract)
outputTable = listDict_to_table(data_extract)
print(outputTable)
