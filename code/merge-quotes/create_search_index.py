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
#from xliterator import remove_diacritics
global search_index
search_index = []
max_len = 200000

skt_folder = '/home/basti/data/segmented-sanskrit/tsv/'
tib_folder = '/home/basti/data/tibetan/tsv/'
pli_folder = '/home/basti/data/pali/tsv/'
chn_folder = '/home/basti/data/chinese/segmented-chinese/tsv/'

search_index_path_tibetan = "/mnt/code/buddhanexus/json/search_index_tibetan.json"
search_index_path_sanskrit = "/mnt/code/buddhanexus/json/search_index_sanskrit.json"
search_index_path_pali = "/mnt/code/buddhanexus/json/search_index_pali.json"
search_index_path_chn = "/mnt/code/buddhanexus/json/search_index_chn.json"




def get_stems(string):
    result = ""
    words = string.split("#")
    for word in words:
        current_word = word.strip().split(" ")[0]
        result += current_word + " "
    return result.replace("  "," ")

def stem_unsandhied(string):
    if "Case=" in string:
        return get_stems(string)
    else:
        return string
punc = " ！？｡。＂＃＄％＆＇（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏./.|*_"
def remove_punc(string):
    return re.sub(r"[%s]+" %punc, "", string)

    
def process_file(file,lang=''):
    filename = file.replace(".tsv","")
    print(filename)
    f = open(file,'r')
    last_segmentnr = ''
    last_sandhied = ''
    last_unsandhied = ''
    lastlast_sandhied = ''
    lastlast_unsandhied = ''
    lastlast_segmentnr = ''
    search_index = []
    for line in f:
        if len(line.split('\t')) > 1:
            segmentnr,entry_sandhied,entry_unsandhied = line.split('\t')[:3]
            segmentnr = segmentnr.replace("LC","")
            entry_unsandhied = entry_unsandhied.rstrip()
            entry_sandhied = entry_sandhied.rstrip()
            if re.search(r"[DH][0-9][0-9][0-9]", segmentnr):
                #entry_unsandhied = line.split('\t')[:4][-1].rstrip()
                entry_unsandhied = entry_unsandhied.rstrip()
                entry_sandhied += ' '
            elif re.search(r"(_[TX])", segmentnr):
                entry_unsandhied = entry_sandhied.replace('#','')                
                entry_unsandhied = remove_punc(entry_unsandhied)
            else:
                entry_sandhied += ' '
                # if lang == 'pli':
                #     entry_unsandhied = remove_diacritics(entry_sandhied)
                if lang != 'pli':
                    entry_unsandhied = stem_unsandhied(entry_unsandhied)
            if last_segmentnr != '':
                entry_sandhied = entry_sandhied.replace('  ',' ')
                sandhied = lastlast_sandhied + last_sandhied + entry_sandhied
                if not re.search(r"(_[TX])", segmentnr):
                    unsandhied = lastlast_unsandhied + " " + last_unsandhied + " " + entry_unsandhied
                else:
                    unsandhied = lastlast_unsandhied + last_unsandhied + entry_unsandhied
                unsandhied = unsandhied.replace("  "," ")
                split_points_sandhied = {"current":len(lastlast_sandhied),"next":len(lastlast_sandhied) + len(last_sandhied)}
                split_points_unsandhied = {"current":len(lastlast_unsandhied) +1,"next":len(lastlast_unsandhied)+ 1 + len(last_unsandhied)}
                search_index.append({"segment_nr": [lastlast_segmentnr,last_segmentnr,segmentnr], '_key':segmentnr, "search_string_precise":sandhied,"search_string_fuzzy":unsandhied,"split_points_precise":split_points_sandhied,"split_points_fuzzy":split_points_unsandhied,"filename":filename})
            lastlast_segmentnr = last_segmentnr
            lastlast_sandhied = last_sandhied
            lastlast_unsandhied = last_unsandhied
            last_sandhied = entry_sandhied
            last_unsandhied = entry_unsandhied
            last_segmentnr = segmentnr
    return search_index
def process_all(folder,lang=''):
    files = []
    search_index = []
    x = 0 
    for file in tqdm(os.listdir(folder)):
        filename = os.fsdecode(file)
        if filename.endswith('tsv') and not "NY" in filename and x < max_len:            
            #process_file(folder+filename)
            x +=1 
            search_index.extend(process_file(folder+filename,lang))
    return search_index

# search_index.extend(process_all(skt_folder))
# with open(search_index_path_sanskrit, 'w') as outfile:        
#      json.dump(search_index, outfile,indent=4,ensure_ascii=False)

search_intex = []
search_index.extend(process_all(pli_folder))
with open(search_index_path_pali, 'w') as outfile:        
     json.dump(search_index, outfile,indent=4,ensure_ascii=False)

     
# search_index = []
# search_index.extend(process_all(tib_folder))
# with open(search_index_path_tibetan, 'w') as outfile:        
#     json.dump(search_index, outfile,indent=4,ensure_ascii=False)
# search_index = []
# search_index.extend(process_all(chn_folder))
# with open(search_index_path_chn, 'w') as outfile:        
#     json.dump(search_index, outfile,indent=4,ensure_ascii=False)
# search_index = []    
