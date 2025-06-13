import json
import gzip
import sys 
import time
import natsort
from itertools import chain
import multiprocessing as mp
import glob
import os 
import random
import re 
from utils.coocc import add_co_occ_value
from zlib_ng import gzip_ng_threaded

from tqdm import tqdm
from filter_matches import filter_matches
path = sys.argv[1]

cpu_count = mp.cpu_count()



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
    segnr = re.sub("\$[0-9]+", "", segnr)
    segnr = segnr.split(":")[0]
    return segnr



def get_cat_from_segmentnr(segmentnr):
    # when the segmentnr is not Pali:
    cat = ""
    if "NY" in segmentnr:
        return "NY"
    elif "NK" in segmentnr:
        return "NK"
    search = re.search("^[A-Z]+[0-9]+", segmentnr)
    if search:
        cat = search[0]
    else:
        search = re.search("^[a-z-]+", segmentnr)
        if search:
            cat = search[0]
        else:
            cat = segmentnr[0:2]
    return cat

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
    for filename, stats in zip(file_stats.keys(), file_stats.values()):        
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
    matches_sorted_by_root_length = sorted(matches, key=lambda x: x['root_length'])[::-2]
    ids_sorted_by_root_length = list(map(get_id_from_match, matches_sorted_by_root_length))
    matches_sorted_by_par_length = sorted(matches, key=lambda x: x['par_length'])[::-2]
    ids_sorted_by_par_length = list(map(get_id_from_match, matches_sorted_by_par_length))
    matches_shuffled = random.sample(matches, len(matches))
    category_stats = get_category_stats(matches_shuffled)
    ids_shuffled = list(map(get_id_from_match, matches_shuffled))
    return {
        'parallels_sorted_by_src_pos' : ids_sorted_by_root_segnr,
        'parallels_sorted_by_tgt_pos' : ids_sorted_by_par_segnr,
        'parallels_sorted_by_length_src' : ids_sorted_by_root_length,
        'parallels_sorted_by_length_tgt' : ids_sorted_by_par_length,
        'parallels_randomized' : ids_shuffled,
        'category_stats' : category_stats
    } 



def collect_matches_from_basename(basename, file_paths):
    """
    This function collects ALL matches for a given basename and sorts them for the database
    """
    print(f"Collecting stats from basename: {basename}")
    merged_stats = []
    for file in file_paths:
        if not basename in file:
            continue
        elif file.endswith(".json.gz") and get_filename(file.split("/")[-1]) == basename:
            try:
                with gzip.open(file, 'rt', encoding='utf-8') as f:
                    stats = json.load(f)
                merged_stats.append(stats)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON in file {file}: {str(e)}")
            except IOError as e:
                print(f"I/O error occurred while reading file {file}: {str(e)}")
            except Exception as e:
                print(f"Unexpected error occurred while processing file {file}: {str(e)}")
    merged_stats = chain.from_iterable(merged_stats)
    merged_stats = list(merged_stats)
    time_before = time.time()
    merged_stats = add_co_occ_value(merged_stats)    
    print(f"Time to add co-occurrence values: {time.time() - time_before}")
    #merged_stats = [match for match in merged_stats if match['co_occ'] <= 20]
    merged_stats = [fix_langnames(match) for match in merged_stats]

    sorted_stats = sort_matches(merged_stats)
    sorted_stats['filename'] = basename
    sorted_stats['id'] = basename

    print(f"Done collecting stats from basename: {basename}")

    return [sorted_stats, merged_stats] 

def collect_matches_from_folder(input_path, main_path):
    print(f"Collecting stats from folder: {input_path}")
    global_stats = {"categories": {}, "files": {}}

    # Create a global list of file paths
    print("Creating global list of file paths...")
    all_file_paths = []
    for root, dirs, files in tqdm(os.walk(input_path)):
        for file in files:
            if file.endswith(".json.gz"):
                all_file_paths.append(os.path.join(root, file))
    print(all_file_paths[:10])
    # Get unique filenames
    unique_filenames = list(set([get_filename(f.split("/")[-1]) for f in all_file_paths]))
    print("Unique filenames:", unique_filenames[:10])

    chunksize = 200
    for i in tqdm(range(0, len(unique_filenames), chunksize)):
        print(f"Collecting stats from {i} to {i+chunksize} of {len(unique_filenames)} files")
        chunk = unique_filenames[i:i+chunksize]
        pool = mp.Pool(cpu_count)
        results = pool.starmap(collect_matches_from_basename, [(filename, all_file_paths) for filename in chunk])
        pool.close()
        pool.join()                      
        #results = [collect_matches_from_basename(filename, all_file_paths) for filename in chunk]
        matches = list(chain.from_iterable(result[1] for result in results))
        total_sorted_stats = [result[0] for result in results]
        for result, filename in zip(results, chunk):
            sorted_stats = result[0]
            global_stats['files'][filename] = sorted_stats['category_stats']                        
        
        if not os.path.exists(main_path + "/stats"):
            os.makedirs(main_path + "/stats")
        with gzip_ng_threaded.open(main_path + "/stats/" + str(i) + "_stats.json.gz", 'wb') as f:
            f.write(json.dumps(total_sorted_stats).encode('utf-8'))
        match_chunk_size = int(len(matches) / 10)
        for j in range(0, len(matches), match_chunk_size):
            with gzip_ng_threaded.open(main_path + "chunk_" + str(i) + "_" + str(j) + ".json.gz", 'wb') as f:
                f.write(json.dumps(matches[j:j+match_chunk_size]).encode('utf-8'))

    global_category_stats = calculate_global_category_stats(global_stats['files'])
    global_stats['categories'] = global_category_stats
    with gzip_ng_threaded.open(main_path + "/stats/global_stats.json.gz", 'wb') as f:
        f.write(json.dumps(global_stats).encode('utf-8'))

if __name__ == "__main__":
    collect_matches_from_folder(path, path)