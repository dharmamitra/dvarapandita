import sys
import re
import gzip
import pprint
import numpy as np
import os
import string
import json
import multiprocessing
from Levenshtein import distance as distance2
import numpy as np
from tqdm import tqdm as tqdm


folder = '/mnt/output_parallel/sanskrit/json/'        

filename = '/mnt/output_parallel/sanskrit/json/T06sthtvbhu.json'
r = open('/mnt/code/merge-quotes/gretil-replaces.tab','r')
replaces_dictionary = {}
for line in r:
     headword = line.split('\t')[0]
     entry = line.split('\t')[1]
     replaces_dictionary[headword] = entry

def replace_segmentnr(segmentnr):
    segment, number = segmentnr.split(':')
    new_segmentnr = segment
    if segment in replaces_dictionary:
        new_segment  = replaces_dictionary[segment].strip() + ':' + number
        return new_segment
    else:
        return segmentnr
        
def process_file(filename):
    with open(filename,'rt') as f:
        global segments
        global quotes
        segments,quotes = json.load(f)
        for segment in segments:            
            segmentnr = segment['segnr']
            segment['segnr'] = replace_segmentnr(segmentnr)
        for quote in quotes:
            new_par_segnr = []
            for par_segnr in quote['par_segnr']:
                new_par_segnr.append(replace_segmentnr(par_segnr))
            quote['par_segnr'] = new_par_segnr
            new_par_segnr = []
            for root_segnr in quote['root_segnr']:
                new_par_segnr.append(replace_segmentnr(root_segnr))
            quote['root_segnr'] = new_par_segnr                                              
        print("DONE",filename)
        with open(filename[:-5] +"_cleaned.json", 'w') as outfile:        
            json.dump([segments,quotes], outfile,indent=4,ensure_ascii=False)


            
process_file(filename)

def process_all(folder):
    files = []
    for file in tqdm(os.listdir(folder)):
        filename = os.fsdecode(file)
        files.append(folder+filename)
    pool = multiprocessing.Pool(processes=80,maxtasksperchild=1)
    pool.map(process_file, files)
    pool.close()
    
process_all(folder)

