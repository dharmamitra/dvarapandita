import json
import glob 
import natsort
import os
import random
import re
import gzip
from tqdm import tqdm
from filter_matches import filter_matches
from utils.coocc import add_co_occ_value
from utils.deduplicate import deduplicate_matches
from utils.constants import COOCC_THRESHOLD
from pathlib import Path
from multiprocessing import Pool
from itertools import islice
import math
from datetime import datetime

use_multiprocessing = True

# ----------------------------
# Helper Functions
# ----------------------------

def safe_write_gzip_ndjson(data, filepath):
    """Safely write data to a gzipped NDJSON file using a temporary file."""
    temp_path = filepath + '.temp'
    try:
        with gzip.open(temp_path, 'wt', encoding='utf-8', compresslevel=6) as f:
            for item in data:
                json.dump(item, f)
                f.write('\n')
            f.flush()
        os.replace(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Error writing to {filepath}: {str(e)}")

def safe_write_gzip_json(data, filepath):
    """Safely write data to a gzipped JSON file using a temporary file."""
    temp_path = filepath + '.temp'
    try:
        with gzip.open(temp_path, 'wt', encoding='utf-8', compresslevel=6) as f:
            json.dump(data, f)
            f.flush()
        os.replace(temp_path, filepath)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise Exception(f"Error writing to {filepath}: {str(e)}")

def rename_lang(lang):
    if "tib" in lang:
        return 'bo'
    if "chn" in lang:
        return 'zh'
    if "eng" in lang:
        return 'en'
    if "skt" in lang:
        return 'sa'
    if 'pli' in lang:
        return 'pa'
    return lang

def fix_langnames(match):
    match['src_lang'] = rename_lang(match['src_lang'])
    match['tgt_lang'] = rename_lang(match['tgt_lang'])
    return match

def get_filename(segnr):
    segnr = segnr.replace(".json.gz", "")
    if "ZH_" in segnr:
        segnr = re.sub("_[0-9][0-9][0-9]$", "", segnr)
        segnr = re.sub("_[0-9][0-9][0-9]:", ":", segnr)
    segnr = re.sub(r"\$[0-9]+", "", segnr)
    segnr = segnr.split(":")[0]
    return segnr

def get_cat_from_segmentnr(segmentnr):
    return segmentnr.split("_")[1]

def get_id_from_match(match):
    return match['id']

def get_category_stats(matches):
    category_stats = {}
    for match in matches:
        par_cat = get_cat_from_segmentnr(match['par_segnr'][0])
        if par_cat not in category_stats:
            category_stats[par_cat] = 0
        category_stats[par_cat] += match['root_length']
    return category_stats

def calculate_global_category_stats(file_stats):
    global_category_stats = {}
    for filename, stats in file_stats.items():
        root_cat = get_cat_from_segmentnr(filename)
        if root_cat not in global_category_stats:
            global_category_stats[root_cat] = {}
        for cat, length in stats.items():
            if cat not in global_category_stats[root_cat]:
                global_category_stats[root_cat][cat] = 0
            global_category_stats[root_cat][cat] += length
    return global_category_stats

def sort_matches(matches):
    matches_sorted_by_root_segnr = natsort.natsorted(matches, key=lambda x: x['root_segnr'])
    ids_sorted_by_root_segnr = list(map(get_id_from_match, matches_sorted_by_root_segnr))
    matches_sorted_by_par_segnr = natsort.natsorted(matches, key=lambda x: x['par_segnr'])
    ids_sorted_by_par_segnr = list(map(get_id_from_match, matches_sorted_by_par_segnr))
    matches_sorted_by_root_length = sorted(matches, key=lambda x: x['root_length'])[::-1]
    ids_sorted_by_root_length = list(map(get_id_from_match, matches_sorted_by_root_length))
    matches_sorted_by_par_length = sorted(matches, key=lambda x: x['par_length'])[::-1]
    ids_sorted_by_par_length = list(map(get_id_from_match, matches_sorted_by_par_length))
    matches_shuffled = random.sample(matches, len(matches))
    category_stats = get_category_stats(matches_shuffled)
    ids_shuffled = list(map(get_id_from_match, matches_shuffled))
    return {
        'parallels_sorted_by_src_pos': ids_sorted_by_root_segnr,
        'parallels_sorted_by_tgt_pos': ids_sorted_by_par_segnr,
        'parallels_sorted_by_length_src': ids_sorted_by_root_length,
        'parallels_sorted_by_length_tgt': ids_sorted_by_par_length,
        'parallels_randomized': ids_shuffled,
        'category_stats': category_stats
    }

def process_file_matches(matches, filename):
    """Process matches from a single file and return stats and filtered matches."""
    try:
        print(f"\n[{datetime.now()}] Starting process_file_matches for {filename}")
        
        # Fix language names
        
        
        # Filter matches
        print(f"[{datetime.now()}] Number of matches before filtering: {len(matches)}")
        filtered_matches = filter_matches(matches)
        print(f"[{datetime.now()}] Number of matches after filtering: {len(filtered_matches)}")
        filtered_matches = deduplicate_matches(filtered_matches)
        print(f"[{datetime.now()}] Number of matches after deduplication: {len(filtered_matches)}")
        
        # Add co-occurrence values
        filtered_matches = add_co_occ_value(filtered_matches)
        print(f"[{datetime.now()}] Finished adding co-occurrence values")
        
        # Filter by co-occurrence threshold
        filtered_matches = [m for m in filtered_matches if m['co_occ'] <= COOCC_THRESHOLD]
        print(f"[{datetime.now()}] Number of matches after co-occurrence filtering: {len(filtered_matches)}")
        
        # fix lang names
        filtered_matches = [fix_langnames(m) for m in filtered_matches]
        print(f"[{datetime.now()}] Finished fixing language names")

        # Get category stats
        category_stats = get_category_stats(filtered_matches)
        print(f"[{datetime.now()}] Finished calculating category stats")
        
        # Create stats object
        stats_obj = {
            'filename': filename,
            'category_stats': category_stats,
            **sort_matches(filtered_matches)
        }
        print(f"[{datetime.now()}] Finished creating stats object")
        
        return stats_obj, filtered_matches, category_stats
        
    except Exception as e:
        print(f"Error processing matches for {filename}: {str(e)}")
        return None, [], {}

def process_single_file(file_path, output_path):
    """Process a single file and return its results"""
    try:
        # Get filename from input path
        filename = Path(file_path).stem.replace('.ndjson', '')
        
        # Check if output files already exist
        matches_output = os.path.join(output_path, f"{filename}.ndjson.gz")
        stats_output = os.path.join(output_path, "stats", f"{filename}_stats.json.gz")
        
        if os.path.exists(matches_output) and os.path.exists(stats_output):
            print(f"Output files already exist for {filename}, skipping...")
            return None

        print(f"Starting to process: {file_path}")
        current_matches = []
        
        # Create temporary uncompressed file
        temp_file = file_path.replace('.gz', '.temp')
        try:
            # Gunzip the file using system command
            os.system(f"gunzip -c '{file_path}' > '{temp_file}'")
            
            # Read the uncompressed file
            with open(temp_file, 'r', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        match = json.loads(line)
                        if not filename:
                            filename = get_filename(match['root_segnr'][0])
                        current_matches.append(match)
                    except json.JSONDecodeError as je:
                        print(f"JSON decode error in {file_path} at line {line_number}: {str(je)}")
                        continue
                    except Exception as e:
                        print(f"Error processing line {line_number} in {file_path}: {str(e)}")
                        continue
                        
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            return None
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.remove(temp_file)

        # Only process if we actually got some matches
        if not current_matches:
            print(f"No valid matches found in {file_path}")
            return None, []

        stats_obj, filtered_matches, cat_stats = process_file_matches(
            current_matches, filename)

        # write matches to file using NDJSON
        safe_write_gzip_ndjson(filtered_matches, os.path.join(output_path, f"{filename}.ndjson.gz"))
        print(f"Wrote matches for {filename}")
        
        # write stats to file using regular JSON
        safe_write_gzip_json(stats_obj, os.path.join(output_path, "stats", f"{filename}_stats.json.gz"))
        print(f"Wrote stats for {filename}")
        
        print(f"Finished processing: {file_path}")
        return stats_obj
            
    except Exception as e:
        print(f"Error processing file {file_path}: {str(e)}")
        return None, []

def process_batch(file_batch, output_path, do_multiprocessing=True):
    """Process a batch of files in parallel and return their results"""
    batch_stats = []
    print("PROCESSING BATCH: ", file_batch)
    
    if do_multiprocessing:
        with Pool() as pool:
            results = pool.starmap(process_single_file, 
                                 [(file, output_path) for file in file_batch])
    else:
        results = [process_single_file(file, output_path) for file in file_batch]
    
    # Combine results
    for stats_obj in results:
        if stats_obj:
            batch_stats.append(stats_obj)
            
    return batch_stats

def chunk_files(files, chunk_size):
    for i in range(0, len(files), chunk_size):
        yield files[i:i + chunk_size]

def process_sorted_files(input_path, output_path, batch_size=100000, use_multiprocessing=False):
    os.makedirs(output_path, exist_ok=True)
    os.makedirs(os.path.join(output_path, "stats"), exist_ok=True)
    
    global_stats = {"categories": {}, "files": {}}
    
    input_files = glob.glob(os.path.join(input_path, "**/*.ndjson.gz"), recursive=True)
    
    
    # Process files in parallel using multiprocessing
    total_batches = math.ceil(len(input_files)/batch_size)    
    # Process batches directly without extra list wrapping
    for batch_idx, file_batch in enumerate(chunk_files(input_files, batch_size)):
        batch_stats = process_batch(file_batch, output_path, 
                                  do_multiprocessing=use_multiprocessing)
        
        # Update global stats
        for stat in batch_stats:
            if 'filename' in stat:
                global_stats['files'][stat['filename']] = stat['category_stats']
        
    global_stats['categories'] = calculate_global_category_stats(global_stats['files'])
    safe_write_gzip_json(global_stats, os.path.join(output_path, "stats", "global_stats.json.gz"))


def collect_matches_from_folder_exp(input_path, output_path):
    """Main function to process pre-sorted files."""
    try:
        print("Processing path: ", input_path)
        process_sorted_files(input_path, output_path, use_multiprocessing=use_multiprocessing)
        print("Processing complete.")
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        raise

