from tqdm import tqdm
from main import tib_stop,tib_get_vectors_fast,vector_pool_hier_weighted,read_stopwords
import numpy as np
import pickle
import re
import faiss
import os
import h5py
import multiprocessing
from random import randint

from quotes_constants import *
from calculate_quotes import calculate_all
from numpy import save as npsave

windowsize = TIBETAN_WINDOWSIZE

tib_stop =  read_stopwords(TIBETAN_STOPWORDS)
def get_weight(word):
    if word in tib_stop or len(word) <=2:
        return 0.001
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
    random_number = randint(0,9)
    npsave(TIBETAN_VECTORS_PATH + "folder" + str(random_number) + "/" +  filename_short + "_vectors.npy",np.array(sumvectors).astype('float32'))
    pickle.dump(tibwords,open(TIBETAN_VECTORS_PATH + "folder" + str(random_number) + "/" + filename_short + "_words.p","wb"))
    return []

def populate_index(tibfolder):
    tibwords = []
    list_of_ids = []
    tibfiles = []
    sumvector_list = []
    for file in os.listdir(tibfolder):
        tibfilename = os.fsdecode(file)
        #if  "T02" in tibfilename or "T03" in tibfilename or "T04" in tibfilename:
        if not "NY" in tibfilename:
            tibfiles.append(tibfolder+tibfilename)
            #read_file(tibfolder+tibfilename)
    pool = multiprocessing.Pool(processes=12)
    file_data = pool.map(read_file, tibfiles)
    pool.close()
    # for data_entry in file_data:
    #     if data_entry[1].ndim == 2:
    #         tibwords.extend(data_entry[0])
    #         sumvector_list.append(data_entry[1])
    # sumvectors = np.concatenate(sumvector_list)
    # print(len(tibwords))
    # print(len(sumvectors))
    # list_of_ids = list(range(len(sumvectors)))
    # pickle.dump( tibwords, open(TIBETAN_WORDS_PATH, "wb" ) )
    # # print("Writing vectors...")
    # # with h5py.File('../vectordata/tibsumvectors.h5', 'w') as hf:
    # #     hf.create_dataset("tibsumvectors",  data=sumvectors)
    # index = faiss.IndexHNSWFlat(100, 32)
    # #index = faiss.index_factory(100, "OPQ64_128,IVF262144_HNSW32,PQ32") # this is a compressed index
    # index.verbose = True
    # faiss.normalize_L2(sumvectors)
    # index.train(sumvectors)
    # index.add(sumvectors)
    # print("Writing Index")
    # faiss.write_index(index, TIBETAN_INDEX_PATH)        
    # return 1

populate_index("/home/basti/data/tibetan/tsv/")


