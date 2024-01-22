import json
import gzip
import sys 
import natsort
import multiprocessing as mp
import glob
import os 
import random
import re 

def get_filename(segnr):
    return segnr.split(":")[0]

def strip_match(match):    
    return {
        "id": match['id'], 
        "root_segnr": match['root_segnr'],
        "par_segnr": match['par_segnr'],
        "root_length": match['root_length'],
        "par_length": match['par_length'],
    }
def safe_load_gzipped_json(path):
    try:
        # Using 'with' statement for safe opening and closing of the file
        with gzip.open(path, 'rt', encoding='utf-8') as file:
            return json.load(file)
    except EOFError:
        # Handling EOFError specifically
        print("EOFError: Compressed file ended before the end-of-stream marker was reached.")
    except json.JSONDecodeError:
        # Handling errors in JSON decoding
        print("JSONDecodeError: The file content is not valid JSON.")
    except FileNotFoundError:
        # Handling file not found error
        print(f"FileNotFoundError: The file {path} was not found.")
    except Exception as e:
        # Handling any other unforeseen errors
        print(f"An unexpected error occurred: {e}")
    return None

def get_stats_from_file(path):
    print("Getting stats from file: " + path)
    global_stats = {}

    stats = safe_load_gzipped_json(path)
    if not stats:
        return
    for stat in stats:
        filename = get_filename(stat['root_segnr'][0])        
        stripped_match = strip_match(stat)
        if filename not in global_stats:
            global_stats[filename] = {
                'lang' : stat['src_lang'],
                'filename' : filename,
                'matches' : []    
            }        
        global_stats[filename]['matches'].append(stripped_match)
    output_path = path[:-8] + "_stats"    
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    for filename, stat in global_stats.items():
        with gzip.open(output_path + '/' + filename + '_stats.json.gz', 'wb') as f:
            f.write(json.dumps(stat).encode('utf-8'))

def extract_stats_from_files(main_path):    
    chunk_paths = []
    for path in os.listdir(main_path):        
        if path.endswith('.json.gz') and not 'stats' in path:
            chunk_paths.append(main_path + path)            
    pool = mp.Pool(mp.cpu_count())
    results = pool.map(get_stats_from_file, chunk_paths)
    pool.close()
    pool.join()
