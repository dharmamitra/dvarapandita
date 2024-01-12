import re
from pathlib import Path

import pandas as pd
import numpy as np
import fasttext

from utils.constants import * ###################################################
from file_mngr import FileMngr, TextFile


class Vectorizer:
    """tsv(segmentId, orig-text) --> tsv(segmentId, orig-text, tokenized-text)
    """

    def __init__(self, 
                 lang: str, 
                 input_dir: str, 
                 threads=1,
                 n_buckets=1,
                 resume_mode=True, 
                 input_extention=".tsv",
                 sep="\t",
                 output_dir = "vectors-tsv",
                 output_extention = ".vectors.tsv"
                 ) -> None:
        self.lang: str = lang
        self.resume_mode = resume_mode
        self.sep = sep
        self.file_mngr = FileMngr(n_buckets=n_buckets,
                                  input_dir = input_dir, 
                                  input_extention = input_extention,
                                  output_dir = output_dir,
                                  output_extention = output_extention
                                  )

        ################## Lang specific ########################  --> LanguageMngr ???
        self.windowsize = WINDOWSIZE[lang]
        self.splitter = self.init_splitter()
        # self.exploder = self.init_exploder
        # self.tokenizer = self.init_tokenizer()
        # self.cleaner = self.init_cleaner()
        self.vector_model = self.init_vector_model() #fasttext
        self.stopwords = self.read_stopwords()

    def create_vectorfile(self, file_path: Path):
        text = TextFile(self.lang, file_path)
        print("NOW PROCESSING", text.name)

        text.segments_df = pd.read_csv(file_path, 
                              sep=self.sep, 
                              names=['segmentId', 'original_text', 'stemmed_text'],
                              on_bad_lines="skip")
        text.words_df = self.explode_segment_df(text.segments_df)
        text.words_df = self.window_vec_exploded_df(text.words_df) 
        return text

    def explode_segment_df(self, segments_df):
        # 1. the segments are splitted into word lists
        words_df = segments_df.drop(columns="original_text")
        words_df['stemmed_text'] = words_df['stemmed_text'].apply(self.splitter)
        # 2. the table is "streched" by the word lists
        return words_df.explode("stemmed_text")

    def window_vec_exploded_df(self, file_df):
        file_df['weights'] = file_df['stemmed_text'].apply(lambda word: self.get_weight(word))
        file_df['vectors'] = file_df['stemmed_text'].apply(lambda word: self.get_vector(word))
        file_df['sumvectors'] = self.calc_win_vecs(
            file_df['vectors'].tolist(), 
            file_df['weights'].tolist()
        )
        return file_df

    def init_vector_model(self):
        return fasttext.load_model(VECTOR_PATH + self.lang + ".bin")

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

    def get_vector(self, word):
        try:
            assert type(word) == str
            return self.vector_model.get_word_vector(word)
        except:
            print(f"{word}: type {type(word)}")

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

    def calc_win_vecs(self, vector_list, weight_list):
        sumvectors = []
        for i in range(len(vector_list)):
            k = i + self.windowsize
            sumvectors.append(self.get_sumvector(vector_list[i:k], weight_list[i:k]))
        return sumvectors

    ########## Language specific functions ##########
    def init_splitter(self):
        match self.lang:
            case "skt":
                return split_sanskrit_stem
            case other:
                return str.split

    def split_sanskrit_stem(stems):
        result = []
        for stem in stems.split("#"):
            stem = stem.strip().split(" ")[0]
            if len(stem) > 0:
                result.append(stem)
        return result