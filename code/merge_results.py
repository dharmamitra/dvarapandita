import pandas as pd
import glob
import time
import multiprocessing
import re
import json
import os
import gzip
import numpy as np
from utils.constants import *
from utils.merging import get_pair_clusters, construct_matches_from_pair_clusters, create_matches_with_text
from posprocess_matches import filter_matches
    
def construct_path_json(match_path):
    """Construct the JSON path from the match path."""
    if "_results.tsv.gz" in match_path:
        return match_path.replace("_results.tsv.gz", ".json.gz")
    if "json.gz" not in match_path:
        return match_path + ".json.gz"
    return match_path

def get_data_dicts(query_df, matches): # and one list!!!
    """Extract the necessary data dictionaries for the matches."""
    query_segments = dict(zip(query_df.segmentnr, query_df.original))
    target_segments = dict(zip(matches.match_segment, matches.match_sentence))
    position_pairs = list(zip(matches.query_position, matches.match_position))
    query_segment_position = dict(zip(matches.query_position, matches.query_segmentnr))
    match_segment_position = dict(zip(matches.match_position, matches.match_segment))
    return query_segments, target_segments, position_pairs, query_segment_position, match_segment_position

def write_to_gzip(json_str, path_json):
    """Write the given JSON string to a gzip file."""
    json_bytes = json_str.encode('utf-8')
    with gzip.GzipFile(path_json, 'w') as fout:
        fout.write(json_bytes)

def process_matches(query_df, result_df, match_path, lang, alignment_method="local"):
    path_json = construct_path_json(match_path)
    print("MERGING", match_path)
    
    result_df.replace(np.nan, '', regex=True, inplace=True)
    
    inquiry_segments, target_segments, position_pairs, inquiry_segment_position, match_segment_position = get_data_dicts(query_df, result_df)
    
    pair_clusters = get_pair_clusters(position_pairs, WINDOWSIZE[lang])
    
    matches_segments = construct_matches_from_pair_clusters(pair_clusters, inquiry_segment_position, match_segment_position)
    match_results = create_matches_with_text(matches_segments, pair_clusters, inquiry_segments, target_segments, lang, alignment_method=alignment_method)
    match_results = filter_matches(match_results)

    json_str = json.dumps(match_results, indent=4, ensure_ascii=False) + "\n"
    write_to_gzip(json_str, path_json)
    print("DONE", match_path)
