from tqdm import tqdm
from main import skt_get_vectors_fast,vector_pool_hier_weighted,read_stopwords
import numpy as np
import pickle
import re
import faiss
import os
import h5py
import multiprocessing
from random import randint
from quotes_constants import *
from numpy import save as npsave

windowsize = SANSKRIT_WINDOWSIZE

skt_stop =  read_stopwords(SANSKRIT_STOPWORDS)

def get_weight(word):
    if word in skt_stop:
        return 0.1
    else:        
        return 1
    
def read_file(filename):
    print("NOW PROCESSING: " + filename)

    filename_short = re.sub(".*/","",filename).replace(".tsv","")
    #bucket_number = randint(0,9)
    bucket_number = 0    
    if not os.path.isfile(SANSKRIT_DATA_PATH + "folder" + str(bucket_number) + "/" + filename_short + "_words.p"):
        sktlines = []
        with open(filename,"r") as f:
            sktlines = [line.rstrip('\n') for line in f]
        sktwords = []
        sktweights = []
        sktvectors = []
        prefix = ''
        
        for line in sktlines:
            line_length = len(line)
            if len(line.split('\t')) >= 3 and line_length < 20000:
                current_id, unstemmed, stemmed_with_stopwords = line.split('\t')[:3]
                if re.search('[a-z][A-Z]', stemmed_with_stopwords):
                    current_id = re.sub(".*/", "", current_id)
                    entries = stemmed_with_stopwords.split(' # ')
                    for entry in entries: 
                        stem = entry.split(' ')[0]
                        stem_vector = skt_get_vectors_fast(stem)
                        if len(stem_vector):
                            sktwords.append([filename_short, current_id, stem, prefix + " " + unstemmed])
                            sktweights.append(get_weight(stem))
                            sktvectors.append(stem_vector[0])
                            prefix = ''
                else:
                    prefix += " " + unstemmed
            else:
                print("WARNING, LINE TOO LONG! ",filename_short, line)

        sumvectors = []
        for c in range(len(sktvectors)):
             sumvectors.append(vector_pool_hier_weighted(sktvectors[c:c+windowsize],sktweights[c:c+windowsize]))
        print("DONE PROCESSING: " + filename)
        np.save(SANSKRIT_DATA_PATH + "folder" + str(bucket_number) + "/" + filename_short + "_vectors.npy",np.array(sumvectors).astype('float32'))
        pickle.dump(sktwords,open(SANSKRIT_DATA_PATH + "folder" + str(bucket_number) + "/" + filename_short + "_words.p","wb"))


def calculate_words_and_vectors(sktfolder):
    sktfiles = []
    for file in os.listdir(sktfolder):       
        sktfilename = os.fsdecode(file)
        if ".tsv" in sktfilename:
            sktfiles.append(sktfolder+sktfilename)
    print(sktfiles)
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.map(read_file, sktfiles)
    pool.close()



calculate_words_and_vectors(SANSKRIT_TSV_DATA_PATH)
