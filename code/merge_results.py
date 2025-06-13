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
from filter_matches import filter_matches
import fcntl
import contextlib

def get_filename(segnr):
    segnr = segnr.replace(".json.gz", "")
    if "ZH_" in segnr:
        segnr = re.sub("_[0-9][0-9][0-9]$", "", segnr)
        segnr = re.sub("_[0-9][0-9][0-9]:", ":", segnr)
    segnr = re.sub(r"\$[0-9]+", "", segnr)
    segnr = segnr.split(":")[0]
    return segnr


@contextlib.contextmanager
def file_lock(path):
    """Context manager for file locking with retry mechanism."""
    lock_path = f"{path}.lock"
    max_retries = 20
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            with open(lock_path, 'w') as lock_file:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                    yield
                    break  # Success - exit the retry loop
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    try:
                        os.remove(lock_path)
                    except OSError:
                        pass
        except OSError as e:
            if attempt == max_retries - 1:  # Last attempt
                raise  # Re-raise the last error if all retries failed
            time.sleep(retry_delay)  # Wait before retrying

def construct_path_json(match_path, inquiry_file):
    """Construct the JSON path with a random number in the matches folder."""
    # Replace folder[0-9]+ pattern with 'matches' in the path
    matches_dir = re.sub(r'folder\d+.*', 'matches/', os.path.dirname(match_path))
    
    # Create matches directory if it doesn't exist
    os.makedirs(matches_dir, exist_ok=True)
    
    # Generate random number between 0 and 1000
    
    
    # Construct new path
    return os.path.join(matches_dir, f"{inquiry_file}.ndjson.gz")

def get_data_dicts(inquiry_df, matches):
    """Extract the necessary data dictionaries for the matches."""
    inquiry_segments = dict(zip(inquiry_df.segmentnr, inquiry_df.original))
    target_segments = dict(zip(matches.match_segment, matches.match_sentence))
    position_pairs = list(zip(matches.query_position, matches.match_position))
    inquiry_segment_position = dict(zip(matches.query_position, matches.query_segmentnr))
    match_segment_position = dict(zip(matches.match_position, matches.match_segment))
    return inquiry_segments, target_segments, position_pairs, inquiry_segment_position, match_segment_position

def append_to_gzip(match_results, path_json):
    """Append matches as NDJSON to a gzip file."""
    with file_lock(path_json):
        # Convert each match to a JSON line
        json_lines = [json.dumps(match, ensure_ascii=False) + '\n' 
                     for match in match_results]
        
        # Append to the gzip file
        with gzip.open(path_json, 'at') as f:
            f.writelines(json_lines)

def process_matches(inquiry_df, matches, match_path, lang, alignment_method="local"):
    print("MERGING", match_path)
    
    matches.replace(np.nan, '', regex=True, inplace=True)
    
    inquiry_segments, target_segments, position_pairs, inquiry_segment_position, match_segment_position = get_data_dicts(inquiry_df, matches)
    print("GETTING PAIR CLUSTERS")
    pair_clusters = get_pair_clusters(position_pairs, WINDOWSIZE[lang] * 2)
    print("DONE GETTING PAIR CLUSTERS", len(pair_clusters))    
    matches_segments = construct_matches_from_pair_clusters(pair_clusters, inquiry_segment_position, match_segment_position)
    print("MATCHES SEGMENTS", len(matches_segments))    
    match_results = create_matches_with_text(matches_segments, pair_clusters, inquiry_segments, target_segments, lang, alignment_method=alignment_method)
    print("MATCH RESULTS", len(match_results))
    number_of_matches_before = len(match_results)
    
    # Convert NumPy int64 to native Python int
    match_results = [{k: int(v) if isinstance(v, np.int64) else v for k, v in match.items()} 
                    for match in match_results]
    
    match_results = filter_matches(match_results)
    print("NUMBER OF MATCHES BEFORE FILTERING", number_of_matches_before)
    print("NUMBER OF MATCHES AFTER FILTERING", len(match_results))
    
    if match_results:  # Only write if we have results
        # Add filename to each match and sort
        for match in match_results:
            match['filename'] = get_filename(match['root_segnr'][0])
        match_results.sort(key=lambda x: x['filename'])
        
        # Group matches by filename
        matches_by_file = {}
        for match in match_results:
            filename = match['filename']
            if filename not in matches_by_file:
                matches_by_file[filename] = []
            matches_by_file[filename].append(match)
        
        # Write matches to separate files by filename
        matches_dir = os.path.dirname(match_path)
        for filename, file_matches in matches_by_file.items():
            output_path = construct_path_json(match_path, filename)
            print("WRITING", output_path)
            # Use file lock when writing
            with file_lock(output_path):
                json_lines = [json.dumps(match, ensure_ascii=False) + '\n' 
                            for match in file_matches]
                
                with gzip.open(output_path, 'at') as f:
                    f.writelines(json_lines)
        
        print("DONE", match_path)