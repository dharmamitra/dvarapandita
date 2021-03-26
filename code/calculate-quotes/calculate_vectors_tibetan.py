from tqdm import tqdm
from main import tib_stop,tib_get_vectors_fast,vector_pool_hier_weighted,read_stopwords
import numpy as np
import pickle
import re
import faiss
import os
import h5py
import multiprocessing
from quotes_constants import *
from calculate_quotes import calculate_all
from numpy import save as npsave

windowsize = TIBETAN_WINDOWSIZE

tib_stop =  read_stopwords(TIBETAN_STOPWORDS)
def get_weight(word):
    if word in tib_stop or len(word) <2:
        return 0.1
    else:        
        return 1
    
def read_file(filename):
    print("NOW PROCESSING: " + filename)
    tibfile = []
    with open(filename,"r") as f:
        tibfile = [line.rstrip('\n') for line in f]
    tibwords = []
    tibweights = []
    tibvectors = []
    filename_short = re.sub(".*/","",filename).replace(".tsv","")
    prefix = ''
    for line in tibfile:
        line_length = len(line.rstrip('\n'))
        if line_length > 1 and line_length < 2000:
            if len(line.split('\t')) == 4:
                current_id,unstripped,stripped_with_stopwords,stripped = line.split('\t')
                if re.search('[a-z]',stripped):
                    current_id = re.sub(".*/","",current_id)
                    current_words = stripped_with_stopwords.split()
                    last_word = ""
                    for i in range(0,len(current_words)):
                        word = current_words[i]
                        tibwords.append([filename_short,current_id,word,prefix + " " + unstripped])
                        prefix = ''
                        tibweights.append(get_weight(word))
                        tibvectors.append(tib_get_vectors_fast(word)[0])
                else:
                    prefix += " " + unstripped
    sumvectors = []
    for c in range(len(tibvectors)):
         sumvectors.append(vector_pool_hier_weighted(tibvectors[c:c+windowsize],tibweights[c:c+windowsize]))
    print("DONE PROCESSING: " + filename)
    del tibfile
    npsave(TIBETAN_VECTORS_PATH + filename_short + "_vectors.npy",np.array(sumvectors).astype('float32'))
    pickle.dump(tibwords,open(TIBETAN_WORDS_PATH + filename_short + "_words.p","wb"))
    return 1

def calculate_vectors_folder(tibfolder):
    tibfiles = []    
    for file in os.listdir(tibfolder):
        tibfilename = os.fsdecode(file)
        #read_file(tibfolder+tibfilename)
        tibfiles.append(tibfolder+tibfilename)
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.map(read_file, tibfiles)
    pool.close()







