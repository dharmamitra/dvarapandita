import os
from pathlib import Path
import glob
import multiprocessing 

import numpy as np
import re
import faiss
import pandas as pd
from utils.constants import *

faiss.omp_set_num_threads(10)

class calculate_results:
    def __init__(self, bucket_path, lang):
        self.main_path = re.sub("folder.*","",bucket_path)
        self.wordlist = pd.read_pickle(bucket_path + "wordlist.p")
        self.segments = self.wordlist['segmentnr'].tolist()
        self.stems = self.wordlist['stemmed'].tolist()
        self.sentences = self.wordlist['original'].tolist()
        self.wordlist = self.wordlist.reset_index()
        self.wordlist_len = len(self.wordlist)
        self.lang = lang
        self.bucket_path = bucket_path
        global index
        index = faiss.read_index(bucket_path + "vectors.idx")
        
    def clean_results_by_threshold(self, scores, positions):
        current_positions = []
        current_scores = []
        list_of_accepted_numbers = []
        threshold = THRESHOLD[self.lang]
        for current_position,current_score in zip(positions,scores):
            if current_score < threshold:
                is_accepted_flag = 0
                for current_number in list_of_accepted_numbers:
                    if abs(current_number-current_position) < MIN_DISTANCE:
                        is_accepted_flag = 1
                if is_accepted_flag == 0:
                    list_of_accepted_numbers.append(current_position)
                    current_positions.append(current_position)
                    current_scores.append(current_score)
        return [current_positions,current_scores]

    def get_word_data(self, query_position, positions,scores):
        all_words = []
        for position, score in zip(positions,scores):
            if position >= 0: # fiass returns -1 when not enough results are found
                current_segment_beg = self.segments[position]
                current_sentence_beg = self.sentences[position]
                current_stems_beg = " ".join(self.stems[position:position+WINDOWSIZE[self.lang]])
                all_words.append([current_segment_beg, current_sentence_beg, current_stems_beg, position, score])
                end_position = position+WINDOWSIZE[self.lang]
                if end_position < self.wordlist_len:
                    current_segment_end = self.segments[end_position]
                    current_sentence_end = self.sentences[end_position]
                    current_stems_end = " ".join(self.stems[position:position+WINDOWSIZE[self.lang]])
                    end_data = [current_segment_end, current_sentence_end, current_stems_end, position, score]
                    if end_data not in all_words: # simple trick to make sure that beg and end are not identical
                        all_words.append(end_data)
        return all_words

    def process_result(self, data):
        query_position, scores, positions = data
        positions, scores = clean_results_by_threshold(positions, scores)
        all_words = get_word_data(query_position, positions, scores)
        return all_words

    def create_querypaths(self, query_path):
        filelist =  glob.glob(query_path + '/**/*.p', recursive=True)
        filepaths = []
        for current_file in filelist:
            filepath = current_file
            if not os.path.isfile(filepath.replace(".p","_results.tsv.gz").replace(query_path,self.bucket_path)) and not "wordlist" in filepath:
                filepaths.append(filepath)
        return filepaths

    def calc_results_folder(self, query_path):
        query_files = self.create_querypaths(query_path)
        # for query_file in query_files:
        #     self.calc_results_file(query_file)
        print("QUERY PATHS", query_files)
        pool = multiprocessing.Pool(processes=16)
        pool.map(self.calc_results_file,query_files)
        pool.close()
        
    def calc_results_file(self, query_file_path):
        print("NOW PROCESSING",query_file_path)
        basename = Path(query_file_path).stem 
        result_df = pd.DataFrame()
        query_df = pd.read_pickle(query_file_path)
        total_query_stems = query_df['stemmed']
        total_query_segmentnrs = query_df['segmentnr']
        #print("QUERY DF",query_df)
        query_vectors = np.array(query_df['sumvectors'].tolist(),dtype="float32")
        faiss.normalize_L2(query_vectors)
        query_results = index.search(query_vectors, QUERY_DEPTH)
        query_position = 0
        result_query_positions = []
        result_segments = []
        result_sentences = []
        result_stems = []
        result_positions = []
        result_scores = []
        query_stems = []
        query_segmentnrs = []
        for scores, positions in zip(query_results[0], query_results[1]):
            cleaned_positions, cleaned_scores = self.clean_results_by_threshold(scores, positions)            
            word_data = self.get_word_data(query_position, cleaned_positions, scores)
            current_query_stems = " ".join(total_query_stems[query_position:query_position+WINDOWSIZE[self.lang]])
            current_query_segmentnrs = list(dict.fromkeys(total_query_segmentnrs[query_position:query_position+WINDOWSIZE[self.lang]]))
            for entry in word_data:
                query_stems.append(current_query_stems)
                query_segmentnrs.append(current_query_segmentnrs)
                result_query_positions.append(query_position)
                result_segments.append(entry[0])
                result_sentences.append(entry[1])
                result_stems.append(entry[2])
                result_positions.append(entry[3])
                result_scores.append(entry[4])                
            query_position += 1
        result_df["query_position"] = result_query_positions
        result_df["query_segmentnr"] = query_segmentnrs
        result_df["query_stems"] = query_stems
        result_df["match_segment"] = result_segments
        result_df["match_sentence"] = result_sentences
        result_df["match_stems"] = result_stems
        result_df["match_position"] = result_positions
        result_df["match_score"] = result_scores
        
        result_df.to_csv(self.bucket_path + basename + "_results.tsv.gz",
                         index=False,
                         sep="\t",
                         compression = "gzip")
        return 1
    def run(self):
        for directory in os.listdir(self.main_path):
            self.calc_results_folder(self.main_path+directory)
                                                    
