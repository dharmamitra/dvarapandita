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
segment_dic_path = '/mnt2/skt2tib-data/tibetan_segments.json'
segment_dic = json.load(open(segment_dic_path,'r'))
results = []
for segment in tqdm(segment_dic):
    results.append(segment_dic[segment])
    
