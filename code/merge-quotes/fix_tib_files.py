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
    rename_tab = ""
    known_textnames = []
    with gzip.open(filename,'rt') as f:
        segments, quotes = json.load(f)
        for segment in segments:
            segment['segnr'] = replace_string(segment['segnr'])
        for quote in quotes:
            quote['id'] = replace_string(quote['id'])
            new_parsegnr = []
            for par_segnr in quote['par_segnr']:
                new_parsegnr.append(replace_string(par_segnr))
            # print(quote['par_segnr'])
            # print("NEW PARSEG",new_parsegnr)
            quote['par_segnr'] = new_parsegnr
            new_rootsegnr = []
            for root_segnr in quote['root_segnr']:
                new_rootsegnr.append(replace_string(root_segnr))
            quote['root_segnr'] = new_rootsegnr
        print(replace_string(filename)[:-8])
        with open(replace_string(filename)[:-8] +".json", 'w') as outfile:        
            json.dump([segments,quotes], outfile,indent=4,ensure_ascii=False)


process_file(sys.argv[1])

#process_file("/mnt/code/buddhanexus/json/tib/K12acip-k_lha_sa-099-006.json.gz")

