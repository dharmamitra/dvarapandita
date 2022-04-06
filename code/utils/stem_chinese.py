import os
import re
import json
import pandas as pd
from utils.constants import PUNC

r = open("../data/chinese_replaces.txt",'r')


replaces_dictionary = {}

for line in r:
     rows = line.split('\t')
     rows[1] = rows[1].strip()
     if len(rows[1]) > 3:
         replaces_dictionary[rows[0].strip('\n')] = rows[1].strip('\n')
    

substrs = sorted(replaces_dictionary, key=len, reverse=True)
regexp = re.compile('|'.join(map(re.escape, substrs)))

def remove_punc(string):
    return re.sub(r"[%s]+" %PUNC.replace(" ",""), "", string)

def replace_brackets(string):
    z = re.search('(\[.+\])',string)
    if z:
        target = z.groups()[0]
        replace = target.replace(' ','')
        return string.replace(target,replace)
    else:
        return string


def multireplace(string):
    return regexp.sub(lambda match: replaces_dictionary[match.group(0)], string)

def stem_chinese(cstring):
    replaced_text = re.sub(r'(.)',r'\1 ',cstring)
    replaced_text = multireplace(replaced_text)
    replaced_text = remove_punc(replaced_text)
    replaced_text = replace_brackets(replaced_text)
    replaced_text = re.sub(r'[^\w\s\[\]]','',replaced_text)
    return replaced_text

def stem_chinese_file(data):
    path,lang = data
    print("NOW PROCESSING",path)
    cfile = json.load(open(path,'r'))
    
    path_short = os.path.splitext(path)[0]
    filenames = []
    line_numbers = []
    original_lines = []
    cleaned_lines = []
    for segmentnr in cfile:
        filename, line_number = segmentnr.split(":")
        original_line = cfile[segmentnr].replace('\n','')
        cleaned_line = stem_chinese(original_line)
        original_lines.append(original_line)
        cleaned_lines.append(cleaned_line)
        line_numbers.append(line_number)
        filenames.append(filename)
    text_df = pd.DataFrame({"filename": filenames, "line_number": line_numbers, 'original': original_lines, "stemmed": cleaned_lines})
    text_df['segmentnr'] = text_df["filename"] + ":" + text_df['line_number']
    text_df.to_csv(path_short + ".tsv", sep="\t", index=False, columns=["segmentnr", "original", "stemmed"])
