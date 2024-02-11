import json
import gzip
import sys 
import natsort
import multiprocessing as mp
import glob
import os 
import random
import re 
from tqdm import tqdm
path = sys.argv[1]

def get_filename(segnr):
    return segnr.split(":")[0]

def get_cat_from_segmentnr(segmentnr):
    # when the segmentnr is not Pali:
    cat = ""
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
    print("Sorting matches")    
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
        'ids_sorted_by_root_segnr' : ids_sorted_by_root_segnr,
        'ids_sorted_by_par_segnr' : ids_sorted_by_par_segnr,
        'ids_sorted_by_root_length' : ids_sorted_by_root_length,
        'ids_sorted_by_par_length' : ids_sorted_by_par_length,
        'ids_shuffled' : ids_shuffled,
        'category_stats' : category_stats
    } 

def collect_stats_from_basename(filename, main_path):
    print("Collecting stats from basename: " + filename)
    subfolders = [f for f in glob.glob(main_path + "/*") if os.path.isdir(f) and f.endswith("_stats")]
    merged_stats = []
    for subfolder in subfolders:
        if os.path.isfile(subfolder + "/" + filename + "_stats.json.gz"):
            stats = json.loads(gzip.open(subfolder + "/" + filename + "_stats.json.gz", 'r').read())
            merged_stats.append(stats)        
    merged_stats = [item for sublist in merged_stats for item in sublist['matches']]
    sorted_stats = sort_matches(merged_stats)
    sorted_stats['filename'] = filename
    sorted_stats['id'] = filename
    return sorted_stats

def collect_stats_from_folder(main_path):
    global_stats = { "collections": {}, 
                    "files": {} }                    
    # subfolders are all folders in main_path that end in _stats
    subfolders = [f for f in glob.glob(main_path + "/*") if os.path.isdir(f) and f.endswith("_stats")]
    # filenames are all files in subfolders that end in _stats.json.gz    
    filenames = []
    for subfolder in subfolders:
        filenames.extend([f[:-14] for f in glob.glob(subfolder + "/*") if f.endswith("_stats.json.gz")])    
    filenames = [f.split("/")[-1] for f in filenames]
    unique_filenames = list(set(filenames))    
    # use mp to collect stats from all files in parallel in chunks of 1000 files a time
    for i in tqdm(range(0, len(unique_filenames), 1000)):
        chunk = unique_filenames[i:i+1000]
        pool = mp.Pool(mp.cpu_count())
        results = pool.starmap(collect_stats_from_basename, [(filename, main_path) for filename in chunk])
        pool.close()
        pool.join()
        
        for result, filename in zip(results, chunk):
            global_stats['files'][filename] = result['category_stats']            
            del result['category_stats']
        if not os.path.exists(main_path + "/stats"):
            os.makedirs(main_path + "/stats")
        with gzip.open(main_path + "/stats/" + str(i) + "_stats.json.gz", 'wb') as f:
            f.write(json.dumps(results).encode('utf-8'))
    global_category_stats = calculate_global_category_stats(global_stats['files'])
    global_stats['collections'] = global_category_stats
    with gzip.open(main_path + "/stats/global_stats.json.gz", 'wb') as f:
        f.write(json.dumps(global_stats).encode('utf-8'))
            
    for subfolder in subfolders:
        os.rmdir(subfolder)    

