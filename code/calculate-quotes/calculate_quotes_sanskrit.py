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
    sktlines = []
    filename_short = re.sub(".*/","",filename).replace(".tsv","")
    bucket_number = "0" 
    if not os.path.isfile(SANSKRIT_DATA_PATH + "folder" + str(bucket_number) + "/" + filename_short + "_words.p"):
        with open(filename,"r") as f:
            sktlines = [line.rstrip('\n') for line in f]
        sktwords = []
        sktweights = []
        sktvectors = []
        prefix = ''
        for line in sktlines:
            line_length = len(line)
            if line_length > 1 and line_length < 2000:
                if len(line.split('\t')) >= 3:
                    current_id, unstemmed, stemmed_with_stopwords = line.split('\t')[:3]
                    if re.search('[a-z][A-Z]',stemmed_with_stopwords):
                        #stripped_with_stopwords = re.sub("[^a-zA-Z ]","",stripped_with_stopwords)
                        current_id = re.sub(".*/", "", current_id)
                        entries = stemmed_with_stopwords.split(' # ')
                        for entry in entries: #i in range(1,len(current_entries)): # warum funktioniert dieser Code???
                            stem = entry.split(' ')[0]
                            sktwords.append([filename_short, current_id, stem, prefix + " " + unstemmed])
                            prefix = ''
                            sktweights.append(get_weight(word))
                            sktvectors.append(skt_get_vectors_fast(word)[0])
                    else:
                        prefix += " " + unstemmed
            else:
                print("WARNING, LINE TOO LONG! ",filename_short, line)
        sumvectors = []
        for c in range(len(sktvectors)):
             sumvectors.append(vector_pool_hier_weighted(sktvectors[c:c+windowsize],sktweights[c:c+windowsize]))
        print("DONE PROCESSING: " + filename)
        #bucket_number = randint(0,9)
        bucket_number = 0
        np.save(SANSKRIT_DATA_PATH + filename_short + "_vectors.npy",np.array(sumvectors).astype('float32'))
        pickle.dump(sktwords,open(SANSKRIT_DATA_PATH + filename_short + "_words.p","wb"))


def calculate_words_and_vectors(sktfolder):
    sktwords = []
    list_of_ids = []
    sktfiles = []
    sumvector_list = []
    for file in os.listdir(sktfolder):
        sktfilename = os.fsdecode(file)
        sktfiles.append(sktfolder+sktfilename)
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.map(read_file, sktfiles)
    pool.close()



calculate_words_and_vectors(SANSKRIT_TSV_DATA_PATH)
