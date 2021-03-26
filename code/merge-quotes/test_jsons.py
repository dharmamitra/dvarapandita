import sys
from tqdm import tqdm as tqdm
import json
import gzip
import os
import multiprocessing

def process_file(filename):
    print(filename)
    with gzip.open(filename,'rt') as f:
        segments,quotes = json.load(f)

def process_all(tab_folder):
    filenames = []
    for file in os.listdir(tab_folder):
        filename = os.fsdecode(file)
        process_file(tab_folder + "/" + filename)

#process_all(sys.argv[1])
process_all("/mnt/output/tib/json")                
# test = gzip.open("/mnt/output/tib/json_unfiltered/K10acip-k_lha_sa-054-004-9.json.gz",'rt')
# segments, quotes = json.load(test)
    
