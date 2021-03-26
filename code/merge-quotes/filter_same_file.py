import multiprocessing
import sys
import re
import gzip
from tqdm import tqdm as tqdm
import json
import os
filename = sys.argv[1]

def process_file(filename):
    with gzip.open(filename,'rt') as f:
        global segments
        global quotes
        segments,quotes = json.load(f)
        new_quotes = []
        main_filename = segments[0]['segnr'].split(':')[0]
        for quote in tqdm(quotes):
             par_segnr = quote['par_segnr'][0]
             current_filename = par_segnr.split(':')[0]             
             if current_filename != main_filename:
                  new_quotes.append(quote)
        with open(filename[:-5] +"_fixed.json", 'w') as outfile:        
            json.dump([segments,new_quotes], outfile,indent=4,ensure_ascii=False)
    

def process_all(folder):
     files = []
     for file in tqdm(os.listdir(folder)):
         if not os.path.isfile(folder + file[:-5] +"_fixed.json") and ".gz" in file:
             filename = os.fsdecode(file)          
             files.append(folder+filename)
     pool = multiprocessing.Pool(processes=12,maxtasksperchild=1)
     pool.map(process_file, files)
     pool.close()
    
process_all("/mnt/code/buddhanexus/json/tib/")

