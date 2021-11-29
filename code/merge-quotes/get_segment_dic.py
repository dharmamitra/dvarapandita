import re
import json
import os 


def atoi(text):
    return int(text) if text.isdigit() else text

def get_dic_by_tsv(tsv_path):
    current_file = open(tsv_path,"r")
    segment_dic = {}
    for line in current_file:        
        segment_id, unsandhied_string = line.split('\t')[:2]
        segment_id = re.sub(".+/","",segment_id)
        segment_dic[segment_id.strip()] = unsandhied_string.strip()
    return segment_dic


def get_segment_dic(tsv_path):
    def natural_keys(text):
        '''
        alist.sort(key=natural_keys) sorts in human order
        http://nedbatchelder.com/blog/200712/human_sorting.html
        (See Toothy's implementation in the comments)
        '''
        return [ atoi(c) for c in re.split(r'(\d+)', text) ]
    segment_dic = {}
    for file in os.listdir(tsv_path):
        filepath = tsv_path + os.fsdecode(file)
        if ".tsv" in filepath:
            current_dic = get_dic_by_tsv(filepath)
            segment_dic.update(current_dic)
    segment_keys = list(segment_dic.keys())
    #segment_keys.sort(key=natural_keys)
    segment_key_numbers = {}
    c = 0
    for key in segment_keys:
        segment_key_numbers[key] = c
        c += 1
    return segment_dic, segment_keys, segment_key_numbers,natural_keys


