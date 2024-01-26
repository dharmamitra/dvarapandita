import fasttext
#from sentence_transformers import SentenceTransformer

from utils.constants import *
import numpy as np 
import re

def split_sanskrit_stem(stems):
    result = []
    for stem in stems.split("#"):
        stem = stem.strip().split(" ")[0]
        if len(stem) > 0:
            result.append(stem)
    return result


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
    return fasttext.load_model(VECTOR_PATH + lang + ".bin")



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

def get_vector(stem, vector_model):
    try:
        # Attempt to get the vector for the given stem
        return vector_model.get_word_vector(stem)
    except Exception as e:
        # In case of any exception, return a zero vector
        # Get the first word in the model's vocabulary
        first_word = next(iter(vector_model.get_words()))
        # Get the dimension of the vectors in the model using the first word
        vector_dim = len(vector_model.get_word_vector(first_word))
        # Return a zero vector of zeros with the same dimension as a NumPy array
        return np.zeros(vector_dim)

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

# write embedding class
#class Embedder():
#    #model = SentenceTransformer('multi-qa-mpnet-base-dot-v1') 
#    model = SentenceTransformer('all-MiniLM-L6-v2')
#    def __init__(self):
#        pass
#    def get_vectors(self,sentences):
#        return self.model.encode(sentences)


