from gensim.models import KeyedVectors
from utils.constants import *
import numpy as np 
import re



def read_stopwords(lang):
    f = open(STOPWORDS_PATH + lang + "_stop.txt", 'r')
    stopwords = []
    for line in f:
        m = re.search("(.*)", line) # this is for tibetan
        #m = re.search("([^\t]+)\t(.*)", line) # this is for chinese
        if m:
            if not m[0] == "#":
                stopwords.append(m.group(1).strip())
    return stopwords

stopwords = {}

for lang in LANGS:
    stopwords[lang] = read_stopwords(lang)


def get_vector_model(lang):    
    return KeyedVectors.load_word2vec_format(VECTOR_PATH + lang + ".vec", binary=False)


def get_weight(word,lang):
    if lang == "tib":
        if word in stopwords[lang]  or len(word) <=2:
            return 0.1
        else:        
            return 1
    else:
        if word in stopwords[lang]:
            return 0.1
        else:        
            return 1

def vector_pool_hier_weighted(vectors,weigths):
    pool = []
    for i in range(1,len(vectors)+1):
        for vector in vectors[0:i]:
            pool.append(np.average(vectors[0:i],axis=0,weights=weigths[0:i]))
    return np.mean(pool,axis=0)

def get_vector(stem,vector_model):
    if stem in vector_model.vocab:
        return vector_model.get_vector(stem)
    else:
        # when OOV, return vector of zeros
        return np.zeros(vector_model.vector_size)
                


def get_sumvector(vectors,weights=False):
    if weights:
        return vector_pool_hier_weighted(vectors,weights)
    else:
        return np.average(vectors,axis=0)

def get_sumvectors(vector_list, weight_list, windowsize):
    sumvectors = []
    for i in range(len(vector_list)):
        k = i + windowsize
        sumvectors.append(get_sumvector(vector_list[i:k], weight_list[i:k]))
    return sumvectors
    
