from pathlib import Path
import glob
import os 
import numpy as np
import re
import faiss
import pandas as pd
from utils.constants import *
from utils.general import test_if_should_load
from merge_results import process_matches
import multiprocessing
import multiprocessing.pool


class CalculateResults:
    def __init__(self, bucket_path, lang, index_method="cpu", cindex=None, alignment_method="local"):
        self.main_path = re.sub("folder.*","",bucket_path)
        self.wordlist = pd.read_pickle(bucket_path + "wordlist.p")
        self.segments = self.wordlist['segmentnr'].tolist()
        self.stems = self.wordlist['analyzed'].tolist()
        self.sentences = self.wordlist['original'].tolist()
        #self.wordlist = self.wordlist.reset_index()
        self.wordlist_len = len(self.wordlist)
        self.lang = lang
        self.bucket_path = bucket_path
        self.alignment_method = alignment_method
        self.index_method = index_method

        global index
        if index_method == "cpu":
            index = faiss.read_index(bucket_path + "vectors.idx")
        else:
            index = cindex   


    def _clean_results_by_threshold(self, scores, positions):        
        threshold = THRESHOLD[self.lang]
        bigger_is_better = BIGGER_IS_BETTER[self.lang]
        epsilon = 1e-6  # Small tolerance for floating-point comparison
        
        if bigger_is_better:
            condition = lambda score: score > (threshold - epsilon)
        else:
            condition = lambda score: score < (threshold + epsilon)
            
        mask = np.array([condition(score) for score in scores])
        current_positions = np.array(positions)[mask].tolist()
        current_scores = np.array(scores)[mask].tolist()
        return [current_positions, current_scores]

    def _get_match_data(self, query_position, positions, scores):
        def get_match_data_from_position(position, score):
            try:
                segment = self.segments[position]
                sentence = self.sentences[position]
                
                # Adjust stem data based on language
                stems = self.stems[position]
                if self.lang != "eng":                
                    end_idx = min(position + WINDOWSIZE[self.lang], len(self.stems))
                    stems = " ".join(str(item) if isinstance(item, float) else item 
                                   for item in self.stems[position:end_idx])            
                return [segment, sentence, stems, position, score]
            except Exception as e:
                raise
            
        all_match_data = []

        for position, score in zip(positions, scores):
            if position >= 0:  # faiss returns -1 when not enough results are found
                try:
                    beginning_data = get_match_data_from_position(position, score)                
                    end_position = position + WINDOWSIZE[self.lang] if position + WINDOWSIZE[self.lang] < self.wordlist_len else self.wordlist_len - 1                         
                    end_data = get_match_data_from_position(end_position, score)        
                    end_data[2] = beginning_data[2]  # stems need to be equalized
                    all_match_data.append(beginning_data)
                    if end_data not in all_match_data:
                        all_match_data.append(end_data)
                except Exception as e:
                    raise
        return all_match_data


    def create_querypaths(self, query_path):
        filelist =  glob.glob(query_path + '/**/*.p', recursive=True)
        filepaths = []
        for current_file in filelist:
            filepath = current_file
            if test_if_should_load(filepath):
                if not "wordlist" in filepath:
                    filepaths.append(filepath)
        return filepaths

    def calc_results_folder(self, query_path):
        query_files = self.create_querypaths(query_path)
        if self.index_method == "gpu": 
            for query_file in query_files:  
                self.calc_results_file(query_file)     
        else:   
            with multiprocessing.Pool(processes=16) as pool:
                results = pool.map(self.calc_results_file, query_files)

    def _get_margin_scores(scoresself, scores):
        """
        for each score, divide it by the average of the other scores
        """
        scores = 1 - scores
        margin_scores = []
        for score in scores:
            other_scores = scores.copy()        
            other_scores = np.delete(other_scores, np.where(other_scores == score))
            margin_score = score / np.mean(other_scores)
            margin_scores.append(margin_score)
        return margin_scores
        
    def calc_results_file(self, query_file_path):
        basename = Path(query_file_path).stem
        
        # File reading
        try:
            query_df = pd.read_pickle(query_file_path)
        except Exception as e:
            return        
        
        query_vectors = self.prepare_query_vectors(query_df)
        
        if query_vectors is not None:
            try:
                query_results = index.search(query_vectors, QUERY_DEPTH)
            except Exception as e:
                return
            
            results = self._extract_results(query_df, query_results)
            result_df = pd.DataFrame(results)
            process_matches(query_df, result_df, self.bucket_path + basename, self.lang, alignment_method=self.alignment_method)

    def prepare_query_vectors(self, query_df):
        query_vectors = np.array(query_df['sumvectors'].tolist(), dtype="float32")
        if len(query_vectors) > 0:
            faiss.normalize_L2(query_vectors)
            return query_vectors

    def _extract_results(self, query_df, query_results):
        results = {
            "query_position": [],
            "query_segmentnr": [],
            "query_stems": [],
            "query_sentence": [],
            "match_segment": [],
            "match_sentence": [],
            "match_stems": [],
            "match_position": [],
            "match_score": []
        }
        
        for query_position, (scores, positions) in enumerate(zip(query_results[0], query_results[1])):
            cleaned_positions, cleaned_scores = self._clean_results_by_threshold(scores, positions)
            word_data = self._get_match_data(query_position, cleaned_positions, cleaned_scores)
            current_query_data = self.get_current_query_data(query_df, query_position)
            
            for entry in word_data:
                try:
                    results["query_position"].append(query_position)
                    results["query_segmentnr"].append(current_query_data["segmentnrs"])
                    results["query_stems"].append(current_query_data["stems"])
                    results["query_sentence"].append(current_query_data["sentence"])
                    results["match_segment"].append(entry[0])
                    results["match_sentence"].append(entry[1])
                    results["match_stems"].append(entry[2])
                    results["match_position"].append(entry[3])
                    results["match_score"].append(entry[4])
                except Exception as e:
                    continue
        
        return results

    def get_current_query_data(self, query_df, query_position):
        total_query_stems = query_df['analyzed']
        total_query_segmentnrs = query_df['segmentnr']
        total_query_sentences = query_df['original']
        query_position = min(query_position, len(total_query_stems))
        end_position = min(query_position + WINDOWSIZE[self.lang], len(total_query_stems))
        stems = " ".join(str(item) for item in total_query_stems[query_position:end_position])
        segmentnrs = list(dict.fromkeys(total_query_segmentnrs[query_position:end_position]))
        sentence = " ".join(list(dict.fromkeys(total_query_sentences[query_position:end_position])))
        
        if self.lang == "eng":
            stems = total_query_stems[query_position]
            segmentnrs = [total_query_segmentnrs[query_position]]
            
        return {"stems": stems, "segmentnrs": segmentnrs, "sentence": sentence}

    def save_results_to_json(self, result_df, basename):
        result_df.to_json(
            self.bucket_path + basename + "-before-alignment.json.gz", 
            orient="records", force_ascii=False, 
            compression="gzip", indent=2
        )


    def run(self):
        for directory in os.listdir(self.main_path):            
            self.calc_results_folder(self.main_path+directory)
                                                    