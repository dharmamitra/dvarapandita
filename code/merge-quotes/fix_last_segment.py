from quotes_constants import *
from get_segment_dic import get_segment_dic,extend_dic_by_tsv
import json
import gzip
import re
import os
import multiprocessing
from tqdm import tqdm as tqdm
tsv_path = ''

lang = "tib"

json_path = "/mnt/output/tib/json/"

if lang=='skt':
    segment_dic_path = SANSKRIT_SEGMENT_DICT_PATH
if lang=='pli':
    segment_dic_path = PALI_SEGMENT_DICT_PATH
if lang=='tib':
    segment_dic_path = TIBETAN_SEGMENT_DICT_PATH
if lang=='chn':

    segment_dic_path = CHINESE_SEGMENT_DICT_PATH

# segment_dic,segment_keys,segment_key_numbers,natural_keys = get_segment_dic(segment_dic_path,tsv_path)


# last_filename = ''
# current_count = 0
# files_segment_dic = {}
# current_segments = []
# for entry in tqdm(segment_dic.keys()):
#     current_filename = entry.split(':')[0]
#     if current_filename != last_filename:
#         files_segment_dic[last_filename] = current_segments
#         current_segments = []
#         current_count = 0
#         last_filename = current_filename
#     current_segments.append({
#         "segnr":entry,
#         "segtext":segment_dic[entry],
#         "position":current_count,
#         "lang": lang
#         })
#     current_count += 1
        
        
    
def process_file(filename):
    list_of_filenames = []
    filename_shortened = filename.replace(".json.gz","").strip()
    filename_shortened = re.sub(".*/","",filename_shortened)
    if filename_shortened in files_segment_dic:
        print("PROCESSING",filename_shortened)
        quotes = []
        current_segments = files_segment_dic[filename_shortened]
        with gzip.open(filename,'rt') as f:
            segments,quotes = json.load(f)
        with open(filename.replace(".json.gz","_fixed.json"), 'w') as outfile:        
            json.dump([current_segments,quotes], outfile,indent=4,ensure_ascii=False)
            #os.system("pigz " + filename_shortened +".json")

def process_all(tab_folder):
    filenames = []
    for file in os.listdir(tab_folder):
        filename = os.fsdecode(file)
        if filename.endswith('.json.gz'):
            #process_file(tab_folder + "/" + filename)
            filenames.append(tab_folder+ "/" + filename)
    pool = multiprocessing.Pool(processes=12)
    quote_results = pool.map(process_file, filenames)
    pool.close()
#process_all(sys.argv[1])

process_all(json_path)                
