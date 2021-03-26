import os
import multiprocessing
import gzip
from tqdm import tqdm as tqdm
from get_segment_dic import get_segment_dic,extend_dic_by_tsv
from quotes_constants import *

segment_dic_path = TIBETAN_SEGMENT_DICT_PATH
tab_folder = "/mnt/output/tib/data/folder0/"


segment_dic,segment_keys,segment_key_numbers,natural_keys = get_segment_dic(segment_dic_path,"")

def process_file(filepath):
    with gzip.open(filepath,'rt') as current_file:
        for line in current_file:
            entries = line.split("\t")
            for entry in entries:
                if len(entry.split('$')) > 2:
                    segment_nrs = entry.split('$')[2].split(';')
                    for segment_nr in segment_nrs:
                        if not segment_nr in segment_dic:
                            print(segment_nr)
                    
                


def process_all(tab_folder):
    file_list = []
    for file in tqdm(os.listdir(tab_folder)):
        filename = os.fsdecode(file)
        if "tab" in filename:
            #process_file(tab_folder+ "/" +filename)
            file_list.append(tab_folder+ "/" +filename)

    pool = multiprocessing.Pool(processes=16,maxtasksperchild=1)
    pool.map(process_file, file_list)
    pool.close()


process_all("/work/ftsx015/tib/data/folder0/")
process_all("/work/ftsx015/tib/data/folder1/")
process_all("/work/ftsx015/tib/data/folder2/")
process_all("/work/ftsx015/tib/data/folder3/")
process_all("/work/ftsx015/tib/data/folder4/")
process_all("/work/ftsx015/tib/data/folder5/")
process_all("/work/ftsx015/tib/data/folder6/")
process_all("/work/ftsx015/tib/data/folder7/")
process_all("/work/ftsx015/tib/data/folder8/")
process_all("/work/ftsx015/tib/data/folder9/")


