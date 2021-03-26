from tqdm import tqdm
from main import pali_get_vectors_fast,vector_pool_flat_weighted,read_stopwords
from quotes_constants import *
import numpy as np
import pickle
import json
import re
import faiss
import os
import h5py
import multiprocessing
import xliterator
from calculate_quotes import calculate_all

windowsize = PALI_WINDOWSIZE
lang = "skt"
segmentdict = {}


def get_stems(string):
    result = ""
    words = string.split("#")
    for word in words:
        current_word = word.strip().split(" ")[0]
        result += current_word + " "
    return result

pali_stop =  read_stopwords(PALI_STOPWORDS)
def get_weight(word):
    if word in pali_stop:
        return 0.001
    else:        
        return 1

def get_category_name(string):
    return re.sub(r"([A-Z0-9]+).*",r"\1",string)

def read_file(filename):
    print("NOW PROCESSING: " + filename)
    palifile = open(filename,"r")
    sktwords = []
    paliweights = []
    sktvectors = []
    filename_short = re.sub(".*/","",filename).replace(".tsv","")
    category = get_category_name(filename_short)
    for line in palifile:
        line_length = len(line.rstrip('\n'))
        if line_length > 1 and line_length < 10000:
            line = line.replace('      ','\t')
            if len(line.split('\t')) >= 3:
                current_id,unstripped,stripped = line.split('\t')[:3]
                current_words = stripped.split()
                for i in range(0,len(current_words)):
                    if len(current_words[i]) > 2:
                        sktwords.append([filename_short,current_id,current_words[i],unstripped])
                        sktvectors.append(pali_get_vectors_fast(current_words[i])[0])
                        paliweights.append(get_weight(current_words[i]))                        
                        segmentdict[current_id] = unstripped
    resultvectors = []
    print("RESULT VECTORS LENGTH",len(sktvectors))
    for c in range(len(sktvectors)):
         resultvectors.append(vector_pool_flat_weighted(sktvectors[c:c+windowsize],paliweights[c:c+windowsize]))
    print("DONE PROCESSING: " + filename)
    return [sktwords,np.array(resultvectors).astype('float32')]

sumvectors = []

def populate_index(palifolder):
    sktwords = []
    list_of_ids = []
    palifiles = []
    sumvector_list = []
    file_data = []
    for file in os.listdir(palifolder):
        palifilename = os.fsdecode(file)
        palifiles.append(palifolder+palifilename)    
        #read_file(palifolder+palifilename)
        #file_data.append(read_file(palifolder+palifilename))
    print("LENGTH",len(palifiles))
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.map(read_file, palifiles)
    pool.close()
    for data_entry in file_data:
        sktwords.extend(data_entry[0])
        sumvector_list.append(data_entry[1])
    sumvectors = np.concatenate(sumvector_list)        
    print(len(sktwords))
    print(len(sumvectors))
    list_of_ids = list(range(len(sumvectors)))
    pickle.dump( sktwords, open(PALI_WORDS_PATH, "wb" ) )
    index = faiss.IndexHNSWFlat(100, 32)
    index.verbose = True
    faiss.normalize_L2(sumvectors)
    index.train(sumvectors)
    index.add(sumvectors)
    print("Writing Index")
    faiss.write_index(index, PALI_INDEX_PATH)
    return 1



