#!/usr/bin/python3

import requests
import json
import yaml
import argparse
import re
import sys
from getpass import getpass
from UliPlot.XLSX import auto_adjust_xlsx_column_width
requests.urllib3.disable_warnings()
from prettytable import PrettyTable


#parser = argparse.ArgumentParser(prog='PROG')
#group = parser.add_mutually_exclusive_group(required=True)
#group.add_argument('-f', '--foo')
#group.add_argument('-b', '--bar')
#args = parser.parse_args()



# Argument definitions
parser = argparse.ArgumentParser(description='Script to search interface description. *** Required ACI 5.2 or above ***')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('-d', '--description', type=str, help='String to search.')
group.add_argument('-l', '--list', type=str, help='List of strings to search.')
args = parser.parse_args()

print(args.list)
