from quotes_constants import *
from postprocess_quotes import postprocess_quotes_tib
import re
import sys
import gzip
import json

filename = sys.argv[1]

r = open("/mnt/code/calculate-quotes/data/rename_tibetan_kangyur.tab",'r')
replaces_dictionary = {}
for line in r:
    if not "T" in line or "a" in line or "b" or line or "c" in line:
        rows = ( line.split('\t'))
        replaces_dictionary[rows[0].strip('\n')] = rows[1].strip('\n')

     
# def multireplace(string, replacements):
#     """
#     Given a string and a replacement map, it returns the replaced string.

#     :param str string: string to execute replacements on
#     :param dict replacements: replacement dictionary {value to find: value to replace}
#     :rtype: str

#     """
#     # Place longer ones first to keep shorter substrings from matching
#     # where the longer ones should take place
#     # For instance given the replacements {'ab': 'AB', 'abc': 'ABC'} against 
#     # the string 'hey abc', it should produce 'hey ABC' and not 'hey ABc'
#     substrs = sorted(replacements, key=len, reverse=True)

#     # Create a big OR regex that matches any of the substrings to replace
#     regexp = re.compile('|'.join(map(re.escape, substrs)))

#     # For each match, look up the new string in the replacements
#     return regexp.sub(lambda match: replacements[match.group(0)], string)

# def replace_string(string):
#     return multireplace(string,replaces_dictionary)


def replace_string(string):
    for entry in replaces_dictionary.keys():
        new_string = string.replace(entry,replaces_dictionary[entry])
        if new_string != string:
            return new_string
    return string.replace("E","")




def process_file(filename):
    with open(filename,'rt') as f:
        entries = json.load(f)
        for entry in entries:
            new_files = []
            for file in entry['files']:
                new_files.append(replace_string(file))
            entry['files'] = new_files
        
        with open(replace_string(filename)[:-5] +"_fixed.json", 'w') as outfile:        
            json.dump(entries, outfile,indent=4,ensure_ascii=False)


process_file("/mnt/code/buddhanexus/data/tib-categories.json")

#process_file("/mnt/code/buddhanexus/json/tib/K12acip-k_lha_sa-099-006.json.gz")

