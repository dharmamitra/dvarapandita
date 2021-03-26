from tqdm import tqdm
from main import pali_get_vectors_fast,vector_pool_hier_weighted,read_stopwords
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

windowsize = PALI_WINDOWSIZE

pli_stop =  read_stopwords(PALI_STOPWORDS)

def get_weight(word):
    if word in pli_stop or len(word) <=2:
        return 0.1
    else:        
        return 1
    
def read_file(filename):
    print("NOW PROCESSING: " + filename)
    plifile = []
    with open(filename,"r") as f:
        plifile = [line.rstrip('\n') for line in f]
    pliwords = []
    pliweights = []
    plivectors = []
    filename_short = re.sub(".*/","",filename).replace(".tsv","")
    prefix = ''
    for line in plifile:
        line_length = len(line.rstrip('\n'))
        if line_length > 1 and line_length < 2000:
            if len(line.split('\t')) >= 3:
                current_id,unstripped,stripped_with_stopwords = line.split('\t')[:3]
                if re.search('[a-z]',stripped_with_stopwords):
                    stripped_with_stopwords = re.sub("[^a-zA-Z ]","",stripped_with_stopwords)
                    current_id = re.sub(".*/","",current_id)
                    current_words = stripped_with_stopwords.split()
                    last_word = ""
                    for i in range(0,len(current_words)):
                        word = current_words[i].replace('+','') 
                        pliwords.append([filename_short,current_id,word,prefix + " " + unstripped])
                        prefix = ''
                        pliweights.append(get_weight(word))
                        plivectors.append(pali_get_vectors_fast(word)[0])
                else:
                    prefix += " " + unstripped
    sumvectors = []
    for c in range(len(plivectors)):
         sumvectors.append(vector_pool_hier_weighted(plivectors[c:c+windowsize],pliweights[c:c+windowsize]))
    print("DONE PROCESSING: " + filename)
    #random_number = randint(0,9)
    random_number = "0"
    npsave(PALI_DATA_PATH + "folder" + str(random_number) + "/" +  filename_short + "_vectors.npy",np.array(sumvectors).astype('float32'))
    pickle.dump(pliwords,open(PALI_DATA_PATH + "folder" + str(random_number) + "/" + filename_short + "_words.p","wb"))
    return [pliwords,np.array(sumvectors).astype('float32')]

def calculate_words_and_vectors(plifolder):
    pliwords = []
    list_of_ids = []
    plifiles = []
    sumvector_list = []
    for file in os.listdir(plifolder):
        plifilename = os.fsdecode(file)
        #if  "T02" in plifilename or "T03" in plifilename or "T04" in plifilename:
        if 1==1:
            #read_file(plifolder+plifilename)
            plifiles.append(plifolder+plifilename)
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.imap(read_file, plifiles)
    pool.close()



calculate_words_and_vectors(PALI_TSV_DATA_PATH)
