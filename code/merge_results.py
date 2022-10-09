import pandas as pd
import glob
import multiprocessing
import re
import os
from ast import literal_eval

from utils.constants import *
from utils.merging import get_pair_clusters, construct_matches_from_pair_clusters, create_matches_with_text
def run_merge_results(path, lang):
    paths = []
    filelist =  glob.glob(path + '/**/*.p', recursive=True)
    filepaths = []
    for current_file in filelist:
        print(current_file)
        if "4021" in current_file:
            filepaths.append([current_file, lang])
            merge_results_file([current_file, lang])
            break
    # pool = multiprocessing.Pool(processes=16)
    # pool.map(self.calc_results_file,query_files)
    # pool.close()

def iterate_buckets(inquiry_df, bucket_path, head_filename, lang):
    # let's just assume that we never gonna use more than 100 buckets
    for i in range(100):
        current_file_path = bucket_path + "folder" + str(i) + "/" + head_filename + "_results.tsv.gz"
        if os.path.isfile(current_file_path):
            process_matches(inquiry_df, current_file_path, lang)
            

def merge_results_file(data):
    path, lang = data
    print("MERGING RESULTS OF",path) 
    inquiry_df = pd.read_pickle(path)
    # remove unneeded data to reduce memory usage (esp. vectors)
    del(inquiry_df['sumvectors'])
    del(inquiry_df['vectors'])
    del(inquiry_df['weights'])
    bucket_path = path.split("folder")[0]
    head_filename = re.sub(".+/","", path)
    head_filename = head_filename.replace(".p","")    
    iterate_buckets(inquiry_df, bucket_path, head_filename, lang)


    
def process_matches(inquiry_df, match_path, lang):
    matches = pd.read_csv(match_path, sep="\t", compression="gzip")
    matches['query_segmentnr'] = matches['query_segmentnr'].apply(lambda x: literal_eval(x))
    # first we convert our data into dictionaries for easier lookup
    inquiry_segments = dict(zip(inquiry_df.segmentnr, inquiry_df.original))
    target_segments = dict(zip(matches.match_segment, matches.match_sentence))
    position_pairs = list(zip(matches.query_position, matches.match_position))
    inquiry_segment_position = dict(zip(matches.query_position, matches.query_segmentnr))
    match_segment_position = dict(zip(matches.match_position, matches.match_segment))

    # next step: get the clusters
    pair_clusters = get_pair_clusters(position_pairs, WINDOWSIZE[lang])

    # reconstruct the matches
    matches_segments = construct_matches_from_pair_clusters(pair_clusters,
                                                            inquiry_segment_position,
                                                            match_segment_position)
    match_results = create_matches_with_text(matches_segments,
                                    inquiry_segments,
                                    target_segments,
                                    lang)

    print(inquiry_df)
    print(matches)
    
run_merge_results("../tibetan-work/folder1", "tib")
