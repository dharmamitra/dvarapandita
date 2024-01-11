import re
from random import randint
from pathlib import Path

import pandas as pd
import numpy as np
import fasttext

from utils.constants import * ###################################################
from file_mngr import FileMngr

class Vectorizer:
    """tsv(segmentId, orig-text) --> tsv(segmentId, orig-text, tokenized-text)
    """

    def __init__(self, 
                 lang: str, 
                 input_dir: str, 
                 n_buckets,
                 threads,
                 resume_mode=True, 
                 input_extention=".tsv",
                 sep="\t",
                 output_dir = "vectors-tsv",
                 output_extention = ".vectors.tsv"
                 ) -> None:
        self.lang: str = lang
        self.resume_mode = resume_mode
        self.sep = sep
        self.file_mngr = FileMngr(input_dir, 
                                  input_extention = input_extention,
                                  output_dir = output_dir,
                                  output_extention = output_extention
                                  )
        
        ################## Lang specific ########################  --> LanguageMngr ???
        self.windowsize = WINDOWSIZE[lang]
        # self.exploder = self.init_exploder
        # self.splitter = self.init_splitter()
        # self.tokenizer = self.init_tokenizer()
        self.cleaner = self.init_cleaner()
        self.vector_model = self.get_vector_model()
        self.stopwords = self.read_stopwords()

    def create_vectorfile(self, file_path: Path):
        print("NOW PROCESSING",file_path.stem)

        filename = file_path.stem
        file_df = pd.read_csv(file_path, 
                              sep=self.sep, 
                              names=['segmentId', 'original_text', 'stemmed_text'],
                              on_bad_lines="skip").astype(str)
#################################################################################
########################     continue here         ##############################
#################################################################################
        vec_df = self.exploder(file_df, self.lang)
        bucket_number = randint(1, self.n_buckets)
        bucket_path = out_path + "folder" + str(bucket_number)

        if not os.path.isdir(bucket_path):
            os.mkdir(bucket_path)
        vec_df.to_pickle(bucket_path + "/" + filename + ".p")
        

    def exploder(self, file_df):
        file_df['stemmed_text'] = file_df['stemmed_text'].apply(self.split)
        vec_df = file_df.explode("stemmed_text")
        vec_df['weights'] = vec_df['stemmed_text'].apply(lambda word: self.get_weight(word, self.lang))
        vec_df['vectors'] = vec_df['stemmed_text'].apply(lambda word: self.get_vector(word, self.vector_model))
        vector_list = vec_df['vectors'].tolist()
        weight_list = vec_df['weights'].tolist()
        vec_df['sumvectors'] = self.get_sumvectors(vector_list, weight_list, self.windowsize)
        return vec_df

    def get_vector_model(lang):
        return fasttext.load_model(VECTOR_PATH + lang + ".bin")

    def read_stopwords(self):
        f = open(STOPWORDS_PATH + self.lang + "_stop.txt", 'r')
        stopwords = []
        for line in f:
            m = re.search("(.*)", line) # this is for tibetan
            #m = re.search("([^\t]+)\t(.*)", line) # this is for chinese
            if m:
                if not m[0] == "#":
                    stopwords.append(m.group(1).strip())
        return stopwords

    def get_weight(self, word):
            if word in self.stopwords:
                return 0.1
            else:        
                return 1

    def get_vector(stem,vector_model):
        return vector_model.get_word_vector(stem)

    def get_sumvector(self, vectors,weights=False):
        if weights:
            return self.vector_pool_hier_weighted(vectors, weights)
        else:
            return np.average(vectors,axis=0)

    def vector_pool_hier_weighted(self, vectors, weigths):
        pool = []
        for i in range(1,len(vectors)+1):
            for vector in vectors[0:i]:
                pool.append(np.average(vectors[0:i],axis=0,weights=weigths[0:i]))
        return np.mean(pool,axis=0)

    def get_sumvectors(self, vector_list, weight_list):
        sumvectors = []
        for i in range(len(vector_list)):
            k = i + self.windowsize
            sumvectors.append(self.get_sumvector(vector_list[i:k], weight_list[i:k]))
        return sumvectors
