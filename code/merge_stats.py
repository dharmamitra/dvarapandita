import json
import gzip
import sys 
import natsort
from itertools import chain
import multiprocessing as mp
import glob
import os 
import random
import re 
from zlib_ng import gzip_ng_threaded

from tqdm import tqdm
from filter_matches import filter_matches
path = sys.argv[1]

def get_filename(segnr):
    segnr = re.sub("_[0-9]+:", ":", segnr)
    segnr = re.sub("$[0-9]+", "", segnr)
    return segnr.split(":")[0]

def add_co_occ_value(matches):
    references = {}
    for match in matches:
        root_segnr = match['root_segnr'][0]
        if root_segnr not in references:
            references[root_segnr] = []
        references[root_segnr].append(match)
    for key in references.keys():
        for match in references[key]:
            coocc = 0
            beg = match['root_offset_beg']
            end = match['root_offset_end']
            for match_refence in references[key]:
                if match_refence['root_offset_beg'] <= beg and match_refence['root_offset_end'] >= end:
                    coocc += 1
            match['co_occ'] = coocc
    return matches
                

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
    #print("Collecting stats from basename: " + filename)
    subfolders = [f for f in glob.glob(main_path + "/*") if os.path.isdir(f)] #and f.endswith("_stats")]
    merged_stats = []
    for subfolder in subfolders:        
        if os.path.isfile(subfolder + "/" + filename + ".json.gz"):            
            stats = json.loads(gzip.open(subfolder + "/" + filename + ".json.gz", 'r').read())
            merged_stats.append(stats)      
    # change this [item for sublist in merged_stats for item in sublist] to itertools.chain.from_iterable      
    merged_stats = chain.from_iterable(merged_stats)
    merged_stats = filter_matches(merged_stats)
    merged_stats = add_co_occ_value(merged_stats)    
    merged_stats = [match for match in merged_stats if match['co_occ'] <= 20]   
    sorted_stats = sort_matches(merged_stats)
    sorted_stats['filename'] = get_filename(filename)
    sorted_stats['id'] = get_filename(filename)
    return [sorted_stats, merged_stats] 

def collect_stats_from_folder(input_path, main_path):
    print("Collecting stats from folder: " + input_path)
    global_stats = { "collections": {}, 
                    "files": {} }                    
    # subfolders are all folders in main_path that end in _stats
    subfolders = [f for f in glob.glob(input_path + "/*") if os.path.isdir(f)]
    # filenames are all files in subfolders that end in _stats.json.gz    
    filenames = []
    for subfolder in subfolders:
        filenames.extend([f[:-8] for f in glob.glob(subfolder + "/*") if f.endswith(".json.gz")])    
    filenames = [f.split("/")[-1] for f in filenames]    
    unique_filenames = list(set(filenames))    
    # use mp to collect stats from all files in parallel in chunks of 1000 files a time
    chunksize = 200
    for i in tqdm(range(0, len(unique_filenames), chunksize)):
        print("Collecting stats from " + str(i) + " to " + str(i+chunksize) + " of " + str(len(unique_filenames)) + " files")
        chunk = unique_filenames[i:i+chunksize]
        pool = mp.Pool(mp.cpu_count())        
        results = pool.starmap(collect_stats_from_basename, [(filename, input_path) for filename in chunk])
        # get results without mp
        pool.close()
        pool.join()              
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
    global_stats['collections'] = global_category_stats
    with gzip_ng_threaded.open(main_path + "/stats/global_stats.json.gz", 'wb') as f:
        f.write(json.dumps(global_stats).encode('utf-8'))
<<<<<<< HEAD
            
    for subfolder in subfolders:
        os.rmdir(subfolder)    

=======
>>>>>>> d1b07d0 (Various code updates)
